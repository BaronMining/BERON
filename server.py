import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

APP_NAME = "BERON"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

SYSTEM_PROMPT = """You are BERON, a personal AI assistant.

You are intelligent, calm, natural, helpful and honest.

You should:
- Answer questions clearly.
- Help the user learn and solve problems.
- Explain things step by step when needed.
- Remember the conversation history provided by the application.
- Never claim that you performed an action unless the application confirms it.
- Never expose API keys or secret credentials.
- Keep normal answers reasonably concise.
"""


@app.get("/")
def home():
    return jsonify({
        "name": APP_NAME,
        "service": "BERON backend",
        "status": "online"
    })


@app.get("/health")
def health():
    return jsonify({
        "service": APP_NAME,
        "status": "healthy"
    })


def ask_groq(messages):

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured in Render Environment."
        )

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_completion_tokens": 1000
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


@app.post("/api/chat")
def chat():

    body = request.get_json(silent=True) or {}

    message = str(body.get("message", "")).strip()

    if not message:
        return jsonify({
            "error": "message is required"
        }), 400

    history = body.get("history", [])

    if not isinstance(history, list):
        history = []

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Keep conversation history limited.
    for item in history[-20:]:

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role in ("user", "assistant") and isinstance(content, str):

            messages.append({
                "role": role,
                "content": content[:8000]
            })

    messages.append({
        "role": "user",
        "content": message
    })

    try:

        answer = ask_groq(messages)

        return jsonify({
            "assistant": APP_NAME,
            "message": answer
        })

    except requests.HTTPError as exc:

        detail = ""

        if exc.response is not None:

            try:
                detail = exc.response.json()

            except Exception:
                detail = exc.response.text[:1000]

        return jsonify({
            "error": "AI provider request failed",
            "detail": detail
        }), 502

    except Exception as exc:

        return jsonify({
            "error": "BERON could not process the request",
            "detail": str(exc)
        }), 500


@app.post("/api/command")
def command():

    body = request.get_json(silent=True) or {}

    command_text = str(
        body.get("command", "")
    ).strip()

    if not command_text:
        return jsonify({
            "error": "command is required"
        }), 400

    return jsonify({
        "status": "received",
        "command": command_text,
        "execution": "pending_client_permission"
    })


if __name__ == "__main__":

    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port
    )
