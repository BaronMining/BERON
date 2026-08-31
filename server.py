import os
import tempfile
from pathlib import Path

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

GROQ_CHAT_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_TRANSCRIPTION_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

# ============================================================
# BERON PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are BERON, a personal AI assistant running for the user.

Your personality:
- Intelligent
- Calm
- Natural
- Helpful
- Friendly
- Direct
- Honest

You are designed to work as a voice assistant.

Keep normal answers reasonably concise because your responses
may be spoken aloud.

Never claim that you performed an action unless the application
actually confirms that the action was performed.

For computer-control actions, ask for confirmation when an
action could be destructive, financial, security-sensitive,
or irreversible.
"""

# ============================================================
# BASIC ROUTES
# ============================================================

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
        "status": "healthy",
        "groq_configured": bool(GROQ_API_KEY)
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
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        },
        timeout=90
    )

    if not response.ok:
        try:
            provider_error = response.json()
        except Exception:
            provider_error = response.text[:1000]

        raise RuntimeError(
            f"Groq chat request failed "
            f"(HTTP {response.status_code}): {provider_error}"
        )

    data = response.json()

    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            f"Groq returned no choices: {data}"
        )

    message = choices[0].get("message", {})
    content = message.get("content")

    if not content:
        raise RuntimeError(
            f"Groq returned an empty response: {data}"
        )

    return str(content).strip()


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post("/api/chat")
def chat():

    try:
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

        # Keep the conversation bounded.
        for item in history[-20:]:

            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role not in ("user", "assistant"):
                continue

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            messages.append({
                "role": role,
                "content": content[:8000]
            })

        messages.append({
            "role": "user",
            "content": message
        })

        answer = ask_groq(messages)

        return jsonify({
            "assistant": APP_NAME,
            "message": answer
        })

    except Exception as exc:

        print(
            f"[BERON CHAT ERROR] {type(exc).__name__}: {exc}",
            flush=True
        )

        return jsonify({
            "error": "BERON could not process the request",
            "detail": str(exc)
        }), 502


# ============================================================
# AUDIO TRANSCRIPTION
# ============================================================

@app.post("/api/transcribe")
def transcribe():

    temp_path = None

    try:

        # ----------------------------------------------------
        # Check API key
        # ----------------------------------------------------

        if not GROQ_API_KEY:
            return jsonify({
                "error": "BERON_GROQ_API_KEY is not configured on Render."
            }), 500

        # ----------------------------------------------------
        # Accept several possible field names.
        #
        # This prevents the client/server mismatch that caused
        # the previous "audio file is required" error.
        # ----------------------------------------------------

        audio_file = (
            request.files.get("audio")
            or request.files.get("file")
            or request.files.get("audio_file")
        )

        if audio_file is None:
            print(
                "[BERON TRANSCRIBE] No audio file received.",
                flush=True
            )

            return jsonify({
                "error": "audio file is required",
                "received_fields": list(request.files.keys())
            }), 400

        if not audio_file.filename:
            return jsonify({
                "error": "audio filename is missing"
            }), 400

        # ----------------------------------------------------
        # Save uploaded audio temporarily.
        # ----------------------------------------------------

        original_name = Path(
            audio_file.filename
        ).name

        suffix = Path(original_name).suffix.lower()

        if not suffix:
            suffix = ".wav"

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            temp_path = temp_file.name
            audio_file.save(temp_path)

        # ----------------------------------------------------
        # Make sure the file actually contains data.
        # ----------------------------------------------------

        file_size = os.path.getsize(temp_path)

        if file_size <= 0:
            return jsonify({
                "error": "received audio file is empty"
            }), 400

        print(
            f"[BERON TRANSCRIBE] Received "
            f"{original_name} ({file_size} bytes)",
            flush=True
        )

        # ----------------------------------------------------
        # Send audio to Groq Whisper.
        # ----------------------------------------------------

        with open(temp_path, "rb") as audio:

            response = requests.post(
                GROQ_TRANSCRIPTION_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                files={
                    "file": (
                        original_name,
                        audio,
                        "application/octet-stream"
                    )
                },
                data={
                    "model": GROQ_TRANSCRIPTION_MODEL,
                    "response_format": "json",
                    "language": "en",
                    "temperature": "0"
                },
                timeout=120
            )

        # ----------------------------------------------------
        # Handle Groq HTTP errors.
        # ----------------------------------------------------

        if not response.ok:

            try:
                provider_error = response.json()
            except Exception:
                provider_error = response.text[:1000]

            print(
                f"[BERON TRANSCRIBE] Groq error "
                f"{response.status_code}: {provider_error}",
                flush=True
            )

            return jsonify({
                "error": "Groq transcription request failed",
                "status_code": response.status_code,
                "detail": provider_error
            }), 502

        # ----------------------------------------------------
        # Parse Groq response.
        # ----------------------------------------------------

        try:
            data = response.json()
        except Exception:

            return jsonify({
                "error": "Groq returned invalid JSON",
                "detail": response.text[:1000]
            }), 502

        text = data.get("text", "")

        if not isinstance(text, str):
            text = str(text)

        text = text.strip()

        if not text:
            return jsonify({
                "error": "Groq returned an empty transcription",
                "provider_response": data
            }), 502

        print(
            f"[BERON TRANSCRIBE] Text: {text}",
            flush=True
        )

        return jsonify({
            "text": text,
            "transcript": text
        })

    except Exception as exc:

        print(
            f"[BERON TRANSCRIBE ERROR] "
            f"{type(exc).__name__}: {exc}",
            flush=True
        )

        return jsonify({
            "error": "BERON transcription failed",
            "detail": str(exc)
        }), 500

    finally:

        # ----------------------------------------------------
        # Always remove temporary audio.
        # ----------------------------------------------------

        if temp_path:

            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as cleanup_error:

                print(
                    f"[BERON CLEANUP ERROR] "
                    f"{cleanup_error}",
                    flush=True
                )


# ============================================================
# COMPUTER COMMAND ENDPOINT
# ============================================================

@app.post("/api/command")
def command():

    try:

        body = request.get_json(silent=True) or {}

        command_text = str(
            body.get("command", "")
        ).strip()

        if not command_text:
            return jsonify({
                "error": "command is required"
            }), 400

        # The cloud backend does NOT execute arbitrary commands.
        # The Windows client will later validate and execute
        # approved commands locally.

        return jsonify({
            "status": "received",
            "command": command_text,
            "execution": "pending_client_permission"
        })

    except Exception as exc:

        return jsonify({
            "error": "command processing failed",
            "detail": str(exc)
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
```
