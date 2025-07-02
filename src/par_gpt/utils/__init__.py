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

# Import from original utils.py to maintain backward compatibility
# Note: Using relative import to avoid circular import
from ..utils import (
    FigletFontName,
    ImageCaptureOutputType,
    VisibleWindow,
    cache_manager,
    capture_window_image,
    describe_image_with_llm,
    figlet_horizontal,
    figlet_vertical,
    get_redis_client,
    get_weather_current,
    get_weather_forecast,
    github_publish_repo,
    image_gen_dali,
    list_visible_windows_mac,
    mk_env_context,
    show_image_in_terminal,  # noqa: F401
    update_pyproject_deps,
)

__all__ = [
    # Original utils.py exports
    "FigletFontName",
    "ImageCaptureOutputType",
    "VisibleWindow",
    "cache_manager",
    "capture_window_image",
    "describe_image_with_llm",
    "figlet_horizontal",
    "figlet_vertical",
    "get_redis_client",
    "get_weather_current",
    "get_weather_forecast",
    "github_publish_repo",
    "image_gen_dali",
    "list_visible_windows_mac",
    "mk_env_context",
    "update_pyproject_deps",
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
]
