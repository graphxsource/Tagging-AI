import base64, json, mimetypes, os, logging
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from openai import AzureOpenAI
#from openai import OpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO)


SYSTEM = (
    "You add tags about the product that is sent to you as an image, "
    "adding things about the type of product, the color and any other relevant attributes as tags."
)

#AZURE ENDPOINT SET
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


#OPENAI ENDPOINT REPLACEMENT
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")
# OPENAI_MODEL   = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
# if not OPENAI_API_KEY:
#     raise RuntimeError("If switching to OpenAI, set OPENAI_API_KEY (or OPEN_AI_API_KEY).")
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# client = OpenAI()
# MODEL = OPENAI_MODEL
# logging.info("Using OpenAI model: %s", MODEL)

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

class UrlOrBase64Body(BaseModel):
    image_url: Optional[HttpUrl] = None
    image_base64: Optional[str] = None
    text: Optional[str] = None

def _to_data_url_from_bytes(data: bytes, content_type: Optional[str]) -> str:
    mime = content_type or "image/png"
    if not mime.startswith("image/"):
        guessed = mimetypes.guess_type(f"file.{mime.split('/')[-1]}")[0]
        mime = guessed if (guessed and guessed.startswith("image/")) else "image/png"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

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


from fastapi import Body

@app.post("/tag", response_model=TagResponse)
async def tag_image_multipart(
    file: UploadFile = File(None, description="Image file (multipart/form-data)"),
    text: Optional[str] = Form(None, description="Optional user text"),
):
    if file is None:
        raise HTTPException(status_code=400, detail="Missing image file.")
    try:
        data = await file.read()
        if not data:
            raise ValueError("Empty file.")
        data_url = _to_data_url_from_bytes(data, file.content_type)
        content = []
        if text and text.strip():
            content.append({"type": "text", "text": text})
        content.append({"type": "image_url", "image_url": {"url": data_url}})
        return _call_model_with_content(content)
    except Exception as e:
        logging.exception("Error processing multipart upload")
        raise HTTPException(status_code=400, detail=f"Invalid image upload: {e}")

@app.post("/tag-json", response_model=TagResponse)
async def tag_image_json(body: UrlOrBase64Body = Body(...)):
    if not body.image_url and not body.image_base64:
        raise HTTPException(status_code=400, detail="Provide image_url or image_base64.")

    content = []
    if body.text and body.text.strip():
        content.append({"type": "text", "text": body.text})

    if body.image_url:
        content.append({"type": "image_url", "image_url": {"url": str(body.image_url)}})
    else:
        data_url = f"data:image/png;base64,{body.image_base64}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})

    try:
        return _call_model_with_content(content)
    except Exception as e:
        logging.exception("Error processing JSON request")
        raise HTTPException(status_code=400, detail=f"Model call failed: {e}")
