"""Centralized error message registry for consistent user experience.

This module provides a centralized registry for all error messages used throughout
applications, ensuring consistent formatting, tone, and helpful guidance for users.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Categories of errors for better organization."""

    CONFIGURATION = "configuration"
    SECURITY = "security"
    NETWORK = "network"
    FILE_OPERATIONS = "file_operations"
    AI_PROVIDER = "ai_provider"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    TOOLS = "tools"
    PERFORMANCE = "performance"
    CACHE = "cache"


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorMessage:
    """Structured error message with metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        solution: str | None = None,
        documentation_url: str | None = None,
    ):
        """Initialize error message.

        Args:
            code: Unique error code (e.g., "CONFIG_INVALID_PROVIDER").
            message: Human-readable error message.
            category: Error category for organization.
            severity: Severity level of the error.
            solution: Optional solution guidance.
            documentation_url: Optional link to relevant documentation.
        """
        self.code = code
        self.message = message
        self.category = category
        self.severity = severity
        self.solution = solution
        self.documentation_url = documentation_url

    def format(self, **kwargs: Any) -> str:
        """Format the error message with context variables."""
        try:
            return self.message.format(**kwargs)
        except KeyError as e:
            return f"{self.message} (formatting error: missing variable {e})"

    def get_full_message(self, **kwargs: Any) -> str:
        """Get the full error message including solution if available."""
        message = self.format(**kwargs)
        parts = [message]

        if self.solution:
            parts.append(f"Solution: {self.solution}")

        if self.documentation_url:
            parts.append(f"Documentation: {self.documentation_url}")

        return "\n".join(parts)

    def __str__(self) -> str:
        """String representation of the error message."""
        return f"[{self.code}] {self.message}"


class ErrorRegistry:
    """Registry for centralized error message management."""

    def __init__(self) -> None:
        """Initialize the error registry."""
        self._errors: dict[str, ErrorMessage] = {}
        self._register_default_errors()

    def register(self, error: ErrorMessage) -> None:
        """Register a new error message.

        Args:
            error: Error message to register.

        Raises:
            ValueError: If error code already exists.
        """
        if error.code in self._errors:
            raise ValueError(f"Error code '{error.code}' already registered")
        self._errors[error.code] = error

    def get(self, code: str) -> ErrorMessage | None:
        """Get an error message by code.

        Args:
            code: Error code to look up.

        Returns:
            Error message if found, None otherwise.
        """
        return self._errors.get(code)

    def format_error(self, code: str, **kwargs: Any) -> str:
        """Format an error message with context variables.

        Args:
            code: Error code to format.
            **kwargs: Variables for message formatting.

        Returns:
            Formatted error message or generic message if code not found.
        """
        error = self.get(code)
        if error:
            return error.format(**kwargs)
        return f"Unknown error code: {code}"

    def get_full_error(self, code: str, **kwargs: Any) -> str:
        """Get full error message including solution guidance.

        Args:
            code: Error code to format.
            **kwargs: Variables for message formatting.

        Returns:
            Full formatted error message.
        """
        error = self.get(code)
        if error:
            return error.get_full_message(**kwargs)
        return f"Unknown error code: {code}"

    def get_errors_by_category(self, category: ErrorCategory) -> list[ErrorMessage]:
        """Get all errors in a specific category.

        Args:
            category: Category to filter by.

        Returns:
            List of error messages in the category.
        """
        return [error for error in self._errors.values() if error.category == category]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> list[ErrorMessage]:
        """Get all errors with a specific severity.

        Args:
            severity: Severity level to filter by.

        Returns:
            List of error messages with the specified severity.
        """
        return [error for error in self._errors.values() if error.severity == severity]

    def _register_default_errors(self) -> None:
        """Register default error messages for common scenarios."""
        # Configuration errors
        self.register(
            ErrorMessage(
                "CONFIG_INVALID_VALUE",
                "Invalid configuration value for '{key}': {value}",
                ErrorCategory.CONFIGURATION,
                ErrorSeverity.ERROR,
                "Check the configuration documentation for valid values",
            )
        )

        # Security errors
        self.register(
            ErrorMessage(
                "SECURITY_PATH_TRAVERSAL",
                "Path traversal detected in '{path}'. This operation is not allowed for security reasons",
                ErrorCategory.SECURITY,
                ErrorSeverity.CRITICAL,
                "Use a path that doesn't contain directory traversal patterns (../ or ..\\)",
            )
        )

        self.register(
            ErrorMessage(
                "SECURITY_DANGEROUS_FILENAME",
                "Filename '{filename}' contains dangerous characters or is a reserved name",
                ErrorCategory.SECURITY,
                ErrorSeverity.ERROR,
                "Use a filename with only safe characters (letters, numbers, hyphens, underscores)",
            )
        )

        # File operation errors
        self.register(
            ErrorMessage(
                "FILE_NOT_FOUND",
                "File not found: {file_path}",
                ErrorCategory.FILE_OPERATIONS,
                ErrorSeverity.ERROR,
                "Check that the file path is correct and the file exists",
            )
        )

        self.register(
            ErrorMessage(
                "FILE_PERMISSION_DENIED",
                "Permission denied accessing file: {file_path}",
                ErrorCategory.FILE_OPERATIONS,
                ErrorSeverity.ERROR,
                "Check file permissions or run with appropriate privileges",
            )
        )

        # Performance errors
        self.register(
            ErrorMessage(
                "PERFORMANCE_TIMEOUT",
                "Operation timed out after {timeout}s",
                ErrorCategory.PERFORMANCE,
                ErrorSeverity.WARNING,
                "Try again or increase the timeout value",
            )
        )

        # Cache errors
        self.register(
            ErrorMessage(
                "CACHE_WRITE_FAILED",
                "Failed to write to cache: {error}",
                ErrorCategory.CACHE,
                ErrorSeverity.WARNING,
                "Check cache directory permissions and available disk space",
            )
        )

        # System errors
        self.register(
            ErrorMessage(
                "SYSTEM_DEPENDENCY_MISSING",
                "Required dependency missing: {dependency}",
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                "Install the required dependency using your package manager",
            )
        )

        # Network errors
        self.register(
            ErrorMessage(
                "NETWORK_CONNECTION_FAILED",
                "Failed to connect to {service}: {error}",
                ErrorCategory.NETWORK,
                ErrorSeverity.ERROR,
                "Check your internet connection and verify the service URL",
            )
        )

        # Validation errors
        self.register(
            ErrorMessage(
                "VALIDATION_FAILED",
                "Validation failed for {field}: {error}",
                ErrorCategory.VALIDATION,
                ErrorSeverity.ERROR,
                "Provide valid input according to the field requirements",
            )
        )


# Global error registry instance
_error_registry = ErrorRegistry()


def get_error_registry() -> ErrorRegistry:
    """Get the global error registry instance."""
    return _error_registry


def register_error(error: ErrorMessage) -> None:
    """Register a new error message in the global registry."""
    _error_registry.register(error)


def format_error(code: str, **kwargs: Any) -> str:
    """Format an error message from the global registry."""
    return _error_registry.format_error(code, **kwargs)


def get_full_error(code: str, **kwargs: Any) -> str:
    """Get full error message including solution from the global registry."""
    return _error_registry.get_full_error(code, **kwargs)


def create_error_with_rich_formatting(error_message: ErrorMessage, console_markup: bool = True, **kwargs: Any) -> str:
    """Create a Rich-formatted error message.

    Args:
        error_message: Error message to format.
        console_markup: Whether to include Rich console markup.
        **kwargs: Variables for message formatting.

    Returns:
        Formatted error message with Rich markup.
    """
    if not console_markup:
        return error_message.get_full_message(**kwargs)

    # Map severity to Rich colors
    severity_colors = {
        ErrorSeverity.INFO: "blue",
        ErrorSeverity.WARNING: "yellow",
        ErrorSeverity.ERROR: "red",
        ErrorSeverity.CRITICAL: "bold red",
    }

    color = severity_colors.get(error_message.severity, "red")
    formatted_message = error_message.format(**kwargs)

    parts = [f"[{color}]{formatted_message}[/{color}]"]

    if error_message.solution:
        parts.append(f"[cyan]Solution:[/cyan] {error_message.solution}")

    if error_message.documentation_url:
        parts.append(f"[blue]Documentation:[/blue] {error_message.documentation_url}")

    return "\n".join(parts)
