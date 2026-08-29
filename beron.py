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
        if not text.strip():
            return
        self.memory.add("user", text)
        result = self.brain.respond(text)
        self.memory.add("assistant", result)
        self.speaker.say(result)

    def run(self):
        self.speaker.say("BERON is online.")
        while True:
            try:
                text = self.listener.listen_for_wake_and_command()
                if text:
                    self.handle(text)
            except KeyboardInterrupt:
                self.speaker.say("BERON shutting down.")
                break
            except Exception as exc:
                print(f"[BERON ERROR] {exc}")
                self.speaker.say("I encountered an error, but I am still online.")
