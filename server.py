import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)

APP_NAME = "BERON"
AI_PROVIDER = os.getenv("BERON_AI_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("BERON_OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("BERON_OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.getenv("BERON_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("BERON_OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are BERON, a personal AI assistant.
Be intelligent, calm, natural, helpful and honest.
Never claim an action was completed unless the application confirms it.
You may suggest actions, but destructive, financial, security-sensitive,
or irreversible actions must require explicit confirmation from the user.
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
    return jsonify({"status": "healthy", "service": APP_NAME})

def ask_openai(messages):
    if not OPENAI_API_KEY:
        raise RuntimeError("BERON_OPENAI_API_KEY is not configured on the server.")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.7,
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def ask_ollama(messages):
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()

@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    history = body.get("history", [])
    if not isinstance(history, list):
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Keep the backend bounded so a client cannot send an enormous conversation.
    for item in history[-20:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:8000]})

    messages.append({"role": "user", "content": message})

    try:
        if AI_PROVIDER == "ollama":
            answer = ask_ollama(messages)
        else:
            answer = ask_openai(messages)

        return jsonify({
            "assistant": APP_NAME,
            "message": answer,
        })

    except requests.HTTPError as exc:
        detail = ""
        if exc.response is not None:
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text[:500]
        return jsonify({
            "error": "AI provider request failed",
            "detail": detail,
        }), 502

    except Exception as exc:
        return jsonify({
            "error": "BERON could not process the request",
            "detail": str(exc),
        }), 500

@app.post("/api/command")
def command():
    body = request.get_json(silent=True) or {}
    command = str(body.get("command", "")).strip()

    if not command:
        return jsonify({"error": "command is required"}), 400

    # The cloud backend does NOT execute arbitrary Windows commands.
    # The Windows client will later validate and execute approved tools locally.
    return jsonify({
        "status": "received",
        "command": command,
        "execution": "pending_client_permission"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
