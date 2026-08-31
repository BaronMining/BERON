import os
import requests

from memory.store import MemoryStore
from tools.registry import ToolRegistry


SYSTEM_PROMPT = """You are BERON, a personal AI assistant running on the user's Windows computer.

Be natural, intelligent, calm, useful and concise.

You can:
- Answer questions
- Have normal conversations
- Help with computer tasks
- Explain things
- Assist the user with their work
- Use approved tools when they are available

Never claim that you performed an action unless the application actually confirms it.

For dangerous, destructive, financial, security-sensitive, or irreversible actions,
require explicit confirmation from the user.

When the user simply talks to you, answer naturally.
"""


class Brain:
    def __init__(self, memory: MemoryStore, tools: ToolRegistry):
        self.memory = memory
        self.tools = tools

        self.backend_url = os.getenv(
            "BERON_BACKEND_URL",
            "https://beron-backend.onrender.com"
        ).rstrip("/")

        self.timeout = int(
            os.getenv("BERON_CHAT_TIMEOUT", "120")
        )

    def _backend_chat(self, messages):
        """
        Send the conversation to the BERON Render backend.

        The Render backend is responsible for talking to Groq.
        The Groq API key therefore stays on Render and is NOT
        stored on the Windows computer.
        """

        url = f"{self.backend_url}/api/chat"

        # Convert backend conversation into the format expected
        # by our Flask API.
        history = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "system":
                continue

            if role in ("user", "assistant") and isinstance(content, str):
                history.append({
                    "role": role,
                    "content": content
                })

        # The last user message is the actual current request.
        user_message = ""

        for message in reversed(messages):
            if message.get("role") == "user":
                user_message = str(
                    message.get("content", "")
                ).strip()
                break

        if not user_message:
            raise RuntimeError("No user message was provided.")

        # Don't duplicate the current user message in history.
        if history and history[-1].get("role") == "user":
            history = history[:-1]

        payload = {
            "message": user_message,
            "history": history[-20:]
        }

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout
        )

        # Give a useful error if Render returns an error.
        if response.status_code != 200:
            try:
                data = response.json()
            except Exception:
                data = response.text[:1000]

            raise RuntimeError(
                f"BERON backend returned HTTP "
                f"{response.status_code}: {data}"
            )

        data = response.json()

        answer = (
            data.get("message")
            or data.get("response")
            or data.get("answer")
            or ""
        )

        if not isinstance(answer, str):
            answer = str(answer)

        answer = answer.strip()

        if not answer:
            raise RuntimeError(
                "BERON backend returned an empty response."
            )

        return answer

    def respond(self, user_text: str) -> str:
        """
        Generate BERON's response.

        The Windows client talks to the Render backend.
        Render talks to Groq.
        """

        user_text = str(user_text).strip()

        if not user_text:
            return ""

        history = self.memory.recent(12)

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        # Add previous conversation.
        for item in history:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({
                    "role": role,
                    "content": content
                })

        # Add current message.
        messages.append({
            "role": "user",
            "content": user_text
        })

        try:
            return self._backend_chat(messages)

        except requests.Timeout:
            return (
                "I'm sorry, the BERON server took too long to respond."
            )

        except requests.ConnectionError:
            return (
                "I cannot connect to the BERON server right now. "
                "Please check your internet connection."
            )

        except Exception as exc:
            print(f"[BERON BRAIN ERROR] {exc}")

            return (
                "I heard you, but I couldn't get a response from "
                f"my AI brain. {exc}"
            )
