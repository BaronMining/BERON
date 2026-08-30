```python
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

APP_NAME = "BERON"

AI_PROVIDER = os.getenv("BERON_AI_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("BERON_OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("BERON_OPENAI_MODEL", "gpt-5.6-luna").strip()

SYSTEM_PROMPT = """You are BERON, a personal AI assistant.

Be intelligent, calm, natural, helpful and honest.

You are designed to communicate naturally with your user.

Never claim an action was completed unless the application confirms it.

You may suggest actions, but destructive, financial, security-sensitive,
or irreversible actions require explicit confirmation.

Keep normal answers reasonably concise.
"""


@app.get("/")
def home():
    return jsonify({
        "name": APP_NAME,
        "status": "online",
        "service": "BERON backend"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": APP_NAME
    })


def ask_openai(messages):
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "BERON_OPENAI_API_KEY is not configured on Render."
        )

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "instructions": SYSTEM_PROMPT,
            "input": messages,
        },
        timeout=90,
    )

    if not response.ok:
        try:
            provider_detail = response.json()
        except Exception:
            provider_detail = response.text[:1000]

        raise RuntimeError(
            f"OpenAI HTTP {response.status_code}: {provider_detail}"
        )

    data = response.json()

    # Responses API normally provides output_text.
    answer = data.get("output_text")

    if not answer:
        # Fallback extraction if output_text is unavailable.
        parts = []

        for item in data.get("output", []):
            if item.get("type") != "message":
                continue

            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text", "")
                    if text:
                        parts.append(text)

        answer = "\n".join(parts).strip()

    if not answer:
        raise RuntimeError(
            "OpenAI returned successfully, but BERON could not find text in the response."
        )

    return answer.strip()


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

    messages = []

    # Keep the backend bounded.
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
        if AI_PROVIDER != "openai":
            return jsonify({
                "error": "Unsupported AI provider",
                "detail": AI_PROVIDER
            }), 500

        answer = ask_openai(messages)

        return jsonify({
            "assistant": APP_NAME,
            "message": answer
        })

    except Exception as exc:
        # Return useful diagnostic information while we are testing.
        # Do NOT include the API key in this response.
        return jsonify({
            "error": "AI provider request failed",
            "detail": str(exc)
        }), 502


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

    # The cloud backend never executes arbitrary Windows commands.
    # The future Windows client will validate approved commands locally.
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
```
