"""Console management utilities for consistent console handling across applications."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from rich.console import Console

F = TypeVar("F", bound=Callable[..., Any])


class ConsoleManager:
    """Manages console instances and provides consistent console handling."""

    def __init__(self, default_console: Console | None = None):
        """Initialize console manager.

        Args:
            default_console: Default console to use when none provided
        """
        self._default_console = default_console or Console(stderr=True)

    @property
    def default_console(self) -> Console:
        """Get the default console instance."""
        return self._default_console

    @default_console.setter
    def default_console(self, console: Console) -> None:
        """Set the default console instance."""
        self._default_console = console

    def get_console(self, console: Console | None = None) -> Console:
        """Get a console instance, defaulting to the configured default if not provided.

        Args:
            console: Optional console instance. If None, uses default console.

        Returns:
            Console instance to use.
        """
        return console or self._default_console

    def with_console(self, func: F) -> F:
        """Decorator that ensures a console is available for the function.

        If the decorated function has a 'console' parameter and it's None,
        it will be replaced with the default console.

        Args:
            func: Function to decorate.

        Returns:
            Decorated function.
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if console is in kwargs
            if "console" in kwargs and kwargs["console"] is None:
                kwargs["console"] = self._default_console
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    def create_console(self, stderr: bool = True, **kwargs: Any) -> Console:
        """Create a new console instance with specified options.

        Args:
            stderr: Whether to use stderr for output
            **kwargs: Additional arguments for Console constructor

        Returns:
            New Console instance
        """
        return Console(stderr=stderr, **kwargs)

    def print_with_default(self, *args: Any, **kwargs: Any) -> None:
        """Print using the default console.

        Args:
            *args: Arguments to pass to console.print
            **kwargs: Keyword arguments to pass to console.print
        """
        self._default_console.print(*args, **kwargs)

    def log_with_default(self, *args: Any, **kwargs: Any) -> None:
        """Log using the default console.

        Args:
            *args: Arguments to pass to console.log
            **kwargs: Keyword arguments to pass to console.log
        """
        self._default_console.log(*args, **kwargs)


# Global console manager instance
_console_manager = ConsoleManager()


def get_default_console_manager() -> ConsoleManager:
    """Get the global console manager instance."""
    return _console_manager


def set_default_console(console: Console) -> None:
    """Set the global default console."""
    _console_manager.default_console = console


def get_console(console: Console | None = None) -> Console:
    """Get a console instance, defaulting to the global default if not provided.

    Args:
        console: Optional console instance. If None, uses global default.

    Returns:
        Console instance to use.
    """
    return _console_manager.get_console(console)


def with_console[F](func: F) -> F:
    """Decorator that ensures a console is available for the function.

    If the decorated function has a 'console' parameter and it's None,
    it will be replaced with the global default console.

    Args:
        func: Function to decorate.

    Returns:
        Decorated function.
    """
    return _console_manager.with_console(func)


def create_console(stderr: bool = True, **kwargs: Any) -> Console:
    """Create a new console instance with specified options.

    Args:
        stderr: Whether to use stderr for output
        **kwargs: Additional arguments for Console constructor

    Returns:
        New Console instance
    """
    return _console_manager.create_console(stderr=stderr, **kwargs)


def print_default(*args: Any, **kwargs: Any) -> None:
    """Print using the global default console.

    Args:
        *args: Arguments to pass to console.print
        **kwargs: Keyword arguments to pass to console.print
    """
    _console_manager.print_with_default(*args, **kwargs)


def log_default(*args: Any, **kwargs: Any) -> None:
    """Log using the global default console.

    Args:
        *args: Arguments to pass to console.log
        **kwargs: Keyword arguments to pass to console.log
    """
    _console_manager.log_with_default(*args, **kwargs)
