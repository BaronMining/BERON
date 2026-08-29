import os
import platform
import subprocess
import webbrowser
import psutil
from pathlib import Path

class WindowsTools:
    def __init__(self, permissions):
        self.permissions = permissions

    def open_app(self, app):
        allowed = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
        }
        command = allowed.get(app.lower())
        if not command:
            return "That application is not on BERON's safe launch list."
        subprocess.Popen(command, shell=True)
        return f"Opened {app}."

    def open_website(self, url):
        if not url.startswith(("https://", "http://")):
            return "I only open explicit HTTP/HTTPS web addresses."
        webbrowser.open(url)
        return "Opened the website."

    def system_status(self):
        return (
            f"Windows/PC status: CPU {psutil.cpu_percent()}%, "
            f"RAM {psutil.virtual_memory().percent}%, "
            f"disk {psutil.disk_usage(Path.home().anchor).percent}%."
        )

    def screenshot(self):
        if not self.permissions.confirm("Take a screenshot of the current screen?"):
            return "Screenshot cancelled."
        from PIL import ImageGrab
        path = Path("data") / "screenshots"
        path.mkdir(parents=True, exist_ok=True)
        file = path / "beron_latest.png"
        ImageGrab.grab().save(file)
        return f"Screenshot saved to {file}."
