"""Utility modules for PAR GPT with lazy loading support."""

# Import the lazy loader for better startup performance
from par_gpt.utils.lazy_utils_loader import (
    get_audio_utils,
    get_config_utils,
    get_console_utils,
    get_image_utils,
    get_llm_utils,
    get_path_security_utils,
    get_redis_utils,
    get_security_utils,
    get_timing_utils,
    lazy_utils_import,
)

# Import only the most essential items directly for backward compatibility
# Heavy modules are loaded lazily via the lazy_utils_loader
from par_gpt.utils.path_security import PathSecurityError


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
        "TimingData": lambda: lazy_utils_import("timing", "TimingData"),
        "TimingRegistry": lambda: lazy_utils_import("timing", "TimingRegistry"),
        "clear_timings": lambda: lazy_utils_import("timing", "clear_timings"),
        "disable_timing": lambda: lazy_utils_import("timing", "disable_timing"),
        "enable_timing": lambda: lazy_utils_import("timing", "enable_timing"),
        "get_timing_summary": lambda: lazy_utils_import("timing", "get_timing_summary"),
        "is_timing_enabled": lambda: lazy_utils_import("timing", "is_timing_enabled"),
        "print_timing_summary": lambda: lazy_utils_import("timing", "print_timing_summary"),
        "time_operation": lambda: lazy_utils_import("timing", "time_operation"),
        "timed": lambda: lazy_utils_import("timing", "timed"),
        "timer": lambda: lazy_utils_import("timing", "timer"),
    }

    if name in utils_maps:
        return utils_maps[name]()

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Note: Functions from original utils.py are NOT imported here to avoid circular imports
# Files that need these functions should implement basic versions directly
# This is a temporary solution to resolve import conflicts

__all__ = [
    # New utils modules
    "AudioResourceManager",
    "get_audio_manager",
    "safe_tts",
    "safe_voice_input",
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
    "print_timing_summary",
    "time_operation",
    "timed",
    "timer",
]
