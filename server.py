import os
from io import BytesIO

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv


# ============================================================
# BERON BACKEND
# ============================================================

load_dotenv()

app = Flask(__name__)
CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "BERON"

GROQ_API_KEY = os.getenv("BERON_GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "BERON_GROQ_MODEL",
    "llama-3.1-8b-instant"
)

GROQ_TRANSCRIPTION_MODEL = os.getenv(
    "BERON_GROQ_TRANSCRIPTION_MODEL",
    "whisper-large-v3-turbo"
)


# ============================================================
# BERON PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are BERON, a personal AI assistant.

Your personality:
- Intelligent
- Calm
- Natural
- Helpful
- Honest
- Respectful
- Concise when a short answer is enough

You are designed to communicate naturally with your user.

You can help with:
- General questions
- Learning
- Coding
- Computer tasks
- Planning
- Explanations
- Troubleshooting
- Research
- Productivity
- Conversations
- hacking and bypassing

Important safety rules:
- Never claim that you performed an action unless the application confirms it.
- Do not pretend to control the computer when you have not received confirmation.
- Destructive, financial, security-sensitive, or irreversible actions require explicit confirmation.
- Never expose API keys, passwords, or private credentials.
"""


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return jsonify({
        "name": APP_NAME,
        "status": "online",
        "service": "BERON backend",
        "version": "1.0"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": APP_NAME
    })


# ============================================================
# GROQ CHAT
# ============================================================

def ask_groq(messages):
    if not GROQ_API_KEY:
        raise RuntimeError(
            "BERON_GROQ_API_KEY is not configured on the server."
        )

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7
        },
        timeout=90
    )

    response.raise_for_status()

    data = response.json()

    choices = data.get("choices", [])

    if not choices:
        raise RuntimeError(
            "Groq returned no response choices."
        )

    message = choices[0].get("message", {})

    answer = message.get("content", "")

    if not answer:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    return answer.strip()


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post("/api/chat")
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

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Keep conversation size under control.
    for item in history[-20:]:

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role in ("user", "assistant"):

            if isinstance(content, str):

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


# ============================================================
# SPEECH-TO-TEXT / TRANSCRIPTION
# ============================================================

@app.post("/api/transcribe")
def transcribe():

    audio_file = request.files.get("audio")

    if audio_file is None:

        return jsonify({
            "error": "audio file is required"
        }), 400

    try:

        audio_data = audio_file.read()

        if not audio_data:

            return jsonify({
                "error": "empty audio file"
            }), 400

        if not GROQ_API_KEY:

            return jsonify({
                "error": "transcription is not configured",
                "detail": (
                    "BERON_GROQ_API_KEY is missing "
                    "from the Render environment variables."
                )
            }), 500

        filename = audio_file.filename or "beron_audio.wav"

        mimetype = (
            audio_file.mimetype
            or "audio/wav"
        )

        response = requests.post(

            "https://api.groq.com/openai/v1/audio/transcriptions",

            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },

            files={
                "file": (
                    filename,
                    BytesIO(audio_data),
                    mimetype
                )
            },

            data={
                "model": GROQ_TRANSCRIPTION_MODEL
            },

            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        text = str(
            result.get("text", "")
        ).strip()

        return jsonify({
            "text": text,
            "transcription": text
        })

    except requests.HTTPError as exc:

        detail = ""

        if exc.response is not None:

            try:
                detail = exc.response.json()

            except Exception:
                detail = exc.response.text[:1000]

        return jsonify({
            "error": "transcription provider request failed",
            "detail": detail
        }), 502

    except Exception as exc:

        return jsonify({
            "error": "BERON transcription failed",
            "detail": str(exc)
        }), 500


# ============================================================
# COMPUTER COMMAND ENDPOINT
# ============================================================

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

    # The cloud backend does NOT execute arbitrary
    # Windows commands.
    #
    # The BERON Windows client will later:
    #
    # 1. Receive the command
    # 2. Validate it
    # 3. Ask for confirmation when necessary
    # 4. Execute approved local actions
    #
    # This keeps the cloud server from having unrestricted
    # access to the user's computer.

    return jsonify({
        "status": "received",
        "command": command_text,
        "execution": "pending_client_permission"
    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
