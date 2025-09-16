import json, os, logging
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from openai import AzureOpenAI

from fastapi import Body

load_dotenv()
logging.basicConfig(level=logging.INFO)


SYSTEM = (
    "You add tags about the product that is sent to you as an image, "
    "adding things about the type of product, the color and any other relevant attributes as tags."
)

AZURE_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY    = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")
AZURE_API_VER    = os.getenv("AZURE_API_VER")

if not (AZURE_ENDPOINT and AZURE_API_KEY and AZURE_DEPLOYMENT):
    raise RuntimeError("Set AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT.")

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VER,
)
MODEL = AZURE_DEPLOYMENT
logging.info("Using Azure OpenAI deployment: %s (api_version=%s)", MODEL, AZURE_API_VER)
app = FastAPI(title="Image Tagger API", version="1.0.0")

allowed_origins = [
"*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class TagResponse(BaseModel):
    tags: List[str]

class UrlBody(BaseModel):
    image_url: Optional[HttpUrl] = None
    text: Optional[str] = None

def _call_model_with_content(content) -> TagResponse:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": content},
    ]

    resp = client.chat.completions.create(
        model=MODEL, 
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "chatbot_reply",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tags"],
                    "additionalProperties": False,
                },
            },
        },
    )

    raw_output = ""
    try:
        msg = resp.choices[0].message
        content_field = getattr(msg, "content", None)
        if isinstance(content_field, list):
            parts = []
            for part in content_field:
                if isinstance(part, dict):
                    if part.get("type") in ("text", "output_text"):
                        parts.append(part.get("text", ""))
                    elif "text" in part:
                        parts.append(part["text"])
            raw_output = "".join(parts).strip()
        else:
            raw_output = (content_field or "").strip()
    except Exception as e:
        logging.error("Failed extracting model output: %s", e)
        raw_output = "{}"

    try:
        data = json.loads(raw_output)
    except Exception:
        start = raw_output.find("{"); end = raw_output.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(raw_output[start:end+1])
            except Exception:
                data = {"tags": []}
        else:
            data = {"tags": []}

    tags = data.get("tags")
    if not isinstance(tags, list):
        tags = []
    tags = [str(t) for t in tags if isinstance(t, (str, int, float))]
    return TagResponse(tags=tags)

@app.post("/tag", response_model=TagResponse)
async def tag_image_json(body: UrlBody = Body(...)):
    if not body.image_url:
        raise HTTPException(status_code=400, detail="Provide image_url.")

    content = []
    if body.text and body.text.strip():
        content.append({"type": "text", "text": body.text})

    content.append({"type": "image_url", "image_url": {"url": str(body.image_url)}})

    try:
        return _call_model_with_content(content)
    except Exception as e:
        logging.exception("Error processing JSON request")
        raise HTTPException(status_code=400, detail=f"Model call failed: {e}")
