# BERON Render Backend Setup

## Render fields

If creating the service manually:

Name:
beron-backend

Language:
Python 3

Branch:
main

Root Directory:
leave blank

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn server:app

Plan:
Free

Health Check Path:
/health

Auto-Deploy:
On

## Environment variables

In Render -> Environment Variables add:

BERON_AI_PROVIDER = openai
BERON_OPENAI_MODEL = gpt-4o-mini
BERON_OPENAI_API_KEY = YOUR_REAL_API_KEY

Do NOT commit the real API key to GitHub.

## Test after deployment

Open:

https://YOUR-BERON-SERVICE.onrender.com/health

You should receive JSON similar to:

{"service":"BERON","status":"healthy"}

The root URL should also return BERON online status.

## Chat API

POST /api/chat

JSON:
{
  "message": "Hello BERON",
  "history": []
}

The response contains:
{
  "assistant": "BERON",
  "message": "..."
}

## Important architecture note

Render is the cloud backend. It should NOT receive unrestricted Windows
commands and it should NOT attempt to access the Windows microphone.

The Windows BERON client will:
1. detect the wake word;
2. capture speech;
3. send text to this backend;
4. receive the AI response;
5. speak the response;
6. execute only locally approved tools through the security layer.

Android will later use the same backend through authenticated endpoints.
