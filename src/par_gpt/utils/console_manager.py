"""Console management utilities for consistent console handling across the application."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from par_ai_core.par_logging import console_err
from rich.console import Console

F = TypeVar("F", bound=Callable[..., Any])


class ConsoleManager:
    """Manages console instances and provides consistent console handling."""

    @staticmethod
    def get_console(console: Console | None = None) -> Console:
        """
        Get a console instance, defaulting to console_err if not provided.

        Args:
            console: Optional console instance. If None, uses console_err.

        Returns:
            Console instance to use.
        """
        return console or console_err

    @staticmethod
    def with_console(func: F) -> F:
        """
        Decorator that ensures a console is available for the function.

        If the decorated function has a 'console' parameter and it's None,
        it will be replaced with console_err.

        Args:
            func: Function to decorate.

        Returns:
            Decorated function.
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if console is in kwargs
            if "console" in kwargs and kwargs["console"] is None:
                kwargs["console"] = console_err
            return func(*args, **kwargs)

        return wrapper  # type: ignore


# Convenience function for backward compatibility
def get_console(console: Console | None = None) -> Console:
    """
    Get a console instance, defaulting to console_err if not provided.

    Args:
        console: Optional console instance. If None, uses console_err.

    Returns:
        Console instance to use.
    """
    return ConsoleManager.get_console(console)
