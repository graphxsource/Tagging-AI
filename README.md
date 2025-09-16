# Tagging-AI

Tagging-AI is a simple API endpoint that uses AI to automatically tag images. It is designed for easy integration and testing, leveraging modern AI models (OpenAI or Azure OpenAI) to generate descriptive tags for images you provide.

## Features

- REST API endpoint for image tagging
- Supports Azure OpenAI backends
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

Edit `.env` and set your API keys and model/deployment info as needed:

```
#AZURE ENVS
AZURE_OPENAI_API_KEY= ""
AZURE_OPENAI_ENDPOINT= ""
AZURE_DEPLOYMENT= ""
AZURE_API_VER= ""
```

## Running the API with Uvicorn

For local testing, run the API using Uvicorn:

```powershell
uvicorn app.main:app --reload
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
