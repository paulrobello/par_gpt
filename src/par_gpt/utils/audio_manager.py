"""Audio resource management utilities for preventing memory leaks."""

from __future__ import annotations

import gc
import threading
import weakref
from collections.abc import Generator
from contextlib import contextmanager

from par_ai_core.par_logging import console_err
from rich.console import Console

from par_gpt.tts_manager import TTSManger, TTSProvider
from par_gpt.voice_input_manager import VoiceInputManager


class AudioResourceManager:
    """Manages audio resources with automatic cleanup to prevent memory leaks."""

    def __init__(self, console: Console | None = None):
        """
        Initialize audio resource manager.

        Args:
            console: Console for output. Defaults to console_err.
        """
        self.console = console or console_err
        self._active_voice_managers: set[VoiceInputManager] = set()
        self._active_tts_managers: set[TTSManger] = set()
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

        # Start background cleanup thread
        self._start_cleanup_thread()

        # Register global cleanup
        weakref.finalize(self, self._global_cleanup)

    def _start_cleanup_thread(self) -> None:
        """Start background thread for periodic cleanup."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._periodic_cleanup, daemon=True, name="AudioResourceCleanup"
            )
            self._cleanup_thread.start()

    def _periodic_cleanup(self) -> None:
        """Periodic cleanup of audio resources."""
        while not self._stop_cleanup.wait(30):  # Check every 30 seconds
            try:
                # Force garbage collection to free audio buffers
                gc.collect()

                # Clean up inactive managers
                inactive_voice = {vm for vm in self._active_voice_managers if not vm._is_active}
                for vm in inactive_voice:
                    try:
                        vm.shutdown()
                        self._active_voice_managers.discard(vm)
                    except Exception:
                        pass

                # Clean up TTS managers that are no longer referenced
                inactive_tts = {
                    tm for tm in self._active_tts_managers if not hasattr(tm, "engine") or tm.engine is None
                }
                for tm in inactive_tts:
                    try:
                        tm.shutdown()
                        self._active_tts_managers.discard(tm)
                    except Exception:
                        pass

            except Exception as e:
                console_err.print(f"Warning: Error in audio cleanup thread: {e}")

    def _global_cleanup(self) -> None:
        """Global cleanup for all audio resources."""
        self._stop_cleanup.set()

        # Cleanup all active managers
        for vm in list(self._active_voice_managers):
            try:
                vm.shutdown()
            except Exception:
                pass

        for tm in list(self._active_tts_managers):
            try:
                tm.shutdown()
            except Exception:
                pass

        self._active_voice_managers.clear()
        self._active_tts_managers.clear()

        # Force final garbage collection
        gc.collect()

    @contextmanager
    def voice_input_context(
        self,
        wake_word: str = "GPT",
        *,
        model: str = "small.en",
        max_listen_time: float = 300.0,
        verbose: bool = False,
    ) -> Generator[VoiceInputManager, None, None]:
        """
        Context manager for voice input with automatic resource cleanup.

        Args:
            wake_word: Wake word to listen for.
            model: Speech recognition model to use.
            max_listen_time: Maximum listening time in seconds.
            verbose: Enable verbose output.

        Yields:
            VoiceInputManager instance.
        """
        vim = VoiceInputManager(
            wake_word=wake_word,
            model=model,
            max_listen_time=max_listen_time,
            verbose=verbose,
            console=self.console,
        )

        self._active_voice_managers.add(vim)

        try:
            yield vim
        finally:
            try:
                vim.shutdown()
            except Exception as e:
                self.console.print(f"Warning: Error shutting down voice input: {e}")
            finally:
                self._active_voice_managers.discard(vim)
                # Force cleanup
                gc.collect()

    @contextmanager
    def tts_context(
        self,
        provider: TTSProvider,
        *,
        voice_name: str | None = None,
        speed: float = 1.0,
        verbose: bool = False,
    ) -> Generator[TTSManger, None, None]:
        """
        Context manager for TTS with automatic resource cleanup.

        Args:
            provider: TTS provider to use.
            voice_name: Voice name (provider-specific).
            speed: Speech speed.
            verbose: Enable verbose output.

        Yields:
            TTSManger instance.
        """
        tts = TTSManger(
            provider,
            voice_name=voice_name,
            speed=speed,
            verbose=verbose,
            console=self.console,
        )

        self._active_tts_managers.add(tts)

        try:
            yield tts
        finally:
            try:
                tts.shutdown()
            except Exception as e:
                self.console.print(f"Warning: Error shutting down TTS: {e}")
            finally:
                self._active_tts_managers.discard(tts)
                # Force cleanup for audio buffers
                gc.collect()

    @contextmanager
    def safe_audio_session(self) -> Generator[AudioResourceManager, None, None]:
        """
        Context manager for a complete audio session with guaranteed cleanup.

        Yields:
            AudioResourceManager instance.
        """
        try:
            yield self
        finally:
            # Ensure all resources are cleaned up
            self._global_cleanup()

    def get_active_managers_count(self) -> tuple[int, int]:
        """
        Get count of active audio managers.

        Returns:
            Tuple of (voice_managers_count, tts_managers_count).
        """
        return len(self._active_voice_managers), len(self._active_tts_managers)

    def force_cleanup(self) -> None:
        """Force immediate cleanup of all audio resources."""
        self._global_cleanup()


# Global audio resource manager instance
_audio_manager: AudioResourceManager | None = None


def get_audio_manager() -> AudioResourceManager:
    """Get the global audio resource manager instance."""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioResourceManager()
    return _audio_manager


def reset_audio_manager() -> None:
    """Reset the global audio resource manager instance."""
    global _audio_manager
    if _audio_manager:
        _audio_manager._global_cleanup()
    _audio_manager = None


# Convenience functions
@contextmanager
def safe_voice_input(
    wake_word: str = "GPT",
    *,
    model: str = "small.en",
    max_listen_time: float = 300.0,
    verbose: bool = False,
) -> Generator[VoiceInputManager, None, None]:
    """
    Convenience function for safe voice input with automatic cleanup.

    Args:
        wake_word: Wake word to listen for.
        model: Speech recognition model to use.
        max_listen_time: Maximum listening time in seconds.
        verbose: Enable verbose output.

    Yields:
        VoiceInputManager instance.
    """
    manager = get_audio_manager()
    with manager.voice_input_context(
        wake_word=wake_word,
        model=model,
        max_listen_time=max_listen_time,
        verbose=verbose,
    ) as vim:
        yield vim


@contextmanager
def safe_tts(
    provider: TTSProvider,
    *,
    voice_name: str | None = None,
    speed: float = 1.0,
    verbose: bool = False,
) -> Generator[TTSManger, None, None]:
    """
    Convenience function for safe TTS with automatic cleanup.

    Args:
        provider: TTS provider to use.
        voice_name: Voice name (provider-specific).
        speed: Speech speed.
        verbose: Enable verbose output.

    Yields:
        TTSManger instance.
    """
    manager = get_audio_manager()
    with manager.tts_context(
        provider=provider,
        voice_name=voice_name,
        speed=speed,
        verbose=verbose,
    ) as tts:
        yield tts
