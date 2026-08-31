import time
from voice.listener import VoiceListener
from voice.speaker import Speaker
from core.brain import Brain
from memory.store import MemoryStore
from tools.registry import ToolRegistry
from security.permissions import PermissionManager


class BERON:
    def __init__(self):
        self.memory = MemoryStore()
        self.speaker = Speaker()
        self.permissions = PermissionManager()
        self.tools = ToolRegistry(self.permissions)
        self.brain = Brain(self.memory, self.tools)
        self.listener = VoiceListener()

    def handle(self, text: str):
        text = text.strip()

        if not text:
            return

        print(f"[BERON] Processing: {text}")

        try:
            self.memory.add("user", text)

            print("[BERON] Sending to brain...")

            result = self.brain.respond(text)

            if not result:
                result = "I heard you, but I didn't receive a response."

            result = str(result).strip()

            print(f"[BERON] Reply: {result}")

            self.memory.add("assistant", result)

            print("[BERON] Speaking...")

            self.speaker.say(result)

            print("[BERON] Done speaking.")

        except Exception as exc:
            print(f"[BERON ERROR] {type(exc).__name__}: {exc}")

            try:
                self.speaker.say(
                    "I heard you, but I had a problem processing that."
                )
            except Exception:
                pass

    def run(self):
        print("[BERON] Starting...")

        try:
            self.speaker.say("BERON is online. I am listening.")
        except Exception as exc:
            print(f"[SPEAKER ERROR] {exc}")

        while True:
            try:
                text = self.listener.listen_for_wake_and_command()

                if text:
                    self.handle(text)

                time.sleep(0.1)

            except KeyboardInterrupt:
                print("[BERON] Shutting down.")

                try:
                    self.speaker.say("BERON shutting down.")
                except Exception:
                    pass

                break

            except Exception as exc:
                print(f"[BERON LOOP ERROR] {type(exc).__name__}: {exc}")
                time.sleep(1)
