import os

class PermissionManager:
    def __init__(self):
        self.require_confirmation = (
            os.getenv("BERON_REQUIRE_CONFIRMATION", "true").lower() == "true"
        )

    def confirm(self, message):
        if not self.require_confirmation:
            return True
        answer = input(f"\nBERON CONFIRMATION: {message} [y/N] ").strip().lower()
        return answer in ("y", "yes")
