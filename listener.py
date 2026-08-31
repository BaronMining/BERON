import os
import tempfile
import requests
import speech_recognition as sr


class VoiceListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        self.wake_word = os.getenv(
            "BERON_WAKE_WORD",
            "beron"
        ).lower()

        self.language = os.getenv(
            "BERON_LANGUAGE",
            "en-US"
        )

        self.backend_url = os.getenv(
            "BERON_BACKEND_URL",
            "https://beron-backend.onrender.com"
        ).rstrip("/")

        self.listen_seconds = int(
            os.getenv("BERON_LISTEN_SECONDS", "5")
        )

    def record_audio(self):
        """
        Record microphone audio and return the SpeechRecognition
        AudioData object.
        """

        with sr.Microphone() as source:
            print(
                f"Listening for {self.listen_seconds} seconds..."
            )

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=0.5
            )

            audio = self.recognizer.listen(
                source,
                timeout=None,
                phrase_time_limit=self.listen_seconds
            )

        return audio

    def transcribe_local(self, audio):
        """
        Local fallback using Google's speech recognition service.
        """

        try:
            text = self.recognizer.recognize_google(
                audio,
                language=self.language
            )

            return text.strip()

        except sr.UnknownValueError:
            return ""

        except sr.RequestError as exc:
            print(f"Speech recognition error: {exc}")
            return ""

    def transcribe_backend(self, audio):
        """
        Send the recorded WAV audio to the BERON backend.

        IMPORTANT:
        The Flask backend expects the multipart field to be named
        'audio'.
        """

        temp_path = None

        try:
            wav_data = audio.get_wav_data()

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp_file:

                temp_file.write(wav_data)
                temp_path = temp_file.name

            with open(temp_path, "rb") as audio_file:

                response = requests.post(
                    f"{self.backend_url}/api/transcribe",

                    files={
                        "audio": (
                            "beron_audio.wav",
                            audio_file,
                            "audio/wav"
                        )
                    },

                    timeout=90
                )

            if response.status_code != 200:
                print(
                    f"Transcription endpoint returned "
                    f"{response.status_code}: {response.text}"
                )

                return ""

            data = response.json()

            text = (
                data.get("text")
                or data.get("transcription")
                or data.get("message")
                or ""
            )

            return str(text).strip()

        except requests.RequestException as exc:

            print(
                f"Could not connect to BERON transcription "
                f"service: {exc}"
            )

            return ""

        except Exception as exc:

            print(
                f"Transcription error: {exc}"
            )

            return ""

        finally:

            if temp_path and os.path.exists(temp_path):

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def listen(self):
        """
        Record audio and try the BERON backend first.

        If the backend transcription is unavailable,
        fall back to local SpeechRecognition.
        """

        audio = self.record_audio()

        # Try BERON backend first.
        text = self.transcribe_backend(audio)

        if text:
            return text

        # Local fallback.
        print("Backend transcription unavailable. Using local speech recognition...")

        return self.transcribe_local(audio)

    def listen_for_wake_and_command(self):
        """
        Wait for the wake word 'BERON'.

        Examples:

        'BERON'
        'BERON what is the weather'
        'Hey BERON'
        """

        try:
            text = self.listen().strip()

        except Exception as exc:

            print(
                f"Listening error: {exc}"
            )

            return None

        if not text:
            return None

        print(f"You: {text}")

        low = text.lower()

        # Wake word wasn't spoken.
        if self.wake_word not in low:
            return None

        # Extract anything said after BERON.
        command = low.split(
            self.wake_word,
            1
        )[1].strip(
            " ,.!?"
        )

        if command:
            return command

        # User only said "BERON".
        print("BERON is listening...")

        try:
            command = self.listen().strip()
        except Exception as exc:
            print(
                f"Command listening error: {exc}"
            )
            return None

        if not command:
            return None

        print(f"You: {command}")

        return command
