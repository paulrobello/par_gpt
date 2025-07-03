"""Main Typer app setup and global callback for PAR GPT."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from par_ai_core.llm_config import ReasoningEffort
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.output_utils import DisplayOutputFormat
from par_ai_core.par_logging import console_err
from par_ai_core.pricing_lookup import PricingDisplay
from rich.console import Console

from par_gpt import __application_title__, __env_var_prefix__, __version__
from par_gpt.cli.config import (
    create_llm_config,
    get_base_url,
    get_model_for_context,
    initialize_globals_for_command,
    load_environment,
    set_environment_variables,
    setup_redis,
    setup_timing,
    setup_tts_and_voice_input,
    validate_provider_api_key,
)
from par_gpt.cli.context import ContextProcessor
from par_gpt.cli.options import GLOBAL_OPTION_DEFAULTS, LoopMode
from par_gpt.cli.security import check_mutual_exclusivity
from par_gpt.lazy_import_manager import lazy_import
from par_gpt.tts_manager import TTSProvider


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__application_title__}: {__version__}")
        raise typer.Exit()


# Create the main Typer app
app = typer.Typer()


@app.callback()
def main(
    ctx: typer.Context,
    ai_provider: Annotated[
        LlmProvider,
        typer.Option(
            "--ai-provider",
            "-a",
            envvar=f"{__env_var_prefix__}_AI_PROVIDER",
            help="AI provider to use for processing",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["ai_provider"],
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            envvar=f"{__env_var_prefix__}_MODEL",
            help="AI model to use for processing. If not specified, a default model will be used.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["model"],
    fallback_models: Annotated[
        list[str] | None,
        typer.Option(
            "--fallback-models",
            "-B",
            envvar=f"{__env_var_prefix__}_FALLBACK_MODELS",
            help="Fallback models to use if the specified model is not available.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["fallback_models"],
    light_model: Annotated[
        bool,
        typer.Option(
            "--light-model",
            "-l",
            envvar=f"{__env_var_prefix__}_LIGHT_MODEL",
            help="Use a light model for processing. If not specified, a default model will be used.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["light_model"],
    ai_base_url: Annotated[
        str | None,
        typer.Option(
            "--ai-base-url",
            "-b",
            envvar=f"{__env_var_prefix__}_AI_BASE_URL",
            help="Override the base URL for the AI provider.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["ai_base_url"],
    temperature: Annotated[
        float,
        typer.Option(
            "--temperature",
            "-t",
            envvar=f"{__env_var_prefix__}_TEMPERATURE",
            help="Temperature to use for processing. If not specified, a default temperature will be used.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["temperature"],
    user_agent_appid: Annotated[
        str | None,
        typer.Option(
            "--user-agent-appid",
            "-U",
            envvar=f"{__env_var_prefix__}_USER_AGENT_APPID",
            help="Extra data to include in the User-Agent header for the AI provider.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["user_agent_appid"],
    pricing: Annotated[
        PricingDisplay,
        typer.Option(
            "--pricing",
            "-p",
            envvar=f"{__env_var_prefix__}_PRICING",
            help="Enable pricing summary display",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["pricing"],
    display_format: Annotated[
        DisplayOutputFormat,
        typer.Option(
            "--display-output",
            "-d",
            envvar=f"{__env_var_prefix__}_DISPLAY_OUTPUT",
            help="Display output in terminal (none, plain, md, csv, or json)",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["display_format"],
    context_location: Annotated[
        str,
        typer.Option(
            "--context-location",
            "-f",
            help="Location of context to use for processing.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["context_location"],
    system_prompt: Annotated[
        str | None,
        typer.Option(
            "--system-prompt",
            "-s",
            help="System prompt to use for processing. If not specified, a default system prompt will be used.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["system_prompt"],
    user_prompt: Annotated[
        str | None,
        typer.Option(
            "--user-prompt",
            "-u",
            help="User prompt to use for processing. If not specified, a default user prompt will be used.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["user_prompt"],
    max_context_size: Annotated[
        int,
        typer.Option(
            "--max-context-size",
            "-M",
            envvar=f"{__env_var_prefix__}_MAX_CONTEXT_SIZE",
            help="Maximum context size when provider supports it. 0 = default. This must be set to more than reasoning_budget if reasoning_budget is set.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["max_context_size"],
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(
            "--reasoning-effort",
            envvar=f"{__env_var_prefix__}_REASONING_EFFORT",
            help="Reasoning effort level to use for o1 and o3 models.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["reasoning_effort"],
    reasoning_budget: Annotated[
        int | None,
        typer.Option(
            "--reasoning-budget",
            envvar=f"{__env_var_prefix__}_REASONING_BUDGET",
            help="Maximum context size for reasoning.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["reasoning_budget"],
    copy_to_clipboard: Annotated[
        bool,
        typer.Option(
            "--copy-to-clipboard",
            "-c",
            help="Copy output to clipboard",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["copy_to_clipboard"],
    copy_from_clipboard: Annotated[
        bool,
        typer.Option(
            "--copy-from-clipboard",
            "-C",
            help="Copy context or context location from clipboard",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["copy_from_clipboard"],
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-D",
            envvar=f"{__env_var_prefix__}_DEBUG",
            help="Enable debug mode",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["debug"],
    show_config: Annotated[
        bool,
        typer.Option(
            "--show-config",
            "-S",
            envvar=f"{__env_var_prefix__}_SHOW_CONFIG",
            help="Show config",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["show_config"],
    user: Annotated[
        str | None,
        typer.Option(
            "--user",
            "-P",
            envvar=f"{__env_var_prefix__}_USER",
            help="User to use for memory and preferences. Defaults to logged in users username.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["user"],
    redis_host: Annotated[
        str | None,
        typer.Option(
            "--redis-host",
            "-r",
            envvar=f"{__env_var_prefix__}_REDIS_HOST",
            help="Host or ip of redis server. Used for memory functions.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["redis_host"],
    redis_port: Annotated[
        int | None,
        typer.Option(
            "--redis-port",
            "-R",
            envvar=f"{__env_var_prefix__}_REDIS_PORT",
            help="Redis port number. Used for memory functions.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["redis_port"],
    enable_redis: Annotated[
        bool,
        typer.Option(
            "--enable-redis",
            envvar=f"{__env_var_prefix__}_ENABLE_REDIS",
            help="Enable Redis memory functionality.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["enable_redis"],
    tts: Annotated[
        bool,
        typer.Option(
            "--tts",
            "-T",
            envvar=f"{__env_var_prefix__}_TTS",
            help="Use TTS for LLM response.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["tts"],
    tts_provider: Annotated[
        TTSProvider | None,
        typer.Option(
            "--tts-provider",
            envvar=f"{__env_var_prefix__}_TTS_PROVIDER",
            help="Provider to use for TTS. Defaults to kokoro",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["tts_provider"],
    tts_voice: Annotated[
        str | None,
        typer.Option(
            "--tts-voice",
            envvar=f"{__env_var_prefix__}_TTS_VOICE",
            help="Voice to use for TTS. Depends on TTS provider chosen.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["tts_voice"],
    tts_list_voices: Annotated[
        bool | None,
        typer.Option(
            "--tts-list-voices",
            help="List voices for selected TTS provider.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["tts_list_voices"],
    voice_input: Annotated[
        bool,
        typer.Option(
            "--voice-input",
            help="Use voice input.",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["voice_input"],
    chat_history: Annotated[
        str | None,
        typer.Option(
            "--chat-history",
            envvar=f"{__env_var_prefix__}_CHAT_HISTORY",
            help="Save and or resume chat history from file",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["chat_history"],
    loop_mode: Annotated[
        LoopMode,
        typer.Option(
            "--loop-mode",
            "-L",
            envvar=f"{__env_var_prefix__}_LOOP_MODE",
            help="One shot or infinite mode",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["loop_mode"],
    show_times: Annotated[
        bool,
        typer.Option(
            "--show-times",
            envvar=f"{__env_var_prefix__}_SHOW_TIMES",
            help="Show timing information for various operations",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["show_times"],
    show_times_detailed: Annotated[
        bool,
        typer.Option(
            "--show-times-detailed",
            envvar=f"{__env_var_prefix__}_SHOW_TIMES_DETAILED",
            help="Show detailed timing information with hierarchical breakdown",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["show_times_detailed"],
    yes_to_all: Annotated[
        bool,
        typer.Option(
            "--yes-to-all",
            "-y",
            envvar=f"{__env_var_prefix__}_YES_TO_ALL",
            help="Automatically accept all security warnings and confirmation prompts",
        ),
    ] = GLOBAL_OPTION_DEFAULTS["yes_to_all"],
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
):
    """PAR GPT Global Options"""

    console = console_err

    # Load environment variables lazily after command is determined
    load_environment()

    # Initialize globals based on command type
    command = ctx.invoked_subcommand or "help"
    initialize_globals_for_command(command)

    # Set Redis enabled flag early to prevent connection attempts when disabled
    setup_redis(enable_redis)

    # Initialize timing system if requested
    setup_timing(show_times, show_times_detailed)

    # Set environment variables with security warnings
    set_environment_variables(user, redis_host, redis_port, console)

    # Validate provider API key
    validate_provider_api_key(ai_provider, console)

    # Check for mutually exclusive options
    check_mutual_exclusivity(copy_from_clipboard, context_location, console)

    # Process context
    context_processor = ContextProcessor(console)
    context_location = context_processor.process_clipboard(copy_from_clipboard, context_location)
    context_is_url, context_is_file = context_processor.validate_context_location(context_location)
    context = context_processor.process_stdin(context_location, copy_from_clipboard)

    # Process context content (images, URLs, files)
    if context_location:
        context_content, context_is_image = context_processor.process_context_content(
            context_location, context_is_url, context_is_file, show_times, show_times_detailed
        )
        if context_content:
            context = context_content
    else:
        context_is_image = False

    # Get appropriate model for context
    try:
        model, model_type = get_model_for_context(ai_provider, model, light_model, context_is_image, command)
        console.print(f"[bold green]Auto selected {model_type} model: {model}")
    except ValueError as e:
        console.print(f"[bold red]{e}. Exiting...")
        raise typer.Exit(1)

    # Get base URL
    ai_base_url = get_base_url(ai_provider, ai_base_url)

    # Create LLM config with timing
    from par_gpt.utils.timing import timer

    with timer("llm_config_setup"):
        llm_config = create_llm_config(
            ai_provider,
            model,
            fallback_models,
            temperature,
            ai_base_url,
            user_agent_appid,
            max_context_size,
            reasoning_effort,
            reasoning_budget,
            command,
        )

    # Setup TTS and voice input
    tts_man, voice_input_man = setup_tts_and_voice_input(
        tts, tts_provider, tts_voice, tts_list_voices, voice_input, debug, console
    )

    # Validate chat history path
    history_file = context_processor.validate_chat_history_path(chat_history)

    # Show configuration if requested
    if show_config:
        display_configuration(
            ai_provider,
            light_model,
            model,
            fallback_models,
            max_context_size,
            reasoning_effort,
            reasoning_budget,
            ai_base_url,
            temperature,
            system_prompt,
            user_prompt,
            pricing,
            display_format,
            context_location,
            context_is_image,
            loop_mode,
            history_file,
            redis_host,
            redis_port,
            enable_redis,
            tts,
            tts_provider,
            tts_voice,
            voice_input,
            debug,
            yes_to_all,
            console,
        )

    # Create state object
    state = {
        "debug": debug,
        "ai_provider": ai_provider,
        "model": model,
        "fallback_models": fallback_models,
        "light_model": light_model,
        "ai_base_url": ai_base_url,
        "pricing": pricing,
        "is_sixel_supported": False,  # query_terminal_support(),
        "llm_config": llm_config,
        "store_url": os.environ.get("VECTOR_STORE_URL", "memory://"),
        "collection_name": "par_gpt",
        "temperature": temperature,
        "user_agent_appid": user_agent_appid,
        "display_format": display_format,
        "context_location": context_location,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "max_context_size": max_context_size,
        "reasoning_effort": reasoning_effort,
        "reasoning_budget": reasoning_budget,
        "copy_to_clipboard": copy_to_clipboard,
        "copy_from_clipboard": copy_from_clipboard,
        "show_config": show_config,
        "context": context,
        "context_is_image": context_is_image,
        "loop_mode": loop_mode,
        "history_file": history_file,
        "redis_host": redis_host,
        "redis_port": redis_port,
        "enable_redis": enable_redis,
        "tts": tts,
        "tts_provider": tts_provider,
        "tts_voice": tts_voice,
        "tts_man": tts_man,
        "voice_input_man": voice_input_man,
        "show_times": show_times,
        "show_times_detailed": show_times_detailed,
        "yes_to_all": yes_to_all,
    }

    ctx.obj = state


def display_configuration(
    ai_provider,
    light_model,
    model,
    fallback_models,
    max_context_size,
    reasoning_effort,
    reasoning_budget,
    ai_base_url,
    temperature,
    system_prompt,
    user_prompt,
    pricing,
    display_format,
    context_location,
    context_is_image,
    loop_mode,
    history_file,
    redis_host,
    redis_port,
    enable_redis,
    tts,
    tts_provider,
    tts_voice,
    voice_input,
    debug,
    yes_to_all,
    console: Console,
):
    """Display configuration panel."""
    Panel = lazy_import("rich.panel", "Panel")
    Text = lazy_import("rich.text", "Text")

    console.print(
        Panel.fit(
            Text.assemble(
                ("AI Provider: ", "cyan"),
                (f"{ai_provider.value}", "green"),
                "\n",
                ("Light Model: ", "cyan"),
                (f"{light_model}", "green"),
                "\n",
                ("Model: ", "cyan"),
                (f"{model}", "green"),
                "\n",
                ("Fallback Models: ", "cyan"),
                (f"{fallback_models}", "green"),
                "\n",
                ("Max Context Size: ", "cyan"),
                (f"{max_context_size}", "green"),
                "\n",
                ("Reasoning Effort: ", "cyan"),
                (f"{reasoning_effort}", "green"),
                "\n",
                ("Reasoning Budget: ", "cyan"),
                (f"{reasoning_budget}", "green"),
                "\n",
                ("AI Provider Base URL: ", "cyan"),
                "\n",
                (f"{ai_base_url or 'default'}", "green"),
                "\n",
                ("Temperature: ", "cyan"),
                (f"{temperature}", "green"),
                "\n",
                ("System Prompt: ", "cyan"),
                (f"{system_prompt or 'default'}", "green"),
                "\n",
                ("User Prompt: ", "cyan"),
                (f"{user_prompt or 'using stdin'}", "green"),
                "\n",
                ("Pricing: ", "cyan"),
                (f"{pricing}", "green"),
                "\n",
                ("Display Format: ", "cyan"),
                (f"{display_format or 'default'}", "green"),
                "\n",
                ("Context Location: ", "cyan"),
                (f"{context_location or 'default'}", "green"),
                "\n",
                ("Context Is Image: ", "cyan"),
                (f"{context_is_image}", "green"),
                "\n",
                ("Loop Mode: ", "cyan"),
                (f"{loop_mode}", "green"),
                "\n",
                ("Chat History: ", "cyan"),
                (f"{history_file or 'None'}", "green"),
                "\n",
                ("Redis Host: ", "cyan"),
                (f"{redis_host or 'default'}", "green"),
                "\n",
                ("Redis Port: ", "cyan"),
                (f"{redis_port or 'default'}", "green"),
                "\n",
                ("Redis Enabled: ", "cyan"),
                (f"{enable_redis}", "green"),
                "\n",
                ("TTS: ", "cyan"),
                (f"{tts}", "green"),
                "\n",
                ("TTS Provider: ", "cyan"),
                (f"{tts_provider}", "green"),
                "\n",
                ("TTS Voice: ", "cyan"),
                (f"{tts_voice or 'Default'}", "green"),
                "\n",
                ("Voice Input: ", "cyan"),
                (f"{voice_input}", "green"),
                "\n",
                ("Debug: ", "cyan"),
                (f"{debug}", "green"),
                "\n",
                ("Yes to All: ", "cyan"),
                (f"{yes_to_all}", "green"),
                "\n",
            ),
            title="[bold]GPT Configuration",
            border_style="bold",
        )
    )
