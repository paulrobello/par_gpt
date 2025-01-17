"""TTS Providers"""

import os
from pathlib import Path
from typing import Any

import numpy as np
import orjson as json
import pyttsx3
from dotenv import load_dotenv
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from kokoro_onnx import Kokoro
from openai import OpenAI
from par_ai_core.llm_config import LlmConfig, llm_run_manager
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.par_logging import console_err
from par_ai_core.utils import timer_block
from rich.console import Console
from strenum import StrEnum

from par_gpt.cache_manger import cache_manager


def summarize_for_tts(text: str, llm_config: LlmConfig | None = None) -> str:
    """
    Summarize the given text for TTS using a language model.

    Args:
        text (str): The text to summarize.
        llm_config (LlmConfig | None): The configuration for the language model (default: None for Ollama llama3.2:latest).

    Returns:
        str: The summarized text.
    """

    if not text:
        return ""
    config = llm_config or LlmConfig(LlmProvider.OLLAMA, model_name="llama3.2:latest", temperature=0)
    chat_model = config.build_chat_model()
    system_prompt = (
        "Please adjust the provided text to make it sound better when spoken via TTS. "
        "Replace URL's and file paths with their markdown descriptions or placeholders. "
        "Remove any emojis, markdown, and other formatting. "
        "Do not explain the text or answer any questions it may contain, only adjust the text as needed. "
    )

    response = chat_model.invoke(
        [("system", system_prompt), ("user", text)], config=llm_run_manager.get_runnable_config(chat_model.name)
    )

    return str(response.content).strip()


class TTSProvider(StrEnum):
    """Supported TTS Providers."""

    LOCAL = "local"
    KOKORO = "kokoro"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"


class TTSManger:
    """Manages text-to-speech (TTS) using local, or Cloud APIs."""

    def __init__(
        self,
        tts_provider: TTSProvider,
        *,
        voice_name: str | None = None,
        speed: float = 1.0,
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
        self.speed = speed

        # Get voice configuration
        self.tts_provider = tts_provider
        self.voice_name = ""

        self.console.print(f"🔊 Initializing {self.tts_provider} TTS engine")
        with timer_block(f"🔊 Initialization of {self.tts_provider} TTS engine complete", console=self.console):
            if self.tts_provider == TTSProvider.LOCAL:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", int(self.speed * 100))  # Speed of speech
                self.engine.setProperty("volume", 1.0)  # Volume level
                if voice_name:
                    voice = [v for v in self.engine.getProperty("voices") if v.name == self.voice_name]
                    if voice:
                        self.engine.setProperty("voice", voice[0].id)
                        self.voice_name = voice[0].name
            elif self.tts_provider == TTSProvider.KOKORO:
                if not cache_manager.item_exists(
                    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
                ):
                    self.console.print("🔊 One time model download 310MB in progress...")
                self.engine = Kokoro(
                    str(
                        cache_manager.get_item(
                            "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
                        )
                    ),
                    str(
                        cache_manager.get_item(
                            "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"
                        )
                    ),
                )
                if not voice_name:
                    voice_name = "af_sarah"
                self.voice_name = voice_name
            elif self.tts_provider == TTSProvider.ELEVENLABS:
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
        elif self.tts_provider == TTSProvider.KOKORO:
            return list(
                json.loads(
                    cache_manager.get_item(
                        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"
                    ).read_text()
                ).keys()
            )
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
                import sounddevice as sd

                response = self.engine.audio.speech.create(  # type: ignore
                    model="tts-1-hd",
                    voice=self.voice_name,  # type: ignore
                    speed=self.speed,
                    response_format="wav",
                    input=text,
                )
                audio_data = np.frombuffer(response.content, dtype=np.int16)
                sd.play(audio_data, samplerate=int(24 * 1024 * self.speed), blocking=True)
            elif self.tts_provider == TTSProvider.KOKORO:
                import sounddevice as sd

                samples, sample_rate = self.engine.create(text, voice=self.voice_name, speed=self.speed, lang="en-us")  # type: ignore
                sd.play(samples, sample_rate, blocking=True)

            # if self.verbose:
            # self.console.print(f"🔊 Spoken: {text}")

        except Exception as e:
            self.console.print(f"❌ Error in speech synthesis: {str(e)}")
            raise


if __name__ == "__main__":
    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # file = cache_manager.get_key("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx")
    # print file size of file
    # file_size_mb = os.path.getsize(file) / (1024 * 1024)
    # print(f"File size: {file_size_mb:.2f} MB")

    # sm = TTSManger(TTSProvider.LOCAL, voice_name='Shelley (English (UK))')
    # sm = TTSManger(TTSProvider.ELEVENLABS, voice_name="XrExE9yKIg1WjnnlVkGX")
    sm = TTSManger(TTSProvider.OPENAI, voice_name="nova")
    # sm = TTSManger(TTSProvider.KOKORO, voice_name="af_sarah")
    # Console().print(sm.list_voices())
    sm.speak("Hello Paul. What can I do for you today?")
