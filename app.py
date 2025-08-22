import base64, json, mimetypes, os, logging
from typing import cast
import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

# --- env / config bootstrap ---
load_dotenv()  # load variables from .env if present

# Support alternate env var naming the user mentioned (OPEN_AI_API_KEY) by mapping it.
if not os.getenv("OPENAI_API_KEY") and os.getenv("OPEN_AI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPEN_AI_API_KEY"]  # normalize for SDK

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "Missing OPENAI_API_KEY (or OPEN_AI_API_KEY) environment variable. Set it in your .env file."
    )

_raw_model = os.getenv("OPENAI_MODEL")
if not _raw_model or not _raw_model.strip():
    MODEL = "gpt-4.1-mini"  # default when env unset or blank
else:
    MODEL = _raw_model.strip()

logging.info("Using model: %s", MODEL)
SYSTEM = "You add tags about the product that is sent to you as an image, adding things about the type of product, the color and any other relevant attributes as tags."

client = OpenAI()  # uses OPENAI_API_KEY from env

def _img_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# Gradio ChatInterface with multimodal input passes:
#   message: {"text": str, "files": [<paths>]}
#   history: list[{"role": ..., "content": ...}]
def chat_fn(message, history):
    """Gradio chat handler.

    Issues fixed vs original:
      * Correct image content part type (image_url with nested url) for Chat Completions API.
      * Removed unsupported 'input_image' type in chat.completions context.
      * Removed reliance on resp.output_parsed / resp.output_text (not present for chat completions).
      * Added defensive JSON parsing & graceful fallback when model output is malformed.
      * Skips adding empty text part when user only uploads images.
    """
    user_text = (message or {}).get("text") or ""
    files = (message or {}).get("files") or []

    # Build multimodal user content for Chat Completions API
    content = []
    if user_text.strip():
        content.append({"type": "text", "text": user_text})
    for p in files:
        if p and p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")) and os.path.exists(p):
            try:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": _img_to_data_url(p)}
                })
            except Exception as e:  # continue even if one image fails
                logging.warning("Failed to encode image %s: %s", p, e)

    # If somehow content is empty (no text, no valid images), send an empty text so API isn't upset
    if not content:
        content = [{"type": "text", "text": ""}]

    # Enforce structured JSON output via json_schema
    # Type checker workaround: SDK accepts list of content parts; annotate/cast.
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": content},  # type: ignore[arg-type]
    ]

    resp = client.chat.completions.create(
        model=MODEL,
        messages=cast(list, messages),
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "chatbot_reply",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": [ "tags"],
                    "additionalProperties": False
                }
            }
        },
    )

    # Extract text content from first choice
    raw_output = None
    try:
        choice_msg = resp.choices[0].message  # type: ignore[index]
        content_field = getattr(choice_msg, "content", None)
        if isinstance(content_field, list):  # sometimes SDK may return list parts
            parts = []
            for part in content_field:
                # Accept various part shapes {"type": "text", "text": ...}
                if isinstance(part, dict):
                    if part.get("type") in ("text", "output_text"):
                        parts.append(part.get("text", ""))
                    elif "text" in part:
                        parts.append(part["text"])  # fallback
            raw_output = "".join(parts).strip()
        else:
            raw_output = (content_field or "").strip()
    except Exception as e:
        logging.error("Failed extracting model output: %s", e)
        raw_output = "{}"  # fallback

    # Parse JSON with error resilience
    try:
        data = json.loads(raw_output)
    except Exception as e:
        logging.warning("JSON parse failed, attempting heuristic cleanup: %s", e)
        # Heuristic: attempt to isolate first/last braces
        try:
            start = raw_output.find('{')
            end = raw_output.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(raw_output[start:end+1])
            else:
                raise ValueError("No JSON object found")
        except Exception:
            # Final fallback minimal schema-compliant object
            data = {"tags": []}

    # Ensure required keys exist (model should supply, but be safe)
    if "tags" not in data or not isinstance(data.get("tags"), list):
        data["tags"] = []

    return json.dumps(data, ensure_ascii=False, indent=2)

demo = gr.ChatInterface(
    fn=chat_fn,
    type="messages",
    title="JSON-first Vision Chatbot",
    description="Attach images and get strictly-typed JSON back.",
    multimodal=True,  # enables text + file uploads in the input box
    textbox=gr.MultimodalTextbox(file_types=["image"], label="Message or drop images")
)

if __name__ == "__main__":
    demo.launch()
