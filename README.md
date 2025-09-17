# Tagging-AI

Tagging-AI is a simple API endpoint that uses AI to automatically tag images. It is designed for easy integration and testing, leveraging modern AI models (OpenAI or Azure OpenAI) to generate descriptive tags for images you provide.

## Features

- REST API endpoint for image tagging
- Supports OpenRouter endpoint for image tagging.
- Easy configuration via `.env` file
- Docker and Uvicorn support for local development and testing

## Setup

### 1. Clone the repository

```powershell
git clone <repo-url>
cd Tagging-AI
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the `.env.example` file to `.env` and fill in the required values:

```powershell
copy .env.example .env
```

Edit `.env` and set your API keys and model info as needed:

```
OPENROUTER_URL= ""
TAGGING_API_KEY= ""
TAGGING_MODEL= ""
```

## Running the API with Uvicorn

For local testing, run the API using Uvicorn:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- The API will be available at `http://127.0.0.1:8000/`
- Use tools like Postman or curl to test the image tagging endpoint.

## Docker Support

You can also run the service using Docker:

```powershell
docker-compose up --build
```

## License

MIT
