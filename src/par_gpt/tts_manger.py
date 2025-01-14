"""TTS Providers"""

import io
import os
from pathlib import Path
from typing import Any

import pyttsx3
from dotenv import load_dotenv
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from openai import OpenAI
from par_ai_core.par_logging import console_err
from rich.console import Console
from strenum import StrEnum


class TTSProvider(StrEnum):
    """Supported TTS Providers."""

    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"


class TTSManger:
    """Manages text-to-speech (TTS) using local, or Cloud APIs."""

    def __init__(
        self,
        tts_provider: TTSProvider,
        *,
        voice_name: str | None = None,
        verbose: bool = False,
        console: Console | None = None,
    ):
        """
        Initialize TTS manager.
        Args:
            tts_provider (TTSProvider): The TTS provider to use (local, elevenlabs, openai)
            voice_name (str | None): The voice name to use (default: None for default)
            verbose (bool): Whether to print verbose output (default: False)
            console (Console | None): The console to use for output
        """
        self.console = console or console_err
        self.verbose = verbose

        # Get voice configuration
        self.tts_provider = tts_provider
        self.voice_name = ""
        # Initialize appropriate TTS engine
        if self.tts_provider == TTSProvider.LOCAL:
            if self.verbose:
                self.console.print("🔊 Initializing local TTS engine")
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 150)  # Speed of speech
            self.engine.setProperty("volume", 1.0)  # Volume level
            if voice_name:
                voice = [v for v in self.engine.getProperty("voices") if v.name == self.voice_name]
                if voice:
                    self.engine.setProperty("voice", voice[0].id)
                    self.voice_name = voice[0].name
        elif self.tts_provider == TTSProvider.ELEVENLABS:
            if self.verbose:
                self.console.print("🔊 Initializing ElevenLabs TTS engine")
            self.engine = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
            if not voice_name:
                voice_name = "XrExE9yKIg1WjnnlVkGX"  # Matilda   "XB0fDUnXU5powFXDhCwa"  # Charlotte
            self.voice_name = voice_name
        elif self.tts_provider == TTSProvider.OPENAI:
            self.engine = OpenAI()
            if not voice_name:
                voice_name = "nova"
            self.voice_name = voice_name
        else:
            raise ValueError(f"Unsupported voice type: {self.tts_provider}")

        if not self.voice_name:
            raise ValueError("Default voice not found for TTS provider, please provide a voice name.")

    def list_voices(self) -> list[Any]:
        """
        List available voices for the configured TTS provider

        Returns:
            list[Any]: Available voices for the configured TTS provider
        """
        if self.tts_provider == TTSProvider.LOCAL:
            return self.engine.getProperty("voices")  # type: ignore
        elif self.tts_provider == TTSProvider.ELEVENLABS:
            # return self.engine.voices.get_all().voices
            return [
                f"{v.name} - {v.voice_id} - {','.join((v.labels or {}).values())}"
                for v in self.engine.voices.get_all().voices  # type: ignore
            ]
        elif self.tts_provider == TTSProvider.OPENAI:
            return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        raise ValueError(f"Unsupported voice type: {self.tts_provider}")

    def speak(self, text: str) -> None:
        """
        Convert text to speech using configured engine

        Args:
            text (str): Text to convert to speech

        Returns:
            None
        """
        try:
            if self.verbose:
                self.console.print(f"🔊 Speaking: {text}")

            if self.tts_provider == TTSProvider.LOCAL:
                self.engine.say(text)  # type: ignore
                self.engine.runAndWait()  # type: ignore
            elif self.tts_provider == TTSProvider.ELEVENLABS:
                audio = self.engine.generate(  # type: ignore
                    text=text,
                    voice=self.voice_name,
                    model="eleven_turbo_v2",
                    stream=False,
                )
                play(audio)
            elif self.tts_provider == TTSProvider.OPENAI:
                response = self.engine.audio.speech.create(  # type: ignore
                    model="tts-1-hd",
                    voice=self.voice_name,  # type: ignore
                    input=text,
                )
                buffer = io.BytesIO()
                for chunk in response.iter_bytes(chunk_size=4096):
                    buffer.write(chunk)
                buffer.seek(0)
                play(buffer.getvalue())

            # if self.verbose:
            # self.console.print(f"🔊 Spoken: {text}")

        except Exception as e:
            self.console.print(f"❌ Error in speech synthesis: {str(e)}")
            raise


if __name__ == "__main__":
    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # sm = SpeechManger(SpeechType.LOCAL, voice_name='Shelley (English (UK))')
    sm = TTSManger(TTSProvider.ELEVENLABS, voice_name="XrExE9yKIg1WjnnlVkGX")
    # sm = SpeechManger(SpeechType.OPENAI, voice_name="nova")
    # Console().print(sm.list_voices())
    sm.speak("Hello Paul. What can I do for you today?")
