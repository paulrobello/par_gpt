"""Thread-safe context manager for tool execution state.

This module provides a thread-safe alternative to global variables for managing
tool execution context across the application.
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


class ThreadSafeContextManager:
    """Thread-safe context manager for managing tool execution state."""

    def __init__(self) -> None:
        """Initialize the context manager."""
        self._contexts: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _get_thread_id(self) -> int:
        """Get the current thread ID."""
        return threading.get_ident()

    def set_context(self, **kwargs: Any) -> None:
        """Set context values for the current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            if thread_id not in self._contexts:
                self._contexts[thread_id] = {}
            self._contexts[thread_id].update(kwargs)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value for the current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            return self._contexts.get(thread_id, {}).get(key, default)

    def clear_context(self) -> None:
        """Clear context for the current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            self._contexts.pop(thread_id, None)

    def clear_all_contexts(self) -> None:
        """Clear all contexts (useful for testing or cleanup)."""
        with self._lock:
            self._contexts.clear()

    @contextmanager
    def context_scope(self, **kwargs: Any) -> Generator[None]:
        """Context manager for setting temporary context values."""
        thread_id = self._get_thread_id()

        # Store original values
        original_context = {}
        with self._lock:
            current_context = self._contexts.get(thread_id, {})
            for key in kwargs:
                if key in current_context:
                    original_context[key] = current_context[key]

        # Set new values
        self.set_context(**kwargs)

        try:
            yield
        finally:
            # Restore original values
            thread_id = self._get_thread_id()
            with self._lock:
                if thread_id in self._contexts:
                    # Remove new keys that weren't there before
                    for key in kwargs:
                        if key not in original_context:
                            self._contexts[thread_id].pop(key, None)
                        else:
                            self._contexts[thread_id][key] = original_context[key]

                    # Clean up empty contexts
                    if not self._contexts[thread_id]:
                        self._contexts.pop(thread_id, None)

    def is_yes_to_all_enabled(self) -> bool:
        """Check if yes-to-all mode is enabled for automatic confirmations."""
        return self.get_context("yes_to_all", False)

    def get_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_context("debug", False)

    def get_user_id(self) -> str | None:
        """Get the current user ID."""
        return self.get_context("user_id")

    def get_all_context(self) -> dict[str, Any]:
        """Get all context values for the current thread (useful for debugging)."""
        thread_id = self._get_thread_id()
        with self._lock:
            return self._contexts.get(thread_id, {}).copy()


# Global instance for backward compatibility and easy access
_context_manager = ThreadSafeContextManager()


def set_tool_context(**kwargs: Any) -> None:
    """Set global context for AI tools (backward compatibility)."""
    _context_manager.set_context(**kwargs)


def get_tool_context(key: str, default: Any = None) -> Any:
    """Get a value from the global tool context (backward compatibility)."""
    return _context_manager.get_context(key, default)


def clear_tool_context() -> None:
    """Clear the global tool context (backward compatibility)."""
    _context_manager.clear_context()


def is_yes_to_all_enabled() -> bool:
    """Check if yes-to-all mode is enabled for automatic confirmations (backward compatibility)."""
    return _context_manager.is_yes_to_all_enabled()


def get_context_manager() -> ThreadSafeContextManager:
    """Get the global context manager instance."""
    return _context_manager
