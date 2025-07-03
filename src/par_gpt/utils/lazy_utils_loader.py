"""Lazy loading system for utils modules to break import cascades."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any


class LazyUtilsLoader:
    """Lazy loader for utils modules to reduce startup time."""

    def __init__(self) -> None:
        """Initialize the lazy utils loader."""
        self._utils_cache: dict[str, Any] = {}

    def get_utils_item(self, module_name: str, item_name: str) -> Any:
        """Get a specific item from a utils module."""
        cache_key = f"{module_name}.{item_name}"

        if cache_key in self._utils_cache:
            return self._utils_cache[cache_key]

        # Import the utils module
        module = importlib.import_module(f"par_gpt.utils.{module_name}")
        item = getattr(module, item_name)

        self._utils_cache[cache_key] = item
        return item

    def get_audio_manager(self) -> Any:
        """Get AudioResourceManager lazily."""
        return self.get_utils_item("audio_manager", "AudioResourceManager")

    def get_safe_tts(self) -> Callable:
        """Get safe_tts function lazily."""
        return self.get_utils_item("audio_manager", "safe_tts")

    def get_safe_voice_input(self) -> Callable:
        """Get safe_voice_input function lazily."""
        return self.get_utils_item("audio_manager", "safe_voice_input")

    def get_console_manager(self) -> Any:
        """Get ConsoleManager lazily."""
        return self.get_utils_item("console_manager", "ConsoleManager")

    def get_environment_config(self) -> Any:
        """Get EnvironmentConfig lazily."""
        return self.get_utils_item("config", "EnvironmentConfig")

    def get_image_processor(self) -> Any:
        """Get ImageProcessor lazily."""
        return self.get_utils_item("image_processor", "ImageProcessor")

    def get_llm_invoker(self) -> Any:
        """Get LLMInvoker lazily."""
        return self.get_utils_item("llm_invoker", "LLMInvoker")

    def get_redis_manager(self) -> Any:
        """Get RedisOperationManager lazily."""
        return self.get_utils_item("redis_manager", "RedisOperationManager")

    def get_path_security_validator(self) -> Any:
        """Get SecurePathValidator lazily."""
        return self.get_utils_item("path_security", "SecurePathValidator")

    def get_timing_functions(self) -> dict[str, Any]:
        """Get timing functions lazily."""
        return {
            "timer": self.get_utils_item("timing", "timer"),
            "timed": self.get_utils_item("timing", "timed"),
            "enable_timing": self.get_utils_item("timing", "enable_timing"),
            "disable_timing": self.get_utils_item("timing", "disable_timing"),
            "is_timing_enabled": self.get_utils_item("timing", "is_timing_enabled"),
        }

    def get_security_warnings(self) -> dict[str, Any]:
        """Get security warning functions lazily."""
        return {
            "warn_code_execution": self.get_utils_item("security_warnings", "warn_code_execution"),
            "warn_command_execution": self.get_utils_item("security_warnings", "warn_command_execution"),
            "warn_environment_modification": self.get_utils_item("security_warnings", "warn_environment_modification"),
            "warn_subprocess_operation": self.get_utils_item("security_warnings", "warn_subprocess_operation"),
        }


# Global lazy utils loader instance
_lazy_utils_loader = LazyUtilsLoader()


def lazy_utils_import(module_name: str, item_name: str) -> Any:
    """Convenience function for lazy utils imports."""
    return _lazy_utils_loader.get_utils_item(module_name, item_name)


def get_timing_utils() -> dict[str, Any]:
    """Get timing utilities lazily."""
    return _lazy_utils_loader.get_timing_functions()


def get_audio_utils() -> dict[str, Any]:
    """Get audio utilities lazily."""
    return {
        "AudioResourceManager": _lazy_utils_loader.get_audio_manager(),
        "safe_tts": _lazy_utils_loader.get_safe_tts(),
        "safe_voice_input": _lazy_utils_loader.get_safe_voice_input(),
    }


def get_security_utils() -> dict[str, Any]:
    """Get security utilities lazily."""
    return _lazy_utils_loader.get_security_warnings()


def get_config_utils() -> dict[str, Any]:
    """Get configuration utilities lazily."""
    return {
        "EnvironmentConfig": _lazy_utils_loader.get_environment_config(),
    }


def get_console_utils() -> dict[str, Any]:
    """Get console utilities lazily."""
    return {
        "ConsoleManager": _lazy_utils_loader.get_console_manager(),
    }


def get_image_utils() -> dict[str, Any]:
    """Get image utilities lazily."""
    return {
        "ImageProcessor": _lazy_utils_loader.get_image_processor(),
    }


def get_llm_utils() -> dict[str, Any]:
    """Get LLM utilities lazily."""
    return {
        "LLMInvoker": _lazy_utils_loader.get_llm_invoker(),
    }


def get_redis_utils() -> dict[str, Any]:
    """Get Redis utilities lazily."""
    return {
        "RedisOperationManager": _lazy_utils_loader.get_redis_manager(),
    }


def get_path_security_utils() -> dict[str, Any]:
    """Get path security utilities lazily."""
    return {
        "SecurePathValidator": _lazy_utils_loader.get_path_security_validator(),
        "sanitize_filename": lazy_utils_import("path_security", "sanitize_filename"),
        "validate_relative_path": lazy_utils_import("path_security", "validate_relative_path"),
        "validate_within_base": lazy_utils_import("path_security", "validate_within_base"),
    }
