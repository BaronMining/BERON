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

GROQ_CHAT_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_AUDIO_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)


# ============================================================
# BERON PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are BERON, a personal AI assistant running for the user.

Be intelligent, calm, natural, helpful and honest.

Speak naturally as a helpful personal assistant.

Do not claim that you performed an action unless the application
actually confirms that the action was completed.

You can help the user understand information, plan tasks,
write things, troubleshoot computers and applications, and
suggest actions.

For destructive, financial, security-sensitive, or irreversible
actions, require explicit confirmation before execution.

Keep ordinary answers reasonably concise because your responses
may be spoken aloud by the Windows voice client.
""".strip()


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
        "status": "healthy"
    })


# ============================================================
# INTERNAL HELPERS
# ============================================================

def require_groq_key():
    """
    Make sure the Groq API key exists before calling Groq.
    """

    if not GROQ_API_KEY:
        raise RuntimeError(
            "BERON_GROQ_API_KEY is not configured on Render."
        )


def groq_headers():
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }


# ============================================================
# GROQ CHAT
# ============================================================

def ask_groq(messages):
    """
    Send a conversation to Groq and return BERON's response.
    """

    require_groq_key()

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
        },
        timeout=90,
    )

    # Keep useful provider errors for debugging.
    if not response.ok:
        try:
            provider_error = response.json()
        except Exception:
            provider_error = response.text[:1000]

        raise RuntimeError(
            f"Groq chat request failed: {provider_error}"
        )

    data = response.json()

    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            "Groq returned no choices."
        )

    message = choices[0].get("message", {})
    answer = message.get("content")

    if not isinstance(answer, str) or not answer.strip():
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

    # --------------------------------------------------------
    # Add recent conversation history.
    # --------------------------------------------------------

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

        # Prevent extremely large requests.
        messages.append({
            "role": role,
            "content": content[:8000]
        })

    # Current user message.
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

    except RuntimeError as exc:

        print(f"[BERON CHAT ERROR] {exc}")

        return jsonify({
            "error": "AI provider request failed",
            "detail": str(exc)
        }), 502

    except requests.RequestException as exc:

        print(f"[BERON NETWORK ERROR] {exc}")

        return jsonify({
            "error": "AI provider request failed",
            "detail": "Could not connect to Groq."
        }), 502

    except Exception as exc:

        print(f"[BERON CHAT ERROR] {exc}")

        return jsonify({
            "error": "BERON could not process the request",
            "detail": str(exc)
        }), 500


# ============================================================
# AUDIO TRANSCRIPTION
# ============================================================

@app.post("/api/transcribe")
def transcribe():

    require_groq_key()

    # --------------------------------------------------------
    # The Windows client must send the audio as multipart/form-data
    # using the field name "audio".
    # --------------------------------------------------------

    audio_file = request.files.get("audio")

    if audio_file is None:

        return jsonify({
            "error": "audio file is required"
        }), 400

    if not audio_file.filename:

        return jsonify({
            "error": "audio filename is required"
        }), 400

    temp_path = None

    try:

        # ----------------------------------------------------
        # Save uploaded audio temporarily.
        # ----------------------------------------------------

        suffix = os.path.splitext(
            audio_file.filename
        )[1].lower()

        if not suffix:
            suffix = ".wav"

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp:

            temp_path = temp.name

            audio_file.save(temp_path)

        # ----------------------------------------------------
        # Send audio to Groq Whisper.
        # ----------------------------------------------------

        with open(temp_path, "rb") as audio:

            response = requests.post(
                GROQ_AUDIO_URL,
                headers=groq_headers(),
                files={
                    "file": (
                        os.path.basename(temp_path),
                        audio,
                        "application/octet-stream"
                    )
                },
                data={
                    "model": GROQ_TRANSCRIPTION_MODEL
                },
                timeout=120,
            )

        # ----------------------------------------------------
        # Handle Groq errors.
        # ----------------------------------------------------

        if not response.ok:

            try:
                provider_error = response.json()
            except Exception:
                provider_error = response.text[:1000]

            print(
                f"[BERON TRANSCRIPTION ERROR] "
                f"{provider_error}"
            )

            return jsonify({
                "error": "Groq transcription request failed",
                "detail": provider_error
            }), 502

        data = response.json()

        text = data.get("text", "")

        if not isinstance(text, str):
            text = str(text)

        text = text.strip()

        if not text:

            return jsonify({
                "error": "No speech was detected"
            }), 422

        print(f"[BERON TRANSCRIPTION] {text}")

        return jsonify({
            "text": text,
            "transcription": text
        })

    except requests.RequestException as exc:

        print(
            f"[BERON TRANSCRIPTION NETWORK ERROR] "
            f"{exc}"
        )

        return jsonify({
            "error": "Could not connect to Groq transcription service",
            "detail": str(exc)
        }), 502

    except Exception as exc:

        print(
            f"[BERON TRANSCRIPTION ERROR] "
            f"{exc}"
        )

        return jsonify({
            "error": "BERON transcription failed",
            "detail": str(exc)
        }), 500

    finally:

        # ----------------------------------------------------
        # Always remove temporary audio file.
        # ----------------------------------------------------

        if temp_path:

            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as exc:
                print(
                    f"[BERON CLEANUP WARNING] {exc}"
                )


# ============================================================
# COMMAND ENDPOINT
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

    # --------------------------------------------------------
    # The cloud backend does NOT execute arbitrary commands
    # on the user's Windows computer.
    #
    # The Windows client can later receive approved commands
    # and request local permission before executing them.
    # --------------------------------------------------------

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
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "error": "Method not allowed"
    }), 405


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
