"""Configuration migration utilities for moving to validated configuration.

This module provides utilities to migrate from the current configuration system
to the new validated Pydantic-based configuration system.
"""

from __future__ import annotations

from typing import Any

from par_ai_core.llm_providers import LlmProvider
from par_ai_core.output_utils import DisplayOutputFormat
from par_ai_core.pricing_lookup import PricingDisplay

from par_gpt.cli.options import LoopMode
from par_gpt.tts_manager import TTSProvider
from par_gpt.utils.config_validation import PARGPTConfig


def migrate_cli_args_to_config(
    ai_provider: LlmProvider,
    model: str | None,
    fallback_models: list[str] | None,
    light_model: bool,
    ai_base_url: str | None,
    temperature: float,
    user_agent_appid: str | None,
    pricing: PricingDisplay,
    display_format: DisplayOutputFormat,
    context_location: str,
    system_prompt: str | None,
    user_prompt: str | None,
    max_context_size: int,
    reasoning_effort: Any,
    reasoning_budget: int | None,
    copy_to_clipboard: bool,
    copy_from_clipboard: bool,
    debug: bool,
    show_config: bool,
    user: str | None,
    redis_host: str | None,
    redis_port: int | None,
    enable_redis: bool,
    tts: bool,
    tts_provider: TTSProvider | None,
    tts_voice: str | None,
    voice_input: bool,
    chat_history: str | None,
    loop_mode: LoopMode,
    show_times: bool,
    show_times_detailed: bool,
    yes_to_all: bool,
    **kwargs: Any,
) -> PARGPTConfig:
    """Migrate CLI arguments to validated configuration.

    Args:
        All the CLI arguments from the current system.

    Returns:
        Validated PARGPTConfig instance.
    """
    # Map CLI arguments to configuration structure
    config_data = {
        "ai": {
            "provider": ai_provider.value if ai_provider else "OpenAI",
            "model": model,
            "fallback_models": fallback_models or [],
            "light_model": light_model,
            "temperature": temperature,
            "max_context_size": max_context_size,
            "base_url": ai_base_url,
        },
        "input": {
            "voice_input": voice_input,
            "context_location": context_location,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
        "output": {
            "display_format": display_format.value if display_format else "md",
            "pricing_display": pricing.value if pricing else "none",
            "copy_to_clipboard": copy_to_clipboard,
            "copy_from_clipboard": copy_from_clipboard,
        },
        "redis": {
            "host": redis_host or "localhost",
            "port": redis_port or 6379,
            "enabled": enable_redis,
        },
        "tts": {
            "enabled": tts,
            "provider": tts_provider.value if tts_provider else None,
            "voice": tts_voice,
        },
        "security": {
            "yes_to_all": yes_to_all,
            "allow_code_execution": kwargs.get("repl", False),
            "sandbox_enabled": kwargs.get("code_sandbox", False),
        },
        "performance": {
            "show_times": show_times,
            "show_times_detailed": show_times_detailed,
        },
        "debug": {
            "debug": debug,
            "show_config": show_config,
            "show_tool_calls": kwargs.get("show_tool_calls", debug),
        },
        "loop_mode": loop_mode.value if loop_mode else "one_shot",
        "user": user,
        "max_iterations": kwargs.get("max_iterations", 5),
        "chat_history": chat_history,
    }

    return PARGPTConfig(**config_data)


def config_to_state_dict(config: PARGPTConfig) -> dict[str, Any]:
    """Convert validated configuration back to state dictionary format.

    This maintains backward compatibility with the existing state management system.

    Args:
        config: Validated configuration.

    Returns:
        State dictionary compatible with existing code.
    """
    # Convert validated config back to the format expected by existing code
    return {
        "debug": config.debug.debug,
        "ai_provider": LlmProvider(config.ai.provider),
        "model": config.ai.model,
        "fallback_models": config.ai.fallback_models,
        "light_model": config.ai.light_model,
        "ai_base_url": config.ai.base_url,
        "pricing": PricingDisplay(config.output.pricing_display),
        "display_format": DisplayOutputFormat(config.output.display_format),
        "temperature": config.ai.temperature,
        "max_context_size": config.ai.max_context_size,
        "copy_to_clipboard": config.output.copy_to_clipboard,
        "copy_from_clipboard": config.output.copy_from_clipboard,
        "show_config": config.debug.show_config,
        "context_location": config.input.context_location,
        "system_prompt": config.input.system_prompt,
        "user_prompt": config.input.user_prompt,
        "loop_mode": LoopMode(config.loop_mode),
        "history_file": config.chat_history,
        "redis_host": config.redis.host,
        "redis_port": config.redis.port,
        "enable_redis": config.redis.enabled,
        "tts": config.tts.enabled,
        "tts_provider": TTSProvider(config.tts.provider) if config.tts.provider else None,
        "tts_voice": config.tts.voice,
        "voice_input": config.input.voice_input,
        "show_times": config.performance.show_times,
        "show_times_detailed": config.performance.show_times_detailed,
        "yes_to_all": config.security.yes_to_all,
        "max_iterations": config.max_iterations,
        "show_tool_calls": config.debug.show_tool_calls,
        "repl": config.security.allow_code_execution,
        "code_sandbox": config.security.sandbox_enabled,
        "user": config.user,
        # Additional fields that may be needed
        "store_url": "memory://",
        "collection_name": "par_gpt",
        "is_sixel_supported": False,
        "context": "",
        "context_is_image": False,
    }


def validate_migration_compatibility(config: PARGPTConfig) -> list[str]:
    """Validate that migrated configuration is compatible with existing code.

    Args:
        config: Configuration to validate.

    Returns:
        List of compatibility warnings.
    """
    warnings: list[str] = []

    # Check for provider-specific compatibility issues
    if config.ai.provider == "Groq" and config.input.system_prompt and config.input.context_location:
        warnings.append("Groq provider may not support images with system prompts")

    # Check for conflicting security settings
    if config.security.allow_code_execution and config.security.sandbox_enabled:
        warnings.append("Both REPL and sandbox modes enabled - sandbox takes precedence")

    # Check for Redis dependency
    if config.redis.enabled and not config.redis.host:
        warnings.append("Redis enabled but no host specified")

    # Check for TTS configuration
    if config.tts.enabled and not config.tts.provider:
        warnings.append("TTS enabled but no provider specified")

    return warnings


def get_config_diff(old_config: dict[str, Any], new_config: PARGPTConfig) -> dict[str, Any]:
    """Get differences between old and new configuration.

    Args:
        old_config: Original configuration dictionary.
        new_config: New validated configuration.

    Returns:
        Dictionary of differences.
    """
    new_state = config_to_state_dict(new_config)
    diff = {}

    # Find changed values
    for key in set(old_config.keys()) | set(new_state.keys()):
        old_value = old_config.get(key)
        new_value = new_state.get(key)

        if old_value != new_value:
            diff[key] = {"old": old_value, "new": new_value}

    return diff
