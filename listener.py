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
        ).lower().strip()

        self.language = os.getenv(
            "BERON_LANGUAGE",
            "en-US"
        )

        self.backend_url = os.getenv(
            "BERON_BACKEND_URL",
            "https://beron-backend.onrender.com"
        ).rstrip("/")

        self.listen_seconds = int(
            os.getenv(
                "BERON_LISTEN_SECONDS",
                "5"
            )
        )

        # Prevent the microphone from being too sensitive.
        self.recognizer.energy_threshold = 300

        self.recognizer.dynamic_energy_threshold = True

        self.recognizer.pause_threshold = 0.8

        self.recognizer.phrase_threshold = 0.3

        self.recognizer.non_speaking_duration = 0.5

    def record_audio(self):

        with sr.Microphone() as source:

            print(
                f"Listening for {self.listen_seconds} seconds..."
            )

            try:
                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=0.5
                )
            except Exception as exc:
                print(
                    f"Microphone calibration warning: {exc}"
                )

            audio = self.recognizer.listen(
                source,
                timeout=None,
                phrase_time_limit=self.listen_seconds
            )

        return audio

    def transcribe_backend(self, audio):

        temp_path = None

        try:

            wav_data = audio.get_wav_data()

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp_file:

                temp_file.write(wav_data)

                temp_path = temp_file.name

            with open(
                temp_path,
                "rb"
            ) as audio_file:

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
                    "Transcription endpoint returned "
                    f"{response.status_code}: "
                    f"{response.text[:1000]}"
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
                f"Backend transcription connection error: {exc}"
            )

            return ""

        except Exception as exc:

            print(
                f"Backend transcription error: {exc}"
            )

            return ""

        finally:

            if (
                temp_path
                and os.path.exists(temp_path)
            ):

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def transcribe_local(self, audio):

        try:

            text = self.recognizer.recognize_google(
                audio,
                language=self.language
            )

            return text.strip()

        except sr.UnknownValueError:

            return ""

        except sr.RequestError as exc:

            print(
                f"Local speech recognition error: {exc}"
            )

            return ""

        except Exception as exc:

            print(
                f"Local transcription error: {exc}"
            )

            return ""

    def listen(self):

        audio = self.record_audio()

        # First use the BERON/Groq transcription service.
        text = self.transcribe_backend(audio)

        if text:

            return text

        # Local fallback.
        print(
            "Backend transcription unavailable. "
            "Using local speech recognition..."
        )

        return self.transcribe_local(audio)

    def listen_for_wake_and_command(self):

        try:

            text = self.listen().strip()

        except Exception as exc:

            print(
                f"Listening error: {exc}"
            )

            return None

        if not text:

            return None

        print(
            f"Heard: {text}"
        )

        low = text.lower()

        # Check whether BERON was called.
        if self.wake_word not in low:

            return None

        # Everything after the wake word.
        command = low.split(
            self.wake_word,
            1
        )[1].strip(
            " ,.!?"
        )

        # Example:
        #
        # "Hey BERON how are you?"
        #
        # becomes:
        #
        # "how are you?"

        if command:

            return command

        # User only said:
        #
        # "BERON"

        print(
            "BERON is listening..."
        )

        try:

            command = self.listen().strip()

        except Exception as exc:

            print(
                f"Command listening error: {exc}"
            )

            return None

        if not command:

            return None

        print(
            f"Heard command: {command}"
        )

        return command
