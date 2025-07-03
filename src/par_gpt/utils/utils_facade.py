"""Utils facade to resolve circular import issues cleanly.

This module provides a clean interface to utils functions without circular imports.
It uses lazy loading and proper dependency injection patterns.
"""

from __future__ import annotations

from typing import Any, Protocol


class UtilsFunctionProtocol(Protocol):
    """Protocol for utils functions to ensure type safety."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Generic callable protocol."""
        ...


class UtilsFacade:
    """Facade for accessing utils functions without circular imports."""

    def __init__(self) -> None:
        """Initialize the facade with lazy loading."""
        self._utils_cache: dict[str, Any] = {}

    def _get_utils_function(self, function_name: str) -> UtilsFunctionProtocol:
        """Get a utils function with lazy loading and caching."""
        if function_name in self._utils_cache:
            return self._utils_cache[function_name]

        try:
            # Import from the utils package using lazy import manager
            from par_utils import LazyImportManager

            _lazy_import_manager = LazyImportManager()
            lazy_import = _lazy_import_manager.get_cached_import

            # Try to get function from utils module
            utils_func = lazy_import("par_gpt.utils", function_name)
            self._utils_cache[function_name] = utils_func
            return utils_func

        except (ImportError, AttributeError):
            # Create a stub function if import fails
            def stub_function(*args: Any, **kwargs: Any) -> Any:
                return f"Function '{function_name}' not available due to import restrictions"

            self._utils_cache[function_name] = stub_function
            return stub_function

    def capture_window_image(self, *args: Any, **kwargs: Any) -> Any:
        """Capture window image with lazy loading."""
        return self._get_utils_function("capture_window_image")(*args, **kwargs)

    def describe_image_with_llm(self, *args: Any, **kwargs: Any) -> Any:
        """Describe image with LLM with lazy loading."""
        return self._get_utils_function("describe_image_with_llm")(*args, **kwargs)

    def get_weather_current(self, *args: Any, **kwargs: Any) -> Any:
        """Get current weather with lazy loading."""
        return self._get_utils_function("get_weather_current")(*args, **kwargs)

    def get_weather_forecast(self, *args: Any, **kwargs: Any) -> Any:
        """Get weather forecast with lazy loading."""
        return self._get_utils_function("get_weather_forecast")(*args, **kwargs)

    def show_image_in_terminal(self, *args: Any, **kwargs: Any) -> Any:
        """Show image in terminal with lazy loading."""
        return self._get_utils_function("show_image_in_terminal")(*args, **kwargs)

    def github_publish_repo(self, *args: Any, **kwargs: Any) -> Any:
        """Publish GitHub repo with lazy loading."""
        return self._get_utils_function("github_publish_repo")(*args, **kwargs)

    def figlet_horizontal(self, *args: Any, **kwargs: Any) -> Any:
        """Generate horizontal figlet text with lazy loading."""
        return self._get_utils_function("figlet_horizontal")(*args, **kwargs)

    def figlet_vertical(self, *args: Any, **kwargs: Any) -> Any:
        """Generate vertical figlet text with lazy loading."""
        return self._get_utils_function("figlet_vertical")(*args, **kwargs)

    def list_visible_windows_mac(self, *args: Any, **kwargs: Any) -> Any:
        """List visible Mac windows with lazy loading."""
        return self._get_utils_function("list_visible_windows_mac")(*args, **kwargs)

    def image_gen_dali(self, *args: Any, **kwargs: Any) -> Any:
        """Generate image with DALL-E with lazy loading."""
        return self._get_utils_function("image_gen_dali")(*args, **kwargs)

    def list_available_screens(self, *args: Any, **kwargs: Any) -> Any:
        """List available screens with lazy loading."""
        return self._get_utils_function("list_available_screens")(*args, **kwargs)

    def capture_screen_image(self, *args: Any, **kwargs: Any) -> Any:
        """Capture screen image with lazy loading."""
        return self._get_utils_function("capture_screen_image")(*args, **kwargs)


# Global facade instance
_utils_facade = UtilsFacade()


def get_utils_facade() -> UtilsFacade:
    """Get the global utils facade instance."""
    return _utils_facade
