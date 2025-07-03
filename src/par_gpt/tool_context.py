"""Global context for AI tools to access runtime state.

This module now uses a thread-safe context manager for better state management.
The API remains backward compatible but now supports thread safety.
"""

from __future__ import annotations

from typing import Any

# Import the new thread-safe context manager
from par_gpt.utils.context_manager import (
    clear_tool_context as _clear_tool_context,
    get_tool_context as _get_tool_context,
    is_yes_to_all_enabled as _is_yes_to_all_enabled,
    set_tool_context as _set_tool_context,
)


def set_tool_context(**kwargs: Any) -> None:
    """Set global context for AI tools (thread-safe)."""
    _set_tool_context(**kwargs)


def get_tool_context(key: str, default: Any = None) -> Any:
    """Get a value from the global tool context (thread-safe)."""
    return _get_tool_context(key, default)


def clear_tool_context() -> None:
    """Clear the global tool context (thread-safe)."""
    _clear_tool_context()


def is_yes_to_all_enabled() -> bool:
    """Check if yes-to-all mode is enabled for automatic confirmations (thread-safe)."""
    return _is_yes_to_all_enabled()
