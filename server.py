import os
import tempfile

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

APP_NAME = "BERON"

# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("BERON_GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "BERON_GROQ_MODEL",
    "llama-3.3-70b-versatile"
).strip()

GROQ_TRANSCRIPTION_MODEL = os.getenv(
    "BERON_GROQ_TRANSCRIPTION_MODEL",
    "whisper-large-v3-turbo"
).strip()

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_TRANSCRIPTION_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

# ============================================================
# BERON PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are BERON, a personal AI assistant running on the user's Windows
computer.

Your personality:
- Intelligent
- Calm
- Natural
- Helpful
- Friendly
- Concise when possible
- Honest
- Hacker when told

You should behave like a capable personal computer assistant.

Important:
- Never claim that you performed an action unless the application
  actually confirms that it happened.
- If an action requires permission, ask for confirmation.
- Never expose API keys, passwords, or other secrets.
- Do not invent information.
- When the user is speaking to you by voice, keep responses reasonably
  natural and concise.
"""

# ============================================================
# BASIC ROUTES
# ============================================================

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


# ============================================================
# GROQ CHAT
# ============================================================

def ask_groq(messages):

    if not GROQ_API_KEY:
        raise RuntimeError(
            "BERON_GROQ_API_KEY is not configured on Render."
        )

    response = requests.post(
        GROQ_CHAT_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "stream": False,
        },
        timeout=90,
    )

    if not response.ok:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]

        raise RuntimeError(
            f"Groq chat request failed: {detail}"
        )

    data = response.json()

    choices = data.get("choices", [])

    if not choices:
        raise RuntimeError(
            "Groq returned no response choices."
        )

    answer = choices[0].get("message", {}).get("content", "")

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

    # Keep conversation history bounded.
    for item in history[-20:]:

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role in ("user", "assistant") and isinstance(
            content, str
        ):
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

    except Exception as exc:

        print(
            f"[BERON CHAT ERROR] {type(exc).__name__}: {exc}"
        )

        return jsonify({
            "error": "AI provider request failed",
            "detail": str(exc)
        }), 502


# ============================================================
# AUDIO TRANSCRIPTION
# ============================================================

@app.post("/api/transcribe")
def transcribe():

    if not GROQ_API_KEY:
        return jsonify({
            "error": "BERON_GROQ_API_KEY is not configured on Render."
        }), 500

    # --------------------------------------------------------
    # IMPORTANT:
    # The Windows client must send:
    #
    # multipart/form-data
    # field name: audio
    #
    # We also accept "file" for compatibility.
    # --------------------------------------------------------

    audio = request.files.get("audio")

    if audio is None:
        audio = request.files.get("file")

    if audio is None:
        return jsonify({
            "error": "audio file is required"
        }), 400

    if not audio.filename:
        return jsonify({
            "error": "audio filename is required"
        }), 400

    temp_path = None

    try:

        # Preserve the original extension.
        filename = audio.filename

        _, extension = os.path.splitext(filename)

        if not extension:
            extension = ".wav"

        # Create temporary file.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temp:

            temp_path = temp.name
            audio.save(temp_path)

        # ----------------------------------------------------
        # Send the actual audio file to Groq.
        # ----------------------------------------------------

        with open(temp_path, "rb") as audio_file:

            files = {
                "file": (
                    filename,
                    audio_file,
                    audio.mimetype or "audio/wav"
                )
            }

            data = {
                "model": GROQ_TRANSCRIPTION_MODEL,
                "response_format": "json",
                "language": "en"
            }

            response = requests.post(
                GROQ_TRANSCRIPTION_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                files=files,
                data=data,
                timeout=120
            )

        if not response.ok:

            try:
                detail = response.json()
            except Exception:
                detail = response.text[:1000]

            print(
                "[BERON TRANSCRIPTION ERROR]",
                response.status_code,
                detail
            )

            return jsonify({
                "error": "Groq transcription request failed",
                "detail": detail
            }), 502

        result = response.json()

        text = str(
            result.get("text", "")
        ).strip()

        if not text:

            return jsonify({
                "error": "Groq returned an empty transcription"
            }), 502

        print(
            f"[BERON TRANSCRIPTION] {text}"
        )

        return jsonify({
            "text": text
        })

    except requests.RequestException as exc:

        print(
            f"[BERON TRANSCRIPTION REQUEST ERROR] {exc}"
        )

        return jsonify({
            "error": "Could not contact Groq transcription service",
            "detail": str(exc)
        }), 502

    except Exception as exc:

        print(
            f"[BERON TRANSCRIPTION ERROR] {type(exc).__name__}: {exc}"
        )

        return jsonify({
            "error": "Transcription failed",
            "detail": str(exc)
        }), 500

    finally:

        if temp_path:

            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass


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

    # The cloud backend DOES NOT execute arbitrary Windows
    # commands.
    #
    # The Windows client is responsible for local execution
    # after permission/security checks.

    return jsonify({
        "status": "received",
        "command": command_text,
        "execution": "pending_client_permission"
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error": "endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error": "internal server error"
    }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
