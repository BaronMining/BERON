from voice.listener import VoiceListener
from voice.speaker import Speaker
from core.brain import Brain
from memory.store import MemoryStore
from tools.registry import ToolRegistry
from security.permissions import PermissionManager


class BERON:

    def __init__(self):
        print("[BERON] Initializing...")

        self.memory = MemoryStore()

        self.speaker = Speaker()

        self.permissions = PermissionManager()

        self.tools = ToolRegistry(
            self.permissions
        )

        self.brain = Brain(
            self.memory,
            self.tools
        )

        self.listener = VoiceListener()

        print("[BERON] Initialization complete.")

    def handle(self, text: str):

        text = str(text).strip()

        if not text:
            return

        print(f"You: {text}")

        # Save user message.
        self.memory.add(
            "user",
            text
        )

        # Ask the AI.
        result = self.brain.respond(text)

        if not result:
            print("[BERON] Empty response.")
            return

        print(f"BERON: {result}")

        # Save AI response.
        self.memory.add(
            "assistant",
            result
        )

        # Speak the answer.
        self.speaker.say(result)

    def run(self):

        self.speaker.say(
            "BERON is online. I am listening."
        )

        while True:

            try:

                text = (
                    self.listener
                    .listen_for_wake_and_command()
                )

                if text:
                    self.handle(text)

            except KeyboardInterrupt:

                print(
                    "[BERON] Shutting down."
                )

                self.speaker.say(
                    "BERON shutting down."
                )

                break

            except Exception as exc:

                print(
                    f"[BERON ERROR] {exc}"
                )

                self.speaker.say(
                    "I encountered an error, "
                    "but I am still online."
                )
