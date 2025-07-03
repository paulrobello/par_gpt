"""CLI option definitions for PAR GPT."""

from __future__ import annotations

from typing import Annotated

import typer
from par_ai_core.llm_config import ReasoningEffort
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.output_utils import DisplayOutputFormat
from par_ai_core.pricing_lookup import PricingDisplay
from strenum import StrEnum

from par_gpt import __env_var_prefix__
from par_gpt.tts_manager import TTSProvider


class LoopMode(StrEnum):
    """Loop mode options."""

    ONE_SHOT = "one_shot"
    INFINITE = "infinite"


def get_global_options() -> dict[str, tuple[type, typer.Option]]:
    """Get all global CLI options as a dictionary for reuse."""
    return {
        "ai_provider": (
            LlmProvider,
            typer.Option(
                "--ai-provider",
                "-a",
                envvar=f"{__env_var_prefix__}_AI_PROVIDER",
                help="AI provider to use for processing",
            ),
        ),
        "model": (
            str | None,
            typer.Option(
                "--model",
                "-m",
                envvar=f"{__env_var_prefix__}_MODEL",
                help="AI model to use for processing. If not specified, a default model will be used.",
            ),
        ),
        "fallback_models": (
            list[str] | None,
            typer.Option(
                "--fallback-models",
                "-B",
                envvar=f"{__env_var_prefix__}_FALLBACK_MODELS",
                help="Fallback models to use if the specified model is not available.",
            ),
        ),
        "light_model": (
            bool,
            typer.Option(
                "--light-model",
                "-l",
                envvar=f"{__env_var_prefix__}_LIGHT_MODEL",
                help="Use a light model for processing. If not specified, a default model will be used.",
            ),
        ),
        "ai_base_url": (
            str | None,
            typer.Option(
                "--ai-base-url",
                "-b",
                envvar=f"{__env_var_prefix__}_AI_BASE_URL",
                help="Override the base URL for the AI provider.",
            ),
        ),
        "temperature": (
            float,
            typer.Option(
                "--temperature",
                "-t",
                envvar=f"{__env_var_prefix__}_TEMPERATURE",
                help="Temperature to use for processing. If not specified, a default temperature will be used.",
            ),
        ),
        "user_agent_appid": (
            str | None,
            typer.Option(
                "--user-agent-appid",
                "-U",
                envvar=f"{__env_var_prefix__}_USER_AGENT_APPID",
                help="Extra data to include in the User-Agent header for the AI provider.",
            ),
        ),
        "pricing": (
            PricingDisplay,
            typer.Option(
                "--pricing",
                "-p",
                envvar=f"{__env_var_prefix__}_PRICING",
                help="Enable pricing summary display",
            ),
        ),
        "display_format": (
            DisplayOutputFormat,
            typer.Option(
                "--display-output",
                "-d",
                envvar=f"{__env_var_prefix__}_DISPLAY_OUTPUT",
                help="Display output in terminal (none, plain, md, csv, or json)",
            ),
        ),
        "context_location": (
            str,
            typer.Option(
                "--context-location",
                "-f",
                help="Location of context to use for processing.",
            ),
        ),
        "system_prompt": (
            str | None,
            typer.Option(
                "--system-prompt",
                "-s",
                help="System prompt to use for processing. If not specified, a default system prompt will be used.",
            ),
        ),
        "user_prompt": (
            str | None,
            typer.Option(
                "--user-prompt",
                "-u",
                help="User prompt to use for processing. If not specified, a default user prompt will be used.",
            ),
        ),
        "max_context_size": (
            int,
            typer.Option(
                "--max-context-size",
                "-M",
                envvar=f"{__env_var_prefix__}_MAX_CONTEXT_SIZE",
                help="Maximum context size when provider supports it. 0 = default. This must be set to more than reasoning_budget if reasoning_budget is set.",
            ),
        ),
        "reasoning_effort": (
            ReasoningEffort | None,
            typer.Option(
                "--reasoning-effort",
                envvar=f"{__env_var_prefix__}_REASONING_EFFORT",
                help="Reasoning effort level to use for o1 and o3 models.",
            ),
        ),
        "reasoning_budget": (
            int | None,
            typer.Option(
                "--reasoning-budget",
                envvar=f"{__env_var_prefix__}_REASONING_BUDGET",
                help="Maximum context size for reasoning.",
            ),
        ),
        "copy_to_clipboard": (
            bool,
            typer.Option(
                "--copy-to-clipboard",
                "-c",
                help="Copy output to clipboard",
            ),
        ),
        "copy_from_clipboard": (
            bool,
            typer.Option(
                "--copy-from-clipboard",
                "-C",
                help="Copy context or context location from clipboard",
            ),
        ),
        "debug": (
            bool,
            typer.Option(
                "--debug",
                "-D",
                envvar=f"{__env_var_prefix__}_DEBUG",
                help="Enable debug mode",
            ),
        ),
        "show_config": (
            bool,
            typer.Option(
                "--show-config",
                "-S",
                envvar=f"{__env_var_prefix__}_SHOW_CONFIG",
                help="Show config",
            ),
        ),
        "user": (
            str | None,
            typer.Option(
                "--user",
                "-P",
                envvar=f"{__env_var_prefix__}_USER",
                help="User to use for memory and preferences. Defaults to logged in users username.",
            ),
        ),
        "redis_host": (
            str | None,
            typer.Option(
                "--redis-host",
                "-r",
                envvar=f"{__env_var_prefix__}_REDIS_HOST",
                help="Host or ip of redis server. Used for memory functions.",
            ),
        ),
        "redis_port": (
            int | None,
            typer.Option(
                "--redis-port",
                "-R",
                envvar=f"{__env_var_prefix__}_REDIS_PORT",
                help="Redis port number. Used for memory functions.",
            ),
        ),
        "enable_redis": (
            bool,
            typer.Option(
                "--enable-redis",
                envvar=f"{__env_var_prefix__}_ENABLE_REDIS",
                help="Enable Redis memory functionality.",
            ),
        ),
        "tts": (
            bool,
            typer.Option(
                "--tts",
                "-T",
                envvar=f"{__env_var_prefix__}_TTS",
                help="Use TTS for LLM response.",
            ),
        ),
        "tts_provider": (
            TTSProvider | None,
            typer.Option(
                "--tts-provider",
                envvar=f"{__env_var_prefix__}_TTS_PROVIDER",
                help="Provider to use for TTS. Defaults to kokoro",
            ),
        ),
        "tts_voice": (
            str | None,
            typer.Option(
                "--tts-voice",
                envvar=f"{__env_var_prefix__}_TTS_VOICE",
                help="Voice to use for TTS. Depends on TTS provider chosen.",
            ),
        ),
        "tts_list_voices": (
            bool | None,
            typer.Option(
                "--tts-list-voices",
                help="List voices for selected TTS provider.",
            ),
        ),
        "voice_input": (
            bool,
            typer.Option(
                "--voice-input",
                help="Use voice input.",
            ),
        ),
        "chat_history": (
            str | None,
            typer.Option(
                "--chat-history",
                envvar=f"{__env_var_prefix__}_CHAT_HISTORY",
                help="Save and or resume chat history from file",
            ),
        ),
        "loop_mode": (
            LoopMode,
            typer.Option(
                "--loop-mode",
                "-L",
                envvar=f"{__env_var_prefix__}_LOOP_MODE",
                help="One shot or infinite mode",
            ),
        ),
        "show_times": (
            bool,
            typer.Option(
                "--show-times",
                envvar=f"{__env_var_prefix__}_SHOW_TIMES",
                help="Show timing information for various operations",
            ),
        ),
        "show_times_detailed": (
            bool,
            typer.Option(
                "--show-times-detailed",
                envvar=f"{__env_var_prefix__}_SHOW_TIMES_DETAILED",
                help="Show detailed timing information with hierarchical breakdown",
            ),
        ),
        "yes_to_all": (
            bool,
            typer.Option(
                "--yes-to-all",
                "-y",
                envvar=f"{__env_var_prefix__}_YES_TO_ALL",
                help="Automatically accept all security warnings and confirmation prompts",
            ),
        ),
    }


def get_agent_options() -> dict[str, tuple[type, typer.Option]]:
    """Get agent-specific CLI options."""
    return {
        "max_iterations": (
            int,
            typer.Option(
                "--max-iterations",
                "-i",
                envvar=f"{__env_var_prefix__}_MAX_ITERATIONS",
                help="Maximum number of iterations to run when in agent mode.",
            ),
        ),
        "show_tool_calls": (
            bool,
            typer.Option(
                "--show-tool-calls",
                "-T",
                envvar=f"{__env_var_prefix__}_SHOW_TOOL_CALLS",
                help="Show tool calls",
            ),
        ),
        "repl": (
            bool,
            typer.Option(
                "--repl",
                envvar=f"{__env_var_prefix__}_REPL",
                help="⚠️  DANGER: Enable REPL tool for code execution on HOST SYSTEM. This allows AI to write and execute arbitrary code with your user permissions. Only use if you understand the security risks.",
            ),
        ),
        "code_sandbox": (
            bool,
            typer.Option(
                "--code-sandbox",
                "-c",
                envvar=f"{__env_var_prefix__}_CODE_SANDBOX",
                help="Enable code sandbox tool. Requires a running code sandbox container.",
            ),
        ),
    }


# Default values for options
GLOBAL_OPTION_DEFAULTS = {
    "ai_provider": LlmProvider.OPENAI,
    "model": None,
    "fallback_models": None,
    "light_model": False,
    "ai_base_url": None,
    "temperature": 0.5,
    "user_agent_appid": None,
    "pricing": PricingDisplay.NONE,
    "display_format": DisplayOutputFormat.MD,
    "context_location": "",
    "system_prompt": None,
    "user_prompt": None,
    "max_context_size": 0,
    "reasoning_effort": None,
    "reasoning_budget": None,
    "copy_to_clipboard": False,
    "copy_from_clipboard": False,
    "debug": False,
    "show_config": False,
    "user": None,
    "redis_host": "localhost",
    "redis_port": 6379,
    "enable_redis": False,
    "tts": False,
    "tts_provider": None,
    "tts_voice": None,
    "tts_list_voices": None,
    "voice_input": False,
    "chat_history": None,
    "loop_mode": LoopMode.ONE_SHOT,
    "show_times": False,
    "show_times_detailed": False,
    "yes_to_all": False,
}

AGENT_OPTION_DEFAULTS = {
    "max_iterations": 5,
    "show_tool_calls": False,
    "repl": False,
    "code_sandbox": False,
}