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
OPENAI_MODEL = os.getenv("BERON_OPENAI_MODEL", "gpt-4o-mini").strip()

SYSTEM_PROMPT = """
You are BERON, a personal AI assistant.

Your personality is intelligent, calm, natural, helpful and honest.

You communicate with the user naturally, like a capable personal assistant.

You must never claim that you completed an action unless the application
actually confirms that the action was completed.

You may suggest actions, but destructive, financial, security-sensitive,
or irreversible actions require explicit confirmation from the user.

Keep normal answers reasonably concise.

When you do not know something, say so honestly.
"""


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "name": APP_NAME,
        "status": "online",
        "service": "BERON backend"
    })


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": APP_NAME
    })


# ---------------------------------------------------------
# OPENAI
# ---------------------------------------------------------

def ask_openai(messages):

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "BERON_OPENAI_API_KEY is not configured on Render."
        )

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ] + messages,
        "temperature": 0.7
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=90
    )

    # If OpenAI rejects the request, preserve its error.
    if not response.ok:

        try:
            provider_detail = response.json()
        except Exception:
            provider_detail = response.text[:1000]

        raise RuntimeError(
            f"OpenAI HTTP {response.status_code}: {provider_detail}"
        )

    data = response.json()

    choices = data.get("choices", [])

    if not choices:
        raise RuntimeError(
            "OpenAI returned no choices."
        )

    message = choices[0].get("message", {})

    answer = message.get("content", "")

    if not answer:
        raise RuntimeError(
            "OpenAI returned an empty response."
        )

    return answer.strip()


# ---------------------------------------------------------
# CHAT
# ---------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():

    body = request.get_json(silent=True) or {}

    message = str(
        body.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "message is required"
        }), 400

    history = body.get("history", [])

    if not isinstance(history, list):
        history = []

    messages = []

    # Keep only the last 20 messages.
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

    # Add current user message.
    messages.append({
        "role": "user",
        "content": message
    })

    try:

        if AI_PROVIDER != "openai":

            return jsonify({
                "error": "Unsupported AI provider",
                "provider": AI_PROVIDER
            }), 500

        answer = ask_openai(messages)

        return jsonify({
            "assistant": APP_NAME,
            "message": answer
        })

    except Exception as exc:

        return jsonify({
            "error": "AI provider request failed",
            "detail": str(exc)
        }), 502


# ---------------------------------------------------------
# COMMAND
# ---------------------------------------------------------

@app.route("/api/command", methods=["POST"])
def command():

    body = request.get_json(silent=True) or {}

    command_text = str(
        body.get("command", "")
    ).strip()

    if not command_text:

        return jsonify({
            "error": "command is required"
        }), 400

    # IMPORTANT:
    # The cloud backend does NOT execute arbitrary commands
    # on your Windows computer.
    #
    # Later, the BERON Windows client will receive approved
    # commands and ask for permission before executing them.

    return jsonify({
        "status": "received",
        "command": command_text,
        "execution": "pending_client_permission"
    })


# ---------------------------------------------------------
# START SERVER
# ---------------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
