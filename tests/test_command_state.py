"""Contract tests for the typed CommandState that replaced the untyped ctx.obj dict.

Pins the field set, precise types, attribute access, and immutability (frozen).
If any of these change, this test fails before the change reaches the command path.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from par_ai_core.llm_config import LlmConfig, ReasoningEffort
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.output_utils import DisplayOutputFormat
from par_ai_core.pricing_lookup import PricingDisplay

from par_gpt.cli.command_state import CommandState
from par_gpt.cli.options import LoopMode


def _build_state(**overrides: object) -> CommandState:
    """Build a CommandState with representative defaults; callers override fields."""
    defaults: dict[str, object] = {
        "debug": True,
        "ai_provider": LlmProvider.OPENAI,
        "model": "gpt-4o",
        "fallback_models": ["gpt-4o-mini"],
        "light_model": False,
        "ai_base_url": None,
        "pricing": PricingDisplay.PRICE,
        "is_sixel_supported": False,
        "llm_config": LlmConfig(provider=LlmProvider.OPENAI, model_name="gpt-4o"),
        "store_url": "memory://",
        "collection_name": "par_gpt",
        "temperature": 0.5,
        "user_agent_appid": None,
        "display_format": DisplayOutputFormat.MD,
        "context_location": "",
        "system_prompt": None,
        "user_prompt": None,
        "max_context_size": 0,
        "reasoning_effort": ReasoningEffort.MEDIUM,
        "reasoning_budget": None,
        "copy_to_clipboard": False,
        "copy_from_clipboard": False,
        "show_config": False,
        "context": None,
        "context_is_image": False,
        "loop_mode": LoopMode.ONE_SHOT,
        "history_file": Path("/tmp/par_gpt_history.json"),
        "redis_host": "localhost",
        "redis_port": 6379,
        "enable_redis": False,
        "show_times": False,
        "show_times_detailed": False,
        "yes_to_all": False,
    }
    defaults.update(overrides)
    return CommandState(**defaults)  # type: ignore[arg-type]


def test_attribute_access_returns_constructed_values() -> None:
    """Each field round-trips through attribute access with the value supplied."""
    state = _build_state(
        model="claude-3-5-sonnet",
        temperature=0.1,
        display_format=DisplayOutputFormat.JSON,
        loop_mode=LoopMode.INFINITE,
        history_file=Path("/tmp/h.json"),
    )

    assert state.model == "claude-3-5-sonnet"
    assert state.temperature == 0.1
    assert state.display_format is DisplayOutputFormat.JSON
    assert state.loop_mode is LoopMode.INFINITE
    assert state.history_file == Path("/tmp/h.json")
    assert state.is_sixel_supported is False
    assert state.collection_name == "par_gpt"


def test_optional_fields_accept_none() -> None:
    """Optional fields (None-able) accept None and expose it via attribute access."""
    state = _build_state(
        model=None,
        fallback_models=None,
        ai_base_url=None,
        user_agent_appid=None,
        system_prompt=None,
        user_prompt=None,
        reasoning_effort=None,
        reasoning_budget=None,
        context=None,
        history_file=None,
        llm_config=None,
    )

    assert state.model is None
    assert state.fallback_models is None
    assert state.ai_base_url is None
    assert state.llm_config is None
    assert state.history_file is None
    assert state.reasoning_effort is None


def test_enum_fields_have_correct_types() -> None:
    """Enum-typed fields hold members of the expected enum classes."""
    state = _build_state()

    assert isinstance(state.ai_provider, LlmProvider)
    assert isinstance(state.pricing, PricingDisplay)
    assert isinstance(state.display_format, DisplayOutputFormat)
    assert isinstance(state.loop_mode, LoopMode)
    assert isinstance(state.reasoning_effort, ReasoningEffort)


def test_show_tool_calls_defaults_to_none() -> None:
    """The 35th field is opt-in: unset means None, preserving the debug-fallback path."""
    state = _build_state()
    assert state.show_tool_calls is None

    explicit = _build_state(show_tool_calls=True)
    assert explicit.show_tool_calls is True


def test_show_tool_calls_debug_fallback_expression_matches_old_behavior() -> None:
    """Replicates base.get_provider_callback's fallback-to-debug semantics."""
    unset = _build_state(debug=True)
    effective = unset.show_tool_calls if unset.show_tool_calls is not None else unset.debug
    assert effective is True

    overridden = _build_state(debug=True, show_tool_calls=False)
    effective = overridden.show_tool_calls if overridden.show_tool_calls is not None else overridden.debug
    assert effective is False


def test_state_is_frozen() -> None:
    """CommandState is a frozen dataclass: assignment must raise FrozenInstanceError."""
    state = _build_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.debug = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.user_prompt = "mutated"  # type: ignore[misc]


def test_expected_field_set_is_present() -> None:
    """Guard against accidental field removal/renaming during the refactor."""
    expected = {
        "debug", "ai_provider", "model", "fallback_models", "light_model",
        "ai_base_url", "pricing", "is_sixel_supported", "llm_config", "store_url",
        "collection_name", "temperature", "user_agent_appid", "display_format",
        "context_location", "system_prompt", "user_prompt", "max_context_size",
        "reasoning_effort", "reasoning_budget", "copy_to_clipboard", "copy_from_clipboard",
        "show_config", "context", "context_is_image", "loop_mode", "history_file",
        "redis_host", "redis_port", "enable_redis", "show_times", "show_times_detailed",
        "yes_to_all", "show_tool_calls",
    }
    actual = {f.name for f in dataclasses.fields(CommandState)}
    assert actual == expected
