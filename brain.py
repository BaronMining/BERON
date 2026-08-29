import os
import requests
from memory.store import MemoryStore
from tools.registry import ToolRegistry

SYSTEM_PROMPT = """You are BERON, a personal AI assistant.
Be natural, calm, useful and honest. Never claim to have performed an action
unless the tool actually succeeded. Use tools when appropriate. For dangerous
or destructive actions, ask for confirmation through the security layer.
You can remember information only when the memory system explicitly stores it.
Keep ordinary replies concise unless the user asks for detail.
"""

class Brain:
    def __init__(self, memory: MemoryStore, tools: ToolRegistry):
        self.memory = memory
        self.tools = tools
        self.provider = os.getenv("BERON_AI_PROVIDER", "ollama").lower()

    def _ollama(self, messages):
        url = os.getenv("BERON_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        model = os.getenv("BERON_OLLAMA_MODEL", "llama3.2")
        r = requests.post(
            f"{url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    def _openai_compatible(self, messages):
        key = os.getenv("BERON_OPENAI_API_KEY")
        model = os.getenv("BERON_OPENAI_MODEL")
        if not key or not model:
            raise RuntimeError("OpenAI-compatible provider is not configured.")
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": messages},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def respond(self, user_text: str) -> str:
        history = self.memory.recent(12)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        try:
            if self.provider == "openai":
                return self._openai_compatible(messages)
            return self._ollama(messages)
        except Exception as exc:
            return (
                "My AI brain is not connected right now. "
                f"Please check the configured provider. Details: {exc}"
            )
