"""Backward compatibility module for PAR GPT utilities.

This module provides backward compatibility by importing utilities from par_utils
and the original utils.py, and exposing them through a consistent interface.
"""

# Import essential utilities from par_utils
from par_utils import (
    CacheManager,
    ConsoleManager,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    LazyImportManager,
    PathSecurityError,
    SecurePathValidator,
    TimingRegistry,
    disable_timing,
    enable_timing,
    is_timing_enabled,
    log_error,
    sanitize_filename,
    show_timing_details,
    show_timing_summary,
    suppress_error,
    timed,
    timer,
    user_timer,
    validate_relative_path,
    validate_within_base,
)

# Create instances for backward compatibility
_console_manager = ConsoleManager()
_lazy_import_manager = LazyImportManager()


def get_console(console=None):
    """Get the global console instance."""
    return _console_manager.get_console(console)


def _import_from_original_utils(function_name: str):
    """Import function from the original utils.py file."""
    # Import the original utils module with importlib to avoid conflicts
    import importlib.util
    from pathlib import Path

    # Get the path to the original utils.py file
    utils_py_path = Path(__file__).parent.parent / "utils.py"

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("original_utils", utils_py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load original utils.py from {utils_py_path}")

    original_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original_utils)

    # Get the requested function
    if not hasattr(original_utils, function_name):
        raise AttributeError(f"Function '{function_name}' not found in original utils.py")

    return getattr(original_utils, function_name)


def _import_from_par_utils(function_name: str):
    """Import function from par_utils package."""
    import par_utils

    return getattr(par_utils, function_name)


def lazy_utils_import(module_name: str, item_name: str):
    """Import a specific item from a utils module."""
    from par_utils import LazyUtilsLoader

    loader = LazyUtilsLoader()
    return loader.get_utils_item(module_name, item_name)


def __getattr__(name: str):
    """Dynamically import utils items when accessed."""
    # Try to get the item from various utils modules lazily
    utils_maps = {
        # Audio utilities
        "AudioResourceManager": lambda: lazy_utils_import("audio_manager", "AudioResourceManager"),
        "get_audio_manager": lambda: lazy_utils_import("audio_manager", "get_audio_manager"),
        "safe_tts": lambda: lazy_utils_import("audio_manager", "safe_tts"),
        "safe_voice_input": lambda: lazy_utils_import("audio_manager", "safe_voice_input"),
        # Config utilities
        "EnvironmentConfig": lambda: lazy_utils_import("config", "EnvironmentConfig"),
        "get_config": lambda: lazy_utils_import("config", "get_config"),
        # Console utilities
        "ConsoleManager": lambda: lazy_utils_import("console_manager", "ConsoleManager"),
        "get_console": lambda: lazy_utils_import("console_manager", "get_console"),
        # Image utilities
        "ImageProcessor": lambda: lazy_utils_import("image_processor", "ImageProcessor"),
        "process_image": lambda: lazy_utils_import("image_processor", "process_image"),
        # LLM utilities
        "LLMInvoker": lambda: lazy_utils_import("llm_invoker", "LLMInvoker"),
        "invoke_llm": lambda: lazy_utils_import("llm_invoker", "invoke_llm"),
        # Path security utilities
        "SecurePathValidator": lambda: lazy_utils_import("path_security", "SecurePathValidator"),
        "is_safe_download_path": lambda: lazy_utils_import("path_security", "is_safe_download_path"),
        "sanitize_filename": lambda: lazy_utils_import("path_security", "sanitize_filename"),
        "secure_path_join": lambda: lazy_utils_import("path_security", "secure_path_join"),
        "validate_path_component": lambda: lazy_utils_import("path_security", "validate_path_component"),
        "validate_relative_path": lambda: lazy_utils_import("path_security", "validate_relative_path"),
        "validate_url_path": lambda: lazy_utils_import("path_security", "validate_url_path"),
        "validate_within_base": lambda: lazy_utils_import("path_security", "validate_within_base"),
        # Redis utilities
        "RedisOperationManager": lambda: lazy_utils_import("redis_manager", "RedisOperationManager"),
        "get_redis_manager": lambda: lazy_utils_import("redis_manager", "get_redis_manager"),
        "with_redis_fallback": lambda: lazy_utils_import("redis_manager", "with_redis_fallback"),
        # Security warnings
        "warn_code_execution": lambda: lazy_utils_import("security_warnings", "warn_code_execution"),
        "warn_command_execution": lambda: lazy_utils_import("security_warnings", "warn_command_execution"),
        "warn_environment_modification": lambda: lazy_utils_import(
            "security_warnings", "warn_environment_modification"
        ),
        "warn_subprocess_operation": lambda: lazy_utils_import("security_warnings", "warn_subprocess_operation"),
        # Timing utilities
        "TimingData": lambda: _import_from_par_utils("TimingData"),
        "TimingRegistry": lambda: _import_from_par_utils("TimingRegistry"),
        "clear_timings": lambda: _import_from_par_utils("clear_timings"),
        "disable_timing": lambda: _import_from_par_utils("disable_timing"),
        "enable_timing": lambda: _import_from_par_utils("enable_timing"),
        "get_timing_summary": lambda: _import_from_par_utils("get_timing_summary"),
        "is_timing_enabled": lambda: _import_from_par_utils("is_timing_enabled"),
        "show_timing_summary": lambda: _import_from_par_utils("show_timing_summary"),
        "show_timing_details": lambda: _import_from_par_utils("show_timing_details"),
        "time_operation": lambda: _import_from_par_utils("time_operation"),
        "timed": lambda: _import_from_par_utils("timed"),
        "timer": lambda: _import_from_par_utils("timer"),
        "user_timer": lambda: _import_from_par_utils("user_timer"),
        # Weather utilities (from original utils.py)
        "get_weather_current": lambda: _import_from_original_utils("get_weather_current"),
        "get_weather_forecast": lambda: _import_from_original_utils("get_weather_forecast"),
        # Original utils.py functions for AI tools
        "show_image_in_terminal": lambda: _import_from_original_utils("show_image_in_terminal"),
        "github_publish_repo": lambda: _import_from_original_utils("github_publish_repo"),
        "figlet_horizontal": lambda: _import_from_original_utils("figlet_horizontal"),
        "figlet_vertical": lambda: _import_from_original_utils("figlet_vertical"),
        "list_visible_windows_mac": lambda: _import_from_original_utils("list_visible_windows_mac"),
        "list_available_screens": lambda: _import_from_original_utils("list_available_screens"),
        "capture_screen_image": lambda: _import_from_original_utils("capture_screen_image"),
        "capture_window_image": lambda: _import_from_original_utils("capture_window_image"),
        "describe_image_with_llm": lambda: _import_from_original_utils("describe_image_with_llm"),
        "image_gen_dali": lambda: _import_from_original_utils("image_gen_dali"),
    }

    if name in utils_maps:
        return utils_maps[name]()

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Note: Functions from original utils.py are NOT imported here to avoid circular imports
# Files that need these functions should implement basic versions directly
# This is a temporary solution to resolve import conflicts

__all__ = [
    # Lazy loader functions
    "get_audio_utils",
    "get_config_utils",
    "get_console_utils",
    "get_image_utils",
    "get_llm_utils",
    "get_path_security_utils",
    "get_redis_utils",
    "get_security_utils",
    "get_timing_utils",
    "lazy_utils_import",
    # New utils modules
    "AudioResourceManager",
    "get_audio_manager",
    "safe_tts",
    "safe_voice_input",
    "CacheManager",
    "ConsoleManager",
    "get_console",
    "EnvironmentConfig",
    "get_config",
    "ImageProcessor",
    "process_image",
    "LLMInvoker",
    "invoke_llm",
    "RedisOperationManager",
    "get_redis_manager",
    "with_redis_fallback",
    # Error handling
    "ErrorCategory",
    "ErrorHandler",
    "ErrorSeverity",
    "log_error",
    "suppress_error",
    # Path security
    "PathSecurityError",
    "SecurePathValidator",
    "is_safe_download_path",
    "sanitize_filename",
    "secure_path_join",
    "validate_path_component",
    "validate_relative_path",
    "validate_url_path",
    "validate_within_base",
    # Security warnings
    "warn_code_execution",
    "warn_command_execution",
    "warn_environment_modification",
    "warn_subprocess_operation",
    # Timing utilities
    "TimingData",
    "TimingRegistry",
    "clear_timings",
    "disable_timing",
    "enable_timing",
    "get_timing_summary",
    "is_timing_enabled",
    "show_timing_details",
    "show_timing_summary",
    "time_operation",
    "timed",
    "timer",
    "user_timer",
    # Weather utilities
    "get_weather_current",
    "get_weather_forecast",
    # Original utils.py functions for AI tools
    "show_image_in_terminal",
    "github_publish_repo",
    "figlet_horizontal",
    "figlet_vertical",
    "list_visible_windows_mac",
    "list_available_screens",
    "capture_screen_image",
    "capture_window_image",
    "describe_image_with_llm",
    "image_gen_dali",
]
