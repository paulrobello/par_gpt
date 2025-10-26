import logging
import re
import threading
import time
import weakref
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.utils import timer_block

# RealtimeSTT import moved to lazy loading in __init__ method
from rich.console import Console

from par_gpt.utils.llm_invoker import LLMInvoker
from par_utils import ConsoleManager, LazyImportManager

# Create instances for backward compatibility
_lazy_import_manager = LazyImportManager()
_console_manager = ConsoleManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


def get_console(console=None):
    """Backward compatibility function for get_console."""
    return _console_manager.get_console(console)


def is_complete_sentence(text: str, llm_config: LlmConfig | None = None) -> bool:
    config = llm_config or LlmConfig(LlmProvider.OLLAMA, model_name="llama3.2:latest", temperature=0)
    invoker = LLMInvoker(config)

    system_prompt = (
        "Please reply with only 'c' if the following text is a complete thought (a sentence that stands on its own), "
        "or 'i' if it is not finished. Do not include any additional text in your reply. "
        "Consider a full sentence to have a clear subject, verb, and predicate or express a complete idea. "
        "Examples:\n"
        "- 'The sky is blue.' is complete (reply 'c').\n"
        "- 'When the sky' is incomplete (reply 'i').\n"
        "- 'She walked home.' is complete (reply 'c').\n"
        "- 'Because he' is incomplete (reply 'i').\n"
    )

    reply = invoker.get_text_response([("system", system_prompt), ("user", text)])
    return reply.strip().lower() == "c"


class VoiceInputManager:
    """Voice input manager with proper memory management and resource cleanup."""

    def __init__(
        self,
        wake_word: str = "GPT",
        *,
        model: str = "small.en",
        post_speech_silence_duration: float = 1.5,
        batch_size: int = 25,
        sanity_check_sentence: bool = True,
        verbose: bool = False,
        console: Console | None = None,
        max_listen_time: float = 300.0,  # 5 minutes max listening time
    ):
        self.console = get_console(console)
        self.verbose = verbose
        self.model = model
        self.post_speech_silence_duration = post_speech_silence_duration
        # Type annotation updated to use Any since AudioToTextRecorder is lazy loaded
        self.recorder: Any | None = None
        self.batch_size = batch_size
        self.wake_word = wake_word
        self.sanity_check_sentence = sanity_check_sentence
        self.last_transcript = ""
        self.max_listen_time = max_listen_time
        self._shutdown_event = threading.Event()
        self._listen_start_time: float = 0
        self._is_active = False

        # Register cleanup on deletion
        weakref.finalize(self, self._cleanup_resources)

    def init_recorder(self) -> None:
        """Initialize audio recorder with proper error handling."""
        if self.recorder is not None:
            self.console.print("🎤 Recorder already initialized")
            return

        self.console.print("🎤 Initializing audio recording system...")
        try:
            with timer_block("🎤 Recording system initialization complete", console=self.console):
                # Lazy load AudioToTextRecorder
                AudioToTextRecorder = lazy_import("RealtimeSTT", "AudioToTextRecorder")
                self.recorder = AudioToTextRecorder(
                    spinner=False,
                    post_speech_silence_duration=self.post_speech_silence_duration,
                    compute_type="float32",
                    model=self.model,
                    beam_size=8,
                    batch_size=self.batch_size,
                    language="en",
                    print_transcription_time=self.verbose,
                    level=logging.ERROR,
                )
                self._is_active = True
        except Exception as e:
            self.console.print(f"❌ Failed to initialize recorder: {e}")
            self.recorder = None
            raise

    def process_text(self, text: str) -> str:
        if not text:
            return ""
        try:
            if self.verbose:
                self.console.print(f"\n🎤 Heard: {text}")

            matches = re.findall(rf"(?i)\b({self.wake_word})\b(.*)", text)
            if not matches:
                if self.verbose:
                    self.console.print(f"🤖 Not {self.wake_word} - ignoring")
                return ""
            if self.recorder:
                self.recorder.stop()

            text = matches[0][1].strip(" \t,.?!\"'")
            if self.sanity_check_sentence:
                if not is_complete_sentence(text):
                    if self.verbose:
                        self.console.print("❌ Not a complete sentence - ignoring")
                    return ""
            if self.verbose:
                self.console.print(f"🎤 USING: {text}")
            return text
        except Exception as e:
            self.console.print(f"❌ Voice Input Error: {str(e)}")
            return ""

    def get_text(self) -> str:
        """Get text input with timeout and proper resource management."""
        self.last_transcript = ""

        if not self.recorder:
            self.init_recorder()

        if not self.recorder:
            return ""

        try:
            if not self.recorder._is_recording:  # type: ignore
                self.recorder.start()

            self._listen_start_time = time.time()
            self._shutdown_event.clear()

            self.console.print(
                f"🎤 Listening for name '{self.wake_word}'. Say '{self.wake_word} exit' to stop listening."
            )

            while self.recorder is not None and not self._shutdown_event.is_set() and self._is_active:
                # Check for timeout
                if time.time() - self._listen_start_time > self.max_listen_time:
                    self.console.print("⏰ Listening timeout reached")
                    break

                # Process audio input with small delay to prevent CPU spinning
                try:
                    text = self.recorder.text() or ""
                    self.last_transcript = self.process_text(text)

                    if self.last_transcript:
                        return self.last_transcript.strip()

                    # Small sleep to prevent CPU spinning
                    time.sleep(0.1)

                except Exception as e:
                    self.console.print(f"❌ Error during audio processing: {e}")
                    break

        except Exception as e:
            self.console.print(f"❌ Error in get_text: {e}")
        finally:
            # Ensure recorder is stopped
            if self.recorder and hasattr(self.recorder, "stop"):
                try:
                    self.recorder.stop()
                except Exception:
                    pass  # Ignore errors during cleanup

        return ""

    def shutdown(self) -> None:
        """Properly shutdown the voice input manager and clean up resources."""
        self._shutdown_event.set()
        self._is_active = False
        self._cleanup_resources()

    def _cleanup_resources(self) -> None:
        """Clean up audio resources to prevent memory leaks."""
        if self.recorder:
            try:
                # Stop recording first
                if hasattr(self.recorder, "stop"):
                    self.recorder.stop()

                # Then shutdown
                if hasattr(self.recorder, "shutdown"):
                    self.recorder.shutdown()

            except Exception as e:
                if self.verbose:
                    self.console.print(f"⚠️  Warning during cleanup: {e}")
            finally:
                self.recorder = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()

    @contextmanager
    def listen_context(self) -> Generator["VoiceInputManager"]:
        """Context manager for safe listening with automatic cleanup."""
        try:
            yield self
        finally:
            self.shutdown()


if __name__ == "__main__":
    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # Example usage with proper memory management
    # with VoiceInputManager(verbose=True) as vim:
    #     while True:
    #         text = vim.get_text()
    #         console_err.print(text)
    #         if text.lower() == "exit":
    #             break
