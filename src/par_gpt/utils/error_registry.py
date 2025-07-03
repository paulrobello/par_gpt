"""Centralized error message registry for consistent user experience.

This module provides a centralized registry for all error messages used throughout
PAR GPT, ensuring consistent formatting, tone, and helpful guidance for users.
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
        """Register default error messages used throughout PAR GPT."""
        # Configuration errors
        self.register(
            ErrorMessage(
                "CONFIG_INVALID_PROVIDER",
                "Invalid AI provider '{provider}'. Supported providers: {supported_providers}",
                ErrorCategory.CONFIGURATION,
                ErrorSeverity.ERROR,
                "Use one of the supported providers or check your configuration",
                "https://github.com/paulrobello/par_gpt#ai-providers",
            )
        )

        self.register(
            ErrorMessage(
                "CONFIG_INVALID_TEMPERATURE",
                "Temperature must be between 0.0 and 2.0, got {temperature}",
                ErrorCategory.CONFIGURATION,
                ErrorSeverity.ERROR,
                "Set temperature to a value between 0.0 and 2.0",
            )
        )

        self.register(
            ErrorMessage(
                "CONFIG_MISSING_API_KEY",
                "API key not found for provider '{provider}'. Environment variable '{key_name}' is not set",
                ErrorCategory.AUTHENTICATION,
                ErrorSeverity.CRITICAL,
                "Set the required API key in your environment or ~/.par_gpt.env file",
                "https://github.com/paulrobello/par_gpt#environment-variables",
            )
        )

        self.register(
            ErrorMessage(
                "CONFIG_INVALID_BASE_URL",
                "Invalid base URL '{base_url}'. URL must start with http:// or https://",
                ErrorCategory.CONFIGURATION,
                ErrorSeverity.ERROR,
                "Provide a valid HTTP or HTTPS URL",
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

        self.register(
            ErrorMessage(
                "SECURITY_FILE_TOO_LARGE",
                "File size {size_mb:.1f}MB exceeds maximum allowed size of {max_size_mb:.1f}MB",
                ErrorCategory.SECURITY,
                ErrorSeverity.ERROR,
                "Use a smaller file or increase the maximum file size limit",
            )
        )

        self.register(
            ErrorMessage(
                "SECURITY_CODE_EXECUTION_DENIED",
                "Code execution was denied by user or security policy",
                ErrorCategory.SECURITY,
                ErrorSeverity.WARNING,
                "Enable code execution if needed using --repl flag or configure security settings",
            )
        )

        # Network errors
        self.register(
            ErrorMessage(
                "NETWORK_CONNECTION_FAILED",
                "Failed to connect to {service} at {url}: {error}",
                ErrorCategory.NETWORK,
                ErrorSeverity.ERROR,
                "Check your internet connection and verify the service URL",
            )
        )

        self.register(
            ErrorMessage(
                "NETWORK_TIMEOUT",
                "Request to {service} timed out after {timeout}s",
                ErrorCategory.NETWORK,
                ErrorSeverity.ERROR,
                "Try again or increase the timeout value",
            )
        )

        self.register(
            ErrorMessage(
                "NETWORK_API_RATE_LIMIT",
                "API rate limit exceeded for {provider}. Rate limit: {limit}, reset time: {reset_time}",
                ErrorCategory.NETWORK,
                ErrorSeverity.WARNING,
                "Wait for the rate limit to reset or use a different provider",
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

        self.register(
            ErrorMessage(
                "FILE_INVALID_FORMAT",
                "Invalid file format for {file_path}. Expected {expected_format}, got {actual_format}",
                ErrorCategory.FILE_OPERATIONS,
                ErrorSeverity.ERROR,
                "Use a file with the correct format",
            )
        )

        # AI Provider errors
        self.register(
            ErrorMessage(
                "AI_MODEL_NOT_FOUND",
                "Model '{model}' not found for provider '{provider}'",
                ErrorCategory.AI_PROVIDER,
                ErrorSeverity.ERROR,
                "Use a valid model name or check available models for the provider",
            )
        )

        self.register(
            ErrorMessage(
                "AI_PROVIDER_ERROR",
                "Error from {provider}: {error_message}",
                ErrorCategory.AI_PROVIDER,
                ErrorSeverity.ERROR,
                "Check the error message and verify your API configuration",
            )
        )

        self.register(
            ErrorMessage(
                "AI_CONTEXT_TOO_LARGE",
                "Context size {context_size} exceeds maximum {max_size} for model '{model}'",
                ErrorCategory.AI_PROVIDER,
                ErrorSeverity.ERROR,
                "Reduce context size or use a model with larger context limit",
            )
        )

        # Tool errors
        self.register(
            ErrorMessage(
                "TOOL_NOT_AVAILABLE",
                "Tool '{tool_name}' is not available: {reason}",
                ErrorCategory.TOOLS,
                ErrorSeverity.WARNING,
                "Install required dependencies or enable the tool in configuration",
            )
        )

        self.register(
            ErrorMessage(
                "TOOL_EXECUTION_FAILED",
                "Failed to execute tool '{tool_name}': {error}",
                ErrorCategory.TOOLS,
                ErrorSeverity.ERROR,
                "Check the tool configuration and error details",
            )
        )

        # User input errors
        self.register(
            ErrorMessage(
                "INPUT_VALIDATION_FAILED",
                "Invalid input for {field}: {validation_error}",
                ErrorCategory.USER_INPUT,
                ErrorSeverity.ERROR,
                "Provide valid input according to the field requirements",
            )
        )

        self.register(
            ErrorMessage(
                "INPUT_REQUIRED",
                "Required input missing: {field}",
                ErrorCategory.USER_INPUT,
                ErrorSeverity.ERROR,
                "Provide the required input",
            )
        )

        # System errors
        self.register(
            ErrorMessage(
                "SYSTEM_DEPENDENCY_MISSING",
                "Required system dependency missing: {dependency}",
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                "Install the required dependency using your system package manager",
            )
        )

        self.register(
            ErrorMessage(
                "SYSTEM_PLATFORM_UNSUPPORTED",
                "Operation not supported on platform '{platform}'",
                ErrorCategory.SYSTEM,
                ErrorSeverity.ERROR,
                "Use a supported platform or find an alternative approach",
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
