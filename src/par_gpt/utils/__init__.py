"""PAR GPT utilities package.

Public surface for ``par_gpt.utils``. Domain logic lives in concrete submodules
(``weather``, ``screen_capture``, ``figlet_utils``, ``media_generation``, etc.);
this module re-exports their names for backward compatibility.

All lazy attribute access resolves through *normal* Python submodule imports
(cached in ``sys.modules``). The legacy ``utils.py`` monolith and its off-disk
``importlib.util.spec_from_file_location`` re-execution have been removed -- see
ARC-001. Singletons (``cache_manager``) live in ``_singletons`` and are
constructed exactly once.
"""

from __future__ import annotations

# Essential utilities re-exported from par_utils (external package; no cycle).
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

# Shared singleton -- constructed exactly once here (normal module caching).
from ._singletons import cache_manager

# Light submodules: top-level deps are already loaded above (par_utils,
# par_ai_core, pydantic, rich, stdlib). All heavy dependencies (PIL, Quartz,
# pyfiglet, elevenlabs, DALL-E, redis, requests) are imported lazily *inside*
# the functions, so importing these names does not regress startup. Importing
# them eagerly here also makes them statically visible to pyright.
from .env_context import mk_env_context
from .figlet_utils import FigletFontName, figlet_horizontal, figlet_vertical
from .image_description import describe_image_with_llm
from .media_generation import image_gen_dali, speak
from .pyproject_deps import update_pyproject_deps
from .redis_client import get_redis_client
from .screen_capture import (
    AvailableScreen,
    ImageCaptureOutputType,
    VisibleWindow,
    capture_screen_image,
    capture_screen_image_mac,
    capture_window_image,
    capture_window_image_mac,
    list_available_screens,
    list_available_screens_mac,
    list_visible_windows,
    list_visible_windows_mac,
)
from .security_warnings import (
    warn_code_execution,
    warn_command_execution,
    warn_environment_modification,
    warn_subprocess_operation,
)
from .terminal_image import show_image_in_terminal
from .weather import get_weather_current, get_weather_forecast

# Create shared instances for backward compatibility.
_console_manager = ConsoleManager()
_lazy_import_manager = LazyImportManager()


def get_console(console=None):
    """Get the global console instance."""
    return _console_manager.get_console(console)


def lazy_utils_import(module_name: str, item_name: str):
    """Import a specific item from a utils submodule (backward compatibility)."""
    from par_utils import LazyUtilsLoader

    loader = LazyUtilsLoader()
    return loader.get_utils_item(module_name, item_name)


# Heavy submodules kept lazy: their top-level imports pull optional/heavy deps
# (audio_manager -> TTS/voice backends, image_processor -> rich_pixels,
# redis_manager -> redis, config -> pydantic_settings, llm_invoker ->
# langchain_core, github_utils -> git). They are resolved on first access via a
# normal cached importlib import -- never the deleted off-disk re-execution.
_SUBMODULE_MAP: dict[str, tuple[str, str]] = {
    # Audio utilities (TTS / voice backends)
    "AudioResourceManager": ("audio_manager", "AudioResourceManager"),
    "get_audio_manager": ("audio_manager", "get_audio_manager"),
    "safe_tts": ("audio_manager", "safe_tts"),
    "safe_voice_input": ("audio_manager", "safe_voice_input"),
    # Config utilities (pydantic_settings)
    "EnvironmentConfig": ("config", "EnvironmentConfig"),
    "get_config": ("config", "get_config"),
    # Image utilities (rich_pixels)
    "ImageProcessor": ("image_processor", "ImageProcessor"),
    "process_image": ("image_processor", "process_image"),
    # LLM utilities (langchain_core)
    "LLMInvoker": ("llm_invoker", "LLMInvoker"),
    "invoke_llm": ("llm_invoker", "invoke_llm"),
    # Redis operation manager (redis)
    "RedisOperationManager": ("redis_manager", "RedisOperationManager"),
    "get_redis_manager": ("redis_manager", "get_redis_manager"),
    "with_redis_fallback": ("redis_manager", "with_redis_fallback"),
    # GitHub repo publishing (git)
    "github_publish_repo": ("github_utils", "github_publish_repo"),
}


def _load(submodule: str, item: str):
    """Import ``item`` from sibling ``par_gpt.utils.<submodule>`` (cached import)."""
    import importlib

    return getattr(importlib.import_module(f".{submodule}", __name__), item)


def __getattr__(name: str):
    """Lazily resolve utils names through normal submodule imports.

    This replaces the legacy off-disk ``importlib.util`` re-execution. Submodules
    are imported once and cached in ``sys.modules``, so module-level singletons
    are constructed exactly once.
    """
    entry = _SUBMODULE_MAP.get(name)
    if entry is not None:
        submodule, item = entry
        return _load(submodule, item)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Lazy loader helper
    "lazy_utils_import",
    # Shared singleton
    "cache_manager",
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
    "get_redis_client",
    # Error handling
    "ErrorCategory",
    "ErrorHandler",
    "ErrorSeverity",
    "log_error",
    "suppress_error",
    # Path security
    "PathSecurityError",
    "SecurePathValidator",
    "sanitize_filename",
    "validate_relative_path",
    "validate_within_base",
    # Security warnings
    "warn_code_execution",
    "warn_command_execution",
    "warn_environment_modification",
    "warn_subprocess_operation",
    # Timing utilities
    "TimingRegistry",
    "disable_timing",
    "enable_timing",
    "is_timing_enabled",
    "show_timing_details",
    "show_timing_summary",
    "timed",
    "timer",
    "user_timer",
    # Weather utilities
    "get_weather_current",
    "get_weather_forecast",
    # Terminal image display
    "show_image_in_terminal",
    # Environment context
    "mk_env_context",
    # Figlet
    "FigletFontName",
    "figlet_horizontal",
    "figlet_vertical",
    # Screen / window enumeration + capture
    "VisibleWindow",
    "AvailableScreen",
    "ImageCaptureOutputType",
    "list_visible_windows_mac",
    "list_visible_windows",
    "list_available_screens_mac",
    "list_available_screens",
    "capture_window_image_mac",
    "capture_window_image",
    "capture_screen_image_mac",
    "capture_screen_image",
    # Image description via LLM
    "describe_image_with_llm",
    # Media generation
    "speak",
    "image_gen_dali",
    # Pyproject dependency syncing
    "update_pyproject_deps",
    # GitHub repo publishing
    "github_publish_repo",
]
