# JSON-first Vision Chatbot

A small Gradio demo that sends text + image inputs to OpenAI's Chat Completions API and enforces a strict JSON schema response.

## Setup

1. Create a `.env` file (already included) and add your API key:

```
OPENAI_API_KEY=sk-your-key-here
# Optional alternate variable name supported:
# OPEN_AI_API_KEY=sk-your-key-here

# (Optional) override model
# OPENAI_MODEL=gpt-4.1-mini
```

2. Install dependencies (Windows PowerShell example):

```
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run the app:

```
python app.py
```

Open the local Gradio URL printed in the console.

## Notes
- Supports images (png, jpg, jpeg, webp, gif).
- Falls back gracefully if the model returns malformed JSON.
- The JSON schema currently requires only `tags` (array of strings). Adjust in `app.py` inside `response_format`.

## Troubleshooting
- If you see a runtime error about missing OPENAI_API_KEY, ensure your `.env` is present and you've reloaded the shell.
- To print debug info, set an env var before running:
```
$env:LOGLEVEL="DEBUG"; python app.py
```
