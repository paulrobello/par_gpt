"""Tests for the centralized error registry."""

from par_gpt.utils.error_registry import (
    ErrorCategory,
    ErrorMessage,
    ErrorRegistry,
    ErrorSeverity,
    create_error_with_rich_formatting,
    format_error,
    get_error_registry,
    get_full_error,
)


class TestErrorMessage:
    """Test cases for ErrorMessage class."""

    def test_error_message_creation(self):
        """Test creating an error message."""
        error = ErrorMessage(
            code="TEST_ERROR",
            message="This is a test error with {variable}",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR,
            solution="Fix the configuration",
            documentation_url="https://example.com/docs",
        )

        assert error.code == "TEST_ERROR"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.ERROR
        assert error.solution == "Fix the configuration"
        assert error.documentation_url == "https://example.com/docs"

    def test_error_message_formatting(self):
        """Test formatting error messages with variables."""
        error = ErrorMessage(
            code="TEST_FORMAT",
            message="Error with {variable} and {number}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
        )

        formatted = error.format(variable="test_value", number=42)
        assert formatted == "Error with test_value and 42"

    def test_error_message_missing_variable(self):
        """Test error message formatting with missing variables."""
        error = ErrorMessage(
            code="TEST_MISSING",
            message="Error with {missing_var}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
        )

        formatted = error.format()
        assert "formatting error: missing variable" in formatted

    def test_full_message(self):
        """Test getting full error message with solution."""
        error = ErrorMessage(
            code="TEST_FULL",
            message="Test error",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.ERROR,
            solution="Test solution",
            documentation_url="https://example.com",
        )

        full_message = error.get_full_message()
        assert "Test error" in full_message
        assert "Solution: Test solution" in full_message
        assert "Documentation: https://example.com" in full_message


class TestErrorRegistry:
    """Test cases for ErrorRegistry class."""

    def test_registry_creation(self):
        """Test creating a new error registry."""
        registry = ErrorRegistry()
        assert len(registry._errors) > 0  # Should have default errors

    def test_register_error(self):
        """Test registering a new error."""
        registry = ErrorRegistry()
        error = ErrorMessage(
            code="CUSTOM_ERROR",
            message="Custom error message",
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.INFO,
        )

        registry.register(error)
        retrieved = registry.get("CUSTOM_ERROR")
        assert retrieved is not None
        assert retrieved.code == "CUSTOM_ERROR"
        assert retrieved.message == "Custom error message"

    def test_register_duplicate_error(self):
        """Test registering duplicate error codes."""
        registry = ErrorRegistry()
        error1 = ErrorMessage(
            code="DUPLICATE",
            message="First message",
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.INFO,
        )
        error2 = ErrorMessage(
            code="DUPLICATE",
            message="Second message",
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.INFO,
        )

        registry.register(error1)
        try:
            registry.register(error2)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already registered" in str(e)

    def test_get_nonexistent_error(self):
        """Test getting non-existent error."""
        registry = ErrorRegistry()
        result = registry.get("NONEXISTENT")
        assert result is None

    def test_format_error(self):
        """Test formatting error with registry."""
        registry = ErrorRegistry()
        formatted = registry.format_error(
            "CONFIG_INVALID_PROVIDER", provider="InvalidProvider", supported_providers="OpenAI, Anthropic"
        )
        assert "InvalidProvider" in formatted
        assert "OpenAI, Anthropic" in formatted

    def test_format_nonexistent_error(self):
        """Test formatting non-existent error."""
        registry = ErrorRegistry()
        formatted = registry.format_error("NONEXISTENT")
        assert "Unknown error code: NONEXISTENT" == formatted

    def test_get_errors_by_category(self):
        """Test filtering errors by category."""
        registry = ErrorRegistry()
        config_errors = registry.get_errors_by_category(ErrorCategory.CONFIGURATION)
        assert len(config_errors) > 0
        for error in config_errors:
            assert error.category == ErrorCategory.CONFIGURATION

    def test_get_errors_by_severity(self):
        """Test filtering errors by severity."""
        registry = ErrorRegistry()
        critical_errors = registry.get_errors_by_severity(ErrorSeverity.CRITICAL)
        assert len(critical_errors) > 0
        for error in critical_errors:
            assert error.severity == ErrorSeverity.CRITICAL


class TestGlobalFunctions:
    """Test cases for global registry functions."""

    def test_global_registry_access(self):
        """Test accessing the global registry."""
        registry = get_error_registry()
        assert isinstance(registry, ErrorRegistry)

        # Should be the same instance
        registry2 = get_error_registry()
        assert registry is registry2

    def test_global_format_error(self):
        """Test global format_error function."""
        formatted = format_error(
            "CONFIG_INVALID_PROVIDER", provider="TestProvider", supported_providers="Valid providers"
        )
        assert "TestProvider" in formatted
        assert "Valid providers" in formatted

    def test_global_get_full_error(self):
        """Test global get_full_error function."""
        full_error = get_full_error("CONFIG_MISSING_API_KEY", provider="TestProvider", key_name="TEST_API_KEY")
        assert "TestProvider" in full_error
        assert "TEST_API_KEY" in full_error
        assert "Solution:" in full_error

    def test_rich_formatting(self):
        """Test Rich formatting function."""
        registry = get_error_registry()
        error = registry.get("CONFIG_INVALID_PROVIDER")
        assert error is not None

        rich_formatted = create_error_with_rich_formatting(
            error, console_markup=True, provider="TestProvider", supported_providers="Valid providers"
        )

        assert "TestProvider" in rich_formatted
        assert "[red]" in rich_formatted or "[yellow]" in rich_formatted  # Should have color markup

        # Test without markup
        plain_formatted = create_error_with_rich_formatting(
            error, console_markup=False, provider="TestProvider", supported_providers="Valid providers"
        )
        assert "TestProvider" in plain_formatted
        assert "[red]" not in plain_formatted and "[yellow]" not in plain_formatted


class TestDefaultErrors:
    """Test cases for default registered errors."""

    def test_config_errors_exist(self):
        """Test that configuration errors are registered."""
        registry = get_error_registry()

        config_errors = [
            "CONFIG_INVALID_PROVIDER",
            "CONFIG_INVALID_TEMPERATURE",
            "CONFIG_MISSING_API_KEY",
            "CONFIG_INVALID_BASE_URL",
        ]

        for error_code in config_errors:
            error = registry.get(error_code)
            assert error is not None, f"Error {error_code} should be registered"
            assert error.category == ErrorCategory.CONFIGURATION

    def test_security_errors_exist(self):
        """Test that security errors are registered."""
        registry = get_error_registry()

        security_errors = [
            "SECURITY_PATH_TRAVERSAL",
            "SECURITY_DANGEROUS_FILENAME",
            "SECURITY_FILE_TOO_LARGE",
            "SECURITY_CODE_EXECUTION_DENIED",
        ]

        for error_code in security_errors:
            error = registry.get(error_code)
            assert error is not None, f"Error {error_code} should be registered"
            assert error.category == ErrorCategory.SECURITY

    def test_network_errors_exist(self):
        """Test that network errors are registered."""
        registry = get_error_registry()

        network_errors = [
            "NETWORK_CONNECTION_FAILED",
            "NETWORK_TIMEOUT",
            "NETWORK_API_RATE_LIMIT",
        ]

        for error_code in network_errors:
            error = registry.get(error_code)
            assert error is not None, f"Error {error_code} should be registered"
            assert error.category == ErrorCategory.NETWORK

    def test_error_solutions_provided(self):
        """Test that critical errors have solutions."""
        registry = get_error_registry()
        critical_errors = registry.get_errors_by_severity(ErrorSeverity.CRITICAL)

        for error in critical_errors:
            assert error.solution is not None, f"Critical error {error.code} should have a solution"
