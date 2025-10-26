"""TTS Providers with proper memory management and resource cleanup."""

import os
import re
import weakref
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import orjson as json
from dotenv import load_dotenv
from par_ai_core.llm_config import LlmConfig, llm_run_manager
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.par_logging import console_err
from par_ai_core.utils import timer_block
from rich.console import Console
from strenum import StrEnum

from par_utils import CacheManager, LazyImportManager

# Create instances for backward compatibility
cache_manager = CacheManager()
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


def summarize_for_tts(text: str) -> str:
    """
    Summarize the given text for TTS.

    Args:
        text (str): The text to summarize.

    Returns:
        str: The summarized text.
    """
    if not text:
        return ""
    summary = text.strip().replace("**", "")

    # Regular expression to match POSIX file paths
    path_pattern = re.compile(r"(?:/[^/\s]+)+/?")

    # Regular expression to match URLs
    url_pattern = re.compile(r"\(?http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    # Replace URLs with the word "URL"
    summary = url_pattern.sub(" URL", summary)

    # Replace POSIX file paths with the word "PATH"
    summary = path_pattern.sub(" PATH", summary)

    return summary


def summarize_for_tts_llm(text: str, llm_config: LlmConfig | None = None) -> str:
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
        "DO NOT explain the text or answer any questions it may contain, only adjust the text as needed. "
        "DO NOT include a preamble or introduction before the text.\n"
        "Examples:\n"
        "Input: I have shown the image in the terminal\n"
        "Output: I have shown the image in the terminal\n"
        "Input: I have fetched data from https://google.com/search\n"
        "Output: I have fetched data from the URL\n"
        "Input: This text is **BOLD**\n"
        "Output: This text is BOLD\n"
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
    """Manages text-to-speech (TTS) using local, or Cloud APIs with proper memory management."""

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
        self.engine: Any = None
        self._audio_streams: list[Any] = []  # Track audio streams for cleanup

        # Get voice configuration
        self.tts_provider = tts_provider
        self.voice_name = ""

        # Register cleanup on deletion
        weakref.finalize(self, self._cleanup_resources)

        self.console.print(f"🔊 Initializing {self.tts_provider} TTS engine")
        with timer_block(f"🔊 Initialization of {self.tts_provider} TTS engine complete", console=self.console):
            if self.tts_provider == TTSProvider.LOCAL:
                # Lazy load pyttsx3
                pyttsx3 = lazy_import("pyttsx3")
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
                # Lazy load Kokoro
                Kokoro = lazy_import("kokoro_onnx", "Kokoro")
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
                # Lazy load ElevenLabs
                ElevenLabs = lazy_import("elevenlabs.client", "ElevenLabs")
                self.engine = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
                if not voice_name:
                    voice_name = "XrExE9yKIg1WjnnlVkGX"  # Matilda   "XB0fDUnXU5powFXDhCwa"  # Charlotte
                self.voice_name = voice_name
            elif self.tts_provider == TTSProvider.OPENAI:
                # Lazy load OpenAI
                OpenAI = lazy_import("openai", "OpenAI")
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

    def speak(self, text: str, do_async: bool = False) -> None:
        """
        Convert text to speech using configured engine

        Args:
            text (str): Text to convert to speech
            do_async (bool): Whether to speak asynchronously (default: False)

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
                # Lazy load elevenlabs play
                play = lazy_import("elevenlabs", "play")
                play(audio)
            elif self.tts_provider == TTSProvider.OPENAI:
                import sounddevice as sd

                audio_response = self.engine.audio.speech.create(  # type: ignore
                    model="tts-1-hd",
                    voice=self.voice_name,  # type: ignore
                    speed=self.speed,
                    response_format="wav",
                    input=text,
                )
                # Lazy load numpy
                np = lazy_import("numpy")
                audio_data = np.frombuffer(audio_response.content, dtype=np.int16)

                # Play with proper cleanup
                try:
                    sd.play(audio_data, samplerate=int(24 * 1024 * self.speed), blocking=True)
                finally:
                    # Ensure audio buffer is released
                    del audio_data

            elif self.tts_provider == TTSProvider.KOKORO:
                import sounddevice as sd

                samples, sample_rate = self.engine.create(text, voice=self.voice_name, speed=self.speed, lang="en-us")  # type: ignore

                # Play with proper cleanup
                try:
                    sd.play(samples, sample_rate, blocking=True)
                finally:
                    # Ensure audio samples are released
                    del samples

            # if self.verbose:
            # self.console.print(f"🔊 Spoken: {text}")

        except Exception as e:
            self.console.print(f"❌ Error in speech synthesis: {str(e)}")
            raise

    def _cleanup_resources(self) -> None:
        """Clean up TTS resources to prevent memory leaks."""
        try:
            if self.tts_provider == TTSProvider.LOCAL and self.engine:
                # Stop pyttsx3 engine
                if hasattr(self.engine, "stop"):
                    self.engine.stop()

            # Clear any audio streams
            self._audio_streams.clear()

            # Clear engine reference
            self.engine = None

        except Exception as e:
            if self.verbose:
                self.console.print(f"⚠️ Warning during TTS cleanup: {e}")

    def shutdown(self) -> None:
        """Explicitly shutdown the TTS manager and clean up resources."""
        self._cleanup_resources()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()

    @contextmanager
    def speak_context(self, text: str) -> Generator[None]:
        """Context manager for safe speech synthesis with automatic cleanup."""
        try:
            self.speak(text)
            yield
        finally:
            # Force cleanup after speech
            if self.tts_provider in [TTSProvider.OPENAI, TTSProvider.KOKORO]:
                try:
                    import gc

                    gc.collect()  # Force garbage collection to free audio buffers
                except ImportError:
                    pass


if __name__ == "__main__":
    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # Example usage with proper memory management
    # with TTSManger(TTSProvider.OPENAI, voice_name="nova") as tts:
    #     tts.speak("Hello Paul. What can I do for you today?")

    # Or using speak context for automatic cleanup
    # tts = TTSManger(TTSProvider.OPENAI, voice_name="nova")
    # with tts.speak_context("Hello Paul. What can I do for you today?"):
    #     pass  # Speech happens here with automatic cleanup
    # tts.shutdown()
