"""Global context for AI tools to access runtime state."""

from __future__ import annotations

# Global state for tool execution context
_tool_context: dict[str, any] = {}


def set_tool_context(**kwargs) -> None:
    """Set global context for AI tools."""
    global _tool_context
    _tool_context.update(kwargs)


def get_tool_context(key: str, default=None):
    """Get a value from the global tool context."""
    return _tool_context.get(key, default)


def clear_tool_context() -> None:
    """Clear the global tool context."""
    global _tool_context
    _tool_context.clear()


def is_yes_to_all_enabled() -> bool:
    """Check if yes-to-all mode is enabled for automatic confirmations."""
    return get_tool_context("yes_to_all", False)
