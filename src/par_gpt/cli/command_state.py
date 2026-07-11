"""Typed command state shared between the CLI callback and command implementations.

Replaces the previous untyped ``dict[str, Any]`` that was attached to
``typer.Context.obj``. Centralizing the shape here gives pyright full
visibility into access sites and prevents typos in key names.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from par_ai_core.llm_config import LlmConfig, ReasoningEffort
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.output_utils import DisplayOutputFormat
from par_ai_core.pricing_lookup import PricingDisplay

from par_gpt.cli.options import LoopMode


@dataclass(frozen=True)
class CommandState:
    """Immutable bundle of resolved global options for a single command invocation.

    Constructed once in the main Typer callback (:func:`par_gpt.cli.app.main`)
    and attached to ``ctx.obj``. Every command reads its configuration from this
    object via attribute access. Fields map 1:1 to the CLI global options; their
    types are taken from the callback parameter annotations and the values
    assigned during startup processing.

    Attributes:
        debug: Enable verbose/debug output.
        ai_provider: Selected AI provider.
        model: Resolved model name (``None`` if the user did not pass one and the
            command is not an LLM command).
        fallback_models: Optional fallback model list.
        light_model: Prefer a light/cheap model.
        ai_base_url: Override base URL for the provider, if any.
        pricing: Pricing display preference.
        is_sixel_supported: Whether the terminal advertises sixel support.
        llm_config: Fully built LLM configuration. ``None`` for non-LLM commands.
        store_url: Vector store URL.
        collection_name: Vector store collection name.
        temperature: Sampling temperature.
        user_agent_appid: Extra user-agent app id, if any.
        display_format: Terminal output format.
        context_location: Raw context location argument.
        system_prompt: Override system prompt, if any.
        user_prompt: Override user prompt, if any.
        max_context_size: Maximum context size (0 = provider default).
        reasoning_effort: Reasoning effort level, if applicable.
        reasoning_budget: Reasoning token budget, if any.
        copy_to_clipboard: Copy LLM output to clipboard.
        copy_from_clipboard: Read context from the clipboard.
        show_config: Print resolved configuration and exit.
        context: Processed context string (``None`` for non-LLM commands).
        context_is_image: Whether ``context`` refers to image input.
        loop_mode: One-shot vs. infinite interaction loop.
        history_file: Chat history file path, if configured.
        redis_host: Redis host (memory functions).
        redis_port: Redis port (memory functions).
        enable_redis: Enable Redis-backed memory.
        show_times: Print a timing summary at the end of the run.
        show_times_detailed: Print a detailed hierarchical timing summary.
        yes_to_all: Auto-accept all security/confirmation prompts.
        show_tool_calls: Explicit toggle for tool-call logging in the provider
            callback. ``None`` means fall back to ``debug`` (preserves the
            previous ``state.get("show_tool_calls", state["debug"])`` behavior).
    """

    debug: bool
    ai_provider: LlmProvider
    model: str | None
    fallback_models: list[str] | None
    light_model: bool
    ai_base_url: str | None
    pricing: PricingDisplay
    is_sixel_supported: bool
    llm_config: LlmConfig | None
    store_url: str
    collection_name: str
    temperature: float
    user_agent_appid: str | None
    display_format: DisplayOutputFormat
    context_location: str
    system_prompt: str | None
    user_prompt: str | None
    max_context_size: int
    reasoning_effort: ReasoningEffort | None
    reasoning_budget: int | None
    copy_to_clipboard: bool
    copy_from_clipboard: bool
    show_config: bool
    context: str | None
    context_is_image: bool
    loop_mode: LoopMode
    history_file: Path | None
    redis_host: str | None
    redis_port: int | None
    enable_redis: bool
    show_times: bool
    show_times_detailed: bool
    yes_to_all: bool
    show_tool_calls: bool | None = None
