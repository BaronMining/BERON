import os
import speech_recognition as sr

class VoiceListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.wake_word = os.getenv("BERON_WAKE_WORD", "beron").lower()
        self.language = os.getenv("BERON_LANGUAGE", "en-US")

    def listen(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source, phrase_time_limit=12)
        return self.recognizer.recognize_google(audio, language=self.language)

    def listen_for_wake_and_command(self):
        text = self.listen().strip()
        print(f"You: {text}")
        low = text.lower()

        if self.wake_word not in low:
            return None

        command = low.split(self.wake_word, 1)[1].strip(" ,.!?")
        if command:
            return command

        print("BERON is listening...")
        return self.listen().strip()
