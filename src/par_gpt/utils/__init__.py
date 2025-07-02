"""Utility modules for PAR GPT."""

# Import from new utils modules
from par_gpt.utils.audio_manager import AudioResourceManager, get_audio_manager, safe_tts, safe_voice_input
from par_gpt.utils.config import EnvironmentConfig, get_config
from par_gpt.utils.console_manager import ConsoleManager, get_console
from par_gpt.utils.image_processor import ImageProcessor, process_image
from par_gpt.utils.llm_invoker import LLMInvoker, invoke_llm
from par_gpt.utils.path_security import (
    PathSecurityError,
    SecurePathValidator,
    is_safe_download_path,
    sanitize_filename,
    secure_path_join,
    validate_path_component,
    validate_relative_path,
    validate_url_path,
    validate_within_base,
)
from par_gpt.utils.redis_manager import RedisOperationManager, get_redis_manager, with_redis_fallback
from par_gpt.utils.security_warnings import (
    warn_code_execution,
    warn_command_execution,
    warn_environment_modification,
    warn_subprocess_operation,
)
from par_gpt.utils.timing import (
    TimingData,
    TimingRegistry,
    clear_timings,
    disable_timing,
    enable_timing,
    get_timing_summary,
    is_timing_enabled,
    print_timing_summary,
    time_operation,
    timed,
    timer,
)

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
