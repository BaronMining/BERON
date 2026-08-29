from tools.windows import WindowsTools

class ToolRegistry:
    def __init__(self, permissions):
        self.permissions = permissions
        self.windows = WindowsTools(permissions)

    def available(self):
        return ["open_app", "open_website", "system_status", "screenshot"]
