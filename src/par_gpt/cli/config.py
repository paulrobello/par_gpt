"""Configuration setup and validation for PAR GPT CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from par_ai_core.llm_config import LlmConfig, LlmMode
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_gpt import __application_binary__, __env_var_prefix__
from par_gpt.lazy_import_manager import lazy_import
from par_gpt.tts_manager import TTSProvider


def load_environment() -> None:
    """Load environment variables from ~/.par_gpt.env file."""
    from dotenv import load_dotenv

    load_dotenv(Path(f"~/.{__application_binary__}.env").expanduser())


def initialize_globals_for_command(command: str) -> None:
    """Initialize global state based on command type."""
    from par_gpt.lazy_import_manager import initialize_globals_for_command as _init

    _init(command)


def set_environment_variables(
    user: str | None,
    redis_host: str | None,
    redis_port: int | None,
    console: Console | None = None,
) -> None:
    """Set environment variables with security warnings."""
    if console is None:
        console = console_err

    env_vars = []
    if user:
        env_vars.append((f"{__env_var_prefix__}_USER", user))
    if redis_host:
        env_vars.append((f"{__env_var_prefix__}_REDIS_HOST", redis_host))
    if redis_port:
        env_vars.append((f"{__env_var_prefix__}_REDIS_PORT", str(redis_port)))

    for var_name, var_value in env_vars:
        try:
            from par_gpt.utils.security_warnings import warn_environment_modification

            if not warn_environment_modification(
                var_name=var_name,
                var_value=var_value,
                console=console,
                skip_confirmation=True,  # These are CLI args, so just inform user
            ):
                console.print("[yellow]Note: Environment variable not set due to user choice[/yellow]")
            else:
                os.environ[var_name] = var_value
        except ImportError:
            # Fallback if security warnings module is not available
            console.print(f"[blue]Setting environment variable:[/blue] {var_name}")
            os.environ[var_name] = var_value


def validate_provider_api_key(ai_provider: LlmProvider, console: Console | None = None) -> None:
    """Validate that required API key is set for the provider."""
    if console is None:
        console = console_err

    if ai_provider not in [LlmProvider.OLLAMA, LlmProvider.LLAMACPP, LlmProvider.BEDROCK, LlmProvider.LITELLM]:
        # Lazy load provider utilities
        provider_env_key_names = lazy_import("par_ai_core.llm_providers", "provider_env_key_names")
        key_name = provider_env_key_names[ai_provider]
        if not os.environ.get(key_name):
            console.print(f"[bold red]{key_name} environment variable not set. Exiting...")
            raise typer.Exit(1)


def get_model_for_context(
    ai_provider: LlmProvider,
    model: str | None,
    light_model: bool,
    context_is_image: bool,
    command: str | None = None,
) -> tuple[str, str]:
    """Get appropriate model based on context and return (model, model_type)."""
    if model:
        return model, "specified"

    if command == "stardew":
        return "gpt-image-1", "image-gen"

    if light_model:
        # Lazy load light models
        provider_light_models = lazy_import("par_ai_core.llm_providers", "provider_light_models")
        model = provider_light_models[ai_provider]
        model_type = "light"
    elif context_is_image:
        # Lazy load vision models
        provider_vision_models = lazy_import("par_ai_core.llm_providers", "provider_vision_models")
        model = provider_vision_models[ai_provider]
        model_type = "vision"
    else:
        # Lazy load provider models
        provider_default_models = lazy_import("par_ai_core.llm_providers", "provider_default_models")
        model = provider_default_models[ai_provider]
        model_type = "default"

    if not model:
        raise ValueError(f"No supported {model_type} model found for {ai_provider}")

    return model, model_type


def get_base_url(ai_provider: LlmProvider, ai_base_url: str | None) -> str | None:
    """Get the base URL for the provider."""
    if ai_base_url == "none":
        # Lazy load provider base URLs
        provider_base_urls = lazy_import("par_ai_core.llm_providers", "provider_base_urls")
        return provider_base_urls[ai_provider]
    return ai_base_url


def create_llm_config(
    ai_provider: LlmProvider,
    model: str,
    fallback_models: list[str] | None = None,
    temperature: float = 0.5,
    ai_base_url: str | None = None,
    user_agent_appid: str | None = None,
    max_context_size: int = 0,
    reasoning_effort: Any | None = None,
    reasoning_budget: int | None = None,
    command: str | None = None,
) -> LlmConfig:
    """Create LLM configuration."""
    # Lazy load LLM configuration
    LlmConfig = lazy_import("par_ai_core.llm_config", "LlmConfig")

    mode = LlmMode.BASE if command == "stardew" else LlmMode.CHAT

    return LlmConfig(
        mode=mode,
        provider=ai_provider,
        model_name=model,
        fallback_models=fallback_models,
        temperature=temperature,
        base_url=ai_base_url,
        streaming=False,
        user_agent_appid=user_agent_appid,
        num_ctx=max_context_size or None,
        env_prefix=__env_var_prefix__,
        reasoning_effort=reasoning_effort,
        reasoning_budget=reasoning_budget,
    ).set_env()


def setup_tts_and_voice_input(
    tts: bool,
    tts_provider: TTSProvider | None,
    tts_voice: str | None,
    tts_list_voices: bool | None,
    voice_input: bool,
    debug: bool,
    console: Console | None = None,
) -> tuple[Any | None, Any | None]:
    """Setup TTS and voice input managers."""
    if console is None:
        console = console_err

    # Lazy import TTS and voice input managers
    TTSManger = lazy_import("par_gpt.tts_manager", "TTSManger")
    VoiceInputManager = lazy_import("par_gpt.voice_input_manager", "VoiceInputManager")

    tts_man: Any | None = None
    if tts:
        if tts_list_voices:
            voices = TTSManger(tts_provider or TTSProvider.KOKORO, console=console).list_voices()
            console.print("\nAvailable voices:", voices)
            raise typer.Exit(0)
        tts_man = TTSManger(tts_provider or TTSProvider.KOKORO, voice_name=tts_voice, console=console)

    voice_input_man: Any | None = None
    if voice_input:
        voice_input_man = VoiceInputManager(wake_word="jenny", verbose=debug or True, sanity_check_sentence=False)

    return tts_man, voice_input_man


def setup_timing(show_times: bool, show_times_detailed: bool) -> None:
    """Initialize timing system if requested."""
    if show_times or show_times_detailed:
        from par_gpt.utils.timing import enable_timing

        enable_timing()


def setup_redis(enable_redis: bool) -> None:
    """Configure Redis availability."""
    from par_gpt.utils.redis_manager import set_redis_enabled

    set_redis_enabled(enable_redis)
