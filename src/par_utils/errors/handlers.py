"""Helper functions for integrating centralized error messages.

This module provides helper functions to integrate the centralized error registry
with existing code throughout applications.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rich.console import Console

from par_utils.errors.registry import (
    ErrorCategory,
    ErrorMessage,
    ErrorSeverity,
    create_error_with_rich_formatting,
    format_error,
    get_error_registry,
    get_full_error,
)


class ErrorHandler:
    """Helper class for handling errors with consistent formatting."""

    def __init__(self, console: Console | None = None):
        """Initialize error handler.

        Args:
            console: Rich console for output (optional).
        """
        self.console = console
        self.registry = get_error_registry()

    def show_error(self, code: str, exit_code: int | None = None, **kwargs: Any) -> None:
        """Show an error message and optionally exit.

        Args:
            code: Error code to display.
            exit_code: If provided, exit with this code after showing error.
            **kwargs: Variables for error message formatting.
        """
        if self.console:
            error = self.registry.get(code)
            if error:
                error_msg = create_error_with_rich_formatting(error, console_markup=True, **kwargs)
                self.console.print(error_msg)
            else:
                self.console.print(f"[red]Unknown error code: {code}[/red]")
        else:
            print(get_full_error(code, **kwargs))

        if exit_code is not None:
            import sys

            sys.exit(exit_code)

    def show_warning(self, code: str, **kwargs: Any) -> None:
        """Show a warning message.

        Args:
            code: Error code to display as warning.
            **kwargs: Variables for error message formatting.
        """
        error = self.registry.get(code)
        if error and self.console:
            # Force warning color regardless of severity
            formatted_msg = f"[yellow]Warning:[/yellow] {error.format(**kwargs)}"
            if error.solution:
                formatted_msg += f"\n[cyan]Solution:[/cyan] {error.solution}"
            self.console.print(formatted_msg)
        else:
            warning_text = f"Warning: {format_error(code, **kwargs)}"
            if self.console:
                self.console.print(f"[yellow]{warning_text}[/yellow]")
            else:
                print(warning_text)

    def show_info(self, code: str, **kwargs: Any) -> None:
        """Show an info message.

        Args:
            code: Error code to display as info.
            **kwargs: Variables for error message formatting.
        """
        error = self.registry.get(code)
        if error and self.console:
            formatted_msg = f"[blue]Info:[/blue] {error.format(**kwargs)}"
            self.console.print(formatted_msg)
        else:
            info_text = f"Info: {format_error(code, **kwargs)}"
            if self.console:
                self.console.print(f"[blue]{info_text}[/blue]")
            else:
                print(info_text)

    def create_exception(self, code: str, exception_class: type[Exception] = ValueError, **kwargs: Any) -> Exception:
        """Create an exception with standardized error message.

        Args:
            code: Error code for the exception.
            exception_class: Type of exception to create.
            **kwargs: Variables for error message formatting.

        Returns:
            Exception instance with formatted error message.
        """
        message = format_error(code, **kwargs)
        return exception_class(message)


def create_configuration_error(message: str, solution: str | None = None) -> ErrorMessage:
    """Create a configuration error message.

    Args:
        message: Error message text.
        solution: Optional solution guidance.

    Returns:
        ErrorMessage for configuration issues.
    """
    return ErrorMessage(
        code=f"CONFIG_CUSTOM_{hash(message) & 0xFFFFFF:06X}",
        message=message,
        category=ErrorCategory.CONFIGURATION,
        severity=ErrorSeverity.ERROR,
        solution=solution,
    )


def create_security_error(message: str, solution: str | None = None) -> ErrorMessage:
    """Create a security error message.

    Args:
        message: Error message text.
        solution: Optional solution guidance.

    Returns:
        ErrorMessage for security issues.
    """
    return ErrorMessage(
        code=f"SECURITY_CUSTOM_{hash(message) & 0xFFFFFF:06X}",
        message=message,
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.CRITICAL,
        solution=solution,
    )


def create_network_error(message: str, solution: str | None = None) -> ErrorMessage:
    """Create a network error message.

    Args:
        message: Error message text.
        solution: Optional solution guidance.

    Returns:
        ErrorMessage for network issues.
    """
    return ErrorMessage(
        code=f"NETWORK_CUSTOM_{hash(message) & 0xFFFFFF:06X}",
        message=message,
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.ERROR,
        solution=solution,
    )


def create_file_error(message: str, solution: str | None = None) -> ErrorMessage:
    """Create a file operation error message.

    Args:
        message: Error message text.
        solution: Optional solution guidance.

    Returns:
        ErrorMessage for file operation issues.
    """
    return ErrorMessage(
        code=f"FILE_CUSTOM_{hash(message) & 0xFFFFFF:06X}",
        message=message,
        category=ErrorCategory.FILE_OPERATIONS,
        severity=ErrorSeverity.ERROR,
        solution=solution,
    )


def handle_config_validation_error(field: str, validation_error: str, console: Console | None = None) -> None:
    """Handle configuration validation errors.

    Args:
        field: Field that failed validation.
        validation_error: Validation error message.
        console: Console for output (optional).
    """
    handler = ErrorHandler(console)
    handler.show_error("VALIDATION_FAILED", field=field, error=validation_error)


def handle_missing_dependency(dependency: str, console: Console | None = None) -> None:
    """Handle missing system dependency errors.

    Args:
        dependency: Name of the missing dependency.
        console: Console for output (optional).
    """
    handler = ErrorHandler(console)
    handler.show_error("SYSTEM_DEPENDENCY_MISSING", dependency=dependency)


def validate_and_handle_errors(
    validation_func: Callable[..., Any], *args: Any, console: Console | None = None, **kwargs: Any
) -> Any:
    """Validate input and handle errors consistently.

    Args:
        validation_func: Function to call for validation.
        *args: Arguments for validation function.
        console: Console for error output.
        **kwargs: Keyword arguments for validation function.

    Returns:
        Result of validation function.

    Raises:
        Exception: If validation fails.
    """
    try:
        return validation_func(*args, **kwargs)
    except ValueError as e:
        handler = ErrorHandler(console)
        handler.show_error("VALIDATION_FAILED", field="input", error=str(e))
        raise
    except FileNotFoundError as e:
        handler = ErrorHandler(console)
        handler.show_error("FILE_NOT_FOUND", file_path=str(e).split("'")[1] if "'" in str(e) else "unknown")
        raise
    except PermissionError as e:
        handler = ErrorHandler(console)
        handler.show_error("FILE_PERMISSION_DENIED", file_path=str(e).split("'")[1] if "'" in str(e) else "unknown")
        raise


def show_startup_warnings(warnings: list[str], console: Console | None = None) -> None:
    """Show startup warnings in a consistent format.

    Args:
        warnings: List of warning messages.
        console: Console for output (optional).
    """
    if not warnings:
        return

    for warning in warnings:
        if console:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        else:
            print(f"Warning: {warning}")


def create_rich_error_panel(error_code: str, console: Console, **kwargs: Any) -> Any:
    """Create a Rich panel for error display.

    Args:
        error_code: Error code to format.
        console: Rich console.
        **kwargs: Variables for error formatting.

    Returns:
        Rich Panel object.
    """
    from rich.panel import Panel

    error = get_error_registry().get(error_code)
    if not error:
        return Panel(f"Unknown error: {error_code}", title="Error", border_style="red")

    content = create_error_with_rich_formatting(error, console_markup=True, **kwargs)
    title = f"[bold red]{error.severity.value.title()} - {error.category.value.title()}[/bold red]"

    return Panel(content, title=title, border_style="red")


def log_error(error_code: str, logger: Any = None, **kwargs: Any) -> None:
    """Log an error using the centralized registry.

    Args:
        error_code: Error code to log.
        logger: Logger instance (optional).
        **kwargs: Variables for error message formatting.
    """
    error = get_error_registry().get(error_code)
    if error:
        message = error.format(**kwargs)
        severity_map = {
            ErrorSeverity.INFO: "info",
            ErrorSeverity.WARNING: "warning",
            ErrorSeverity.ERROR: "error",
            ErrorSeverity.CRITICAL: "critical",
        }

        if logger:
            log_method = getattr(logger, severity_map.get(error.severity, "error"), logger.error)
            log_method(f"[{error.code}] {message}")
        else:
            print(f"{error.severity.value.upper()}: [{error.code}] {message}")
    else:
        if logger:
            logger.error(f"Unknown error code: {error_code}")
        else:
            print(f"ERROR: Unknown error code: {error_code}")


def suppress_error(error_code: str, **kwargs: Any) -> str:
    """Suppress an error and return the formatted message for logging.

    Args:
        error_code: Error code to suppress.
        **kwargs: Variables for error message formatting.

    Returns:
        Formatted error message for logging purposes.
    """
    return format_error(error_code, **kwargs)
