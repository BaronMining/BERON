import os
import requests

from memory.store import MemoryStore
from tools.registry import ToolRegistry


class Brain:
    def __init__(self, memory: MemoryStore, tools: ToolRegistry):
        self.memory = memory
        self.tools = tools

        self.backend_url = os.getenv(
            "BERON_BACKEND_URL",
            "https://beron-backend.onrender.com"
        ).rstrip("/")

        self.timeout = int(
            os.getenv("BERON_BACKEND_TIMEOUT", "120")
        )

    def respond(self, user_text: str) -> str:
        user_text = str(user_text).strip()

        if not user_text:
            return ""

        history = self.memory.recent(12)

        # Convert stored memory into the format expected by the backend.
        clean_history = []

        for item in history:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role in ("user", "assistant") and isinstance(content, str):
                clean_history.append({
                    "role": role,
                    "content": content[:8000]
                })

        payload = {
            "message": user_text,
            "history": clean_history
        }

        try:
            response = requests.post(
                f"{self.backend_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            answer = data.get("message")

            if not answer:
                return "I received an empty response from my AI brain."

            return str(answer).strip()

        except requests.Timeout:
            return (
                "My AI brain is taking too long to respond. "
                "Please try again."
            )

        except requests.ConnectionError:
            return (
                "I cannot connect to my BERON backend right now."
            )

        except requests.HTTPError as exc:
            try:
                data = exc.response.json()
                detail = data.get("detail") or data.get("error")

                if isinstance(detail, dict):
                    detail = str(detail)

                if detail:
                    print(f"[BERON BACKEND ERROR] {detail}")

            except Exception:
                pass

            return (
                "My AI brain returned an error. "
                "Please check the BERON backend."
            )

        except Exception as exc:
            print(f"[BERON BRAIN ERROR] {exc}")

            return (
                "I encountered a problem connecting to my AI brain."
            )
