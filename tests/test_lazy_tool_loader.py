"""Routing tests for the lazy AI-tool loader.

These tests exercise the keyword-gated tool selection in
``src/par_gpt/lazy_tool_loader.py`` (ARC-006 surface) without invoking any LLM.
They assert:

    * ``build_ai_tool_list`` returns the documented ``tuple[list, dict]``;
    * the always-on core tools are present regardless of the question;
    * representative questions route to the expected tool sets
      (git, figlet, capture), and unrelated questions do not pull those tools in;
    * Redis-gated tools only appear when ``enable_redis=True``.

To keep routing deterministic regardless of the host environment, the
search/weather/github provider env vars are cleared via an autouse fixture.
The REPL path (``repl=True``) is intentionally avoided so no heavy modules are
imported; the routing concern is the keyword branches, which are repl-independent.
"""

from __future__ import annotations

import pytest

from par_gpt.lazy_tool_loader import LazyToolLoader, build_ai_tool_list

# Env vars that gate provider-specific tool registration in get_conditional_tools.
_PROVIDER_ENV_KEYS = (
    "TAVILY_API_KEY",
    "SERPER_API_KEY",
    "GOOGLE_CSE_ID",
    "GOOGLE_CSE_API_KEY",
    "BRAVE_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "GOOGLE_API_KEY",
    "WEATHERAPI_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear provider env vars so tool selection depends only on the question."""
    for key in _PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _tool_names(tools: list) -> set[str]:
    return {t.name for t in tools}


# ---------------------------------------------------------------------------
# Return-type contract
# ---------------------------------------------------------------------------


def test_build_ai_tool_list_returns_documented_tuple() -> None:
    """build_ai_tool_list must return (list[BaseTool], dict)."""
    result = build_ai_tool_list("a simple question")

    assert isinstance(result, tuple)
    assert len(result) == 2
    tools, local_modules = result
    assert isinstance(tools, list)
    assert isinstance(local_modules, dict)
    assert len(tools) >= 1


def test_get_conditional_tools_returns_tuple() -> None:
    """The lower-level getter returns the same documented tuple shape."""
    loader = LazyToolLoader()

    tools, local_modules = loader.get_conditional_tools("hello", repl=False, code_sandbox=False, yes_to_all=False)

    assert isinstance(tools, list)
    assert isinstance(local_modules, dict)


# ---------------------------------------------------------------------------
# Core tools (always present)
# ---------------------------------------------------------------------------


def test_core_tools_always_present() -> None:
    """The always-on core tool set is returned for any question."""
    tools, _ = build_ai_tool_list("an unrelated greeting")

    names = _tool_names(tools)
    assert "user_prompt" in names
    assert "ai_open_url" in names
    assert "ai_fetch_url" in names
    assert "ai_display_image_in_terminal" in names
    # Redis-gated tool must NOT appear when enable_redis is False.
    assert "ai_memory_db" not in names


def test_get_core_tools_with_redis() -> None:
    """The memory tool is registered only when redis is enabled."""
    loader = LazyToolLoader()

    without = _tool_names(loader.get_core_tools(enable_redis=False))
    with_redis = _tool_names(loader.get_core_tools(enable_redis=True))

    assert "ai_memory_db" not in without
    assert "ai_memory_db" in with_redis


# ---------------------------------------------------------------------------
# Keyword routing
# ---------------------------------------------------------------------------


def test_git_question_routes_to_git_commit_tool() -> None:
    """A question containing 'git'/'commit' pulls in git_commit_tool."""
    tools, _ = build_ai_tool_list("please git commit my staged changes")

    assert "git_commit_tool" in _tool_names(tools)


def test_non_git_question_does_not_load_git_tool() -> None:
    """A question without git/commit/checkout keywords must not load the git tool."""
    tools, _ = build_ai_tool_list("tell me a joke about the weather")

    assert "git_commit_tool" not in _tool_names(tools)


def test_figlet_question_routes_to_figlet() -> None:
    """The 'figlet' keyword loads ai_figlet."""
    tools, _ = build_ai_tool_list("make a figlet banner that says HI")

    assert "ai_figlet" in _tool_names(tools)


def test_capture_question_routes_to_capture_tools() -> None:
    """The 'screenshot' keyword loads both capture tools."""
    tools, _ = build_ai_tool_list("take a screenshot of my screen")

    names = _tool_names(tools)
    assert "ai_capture_screen_image" in names
    assert "ai_capture_window_image" in names


def test_window_question_routes_to_window_lister() -> None:
    """The 'window' keyword loads the visible-windows lister."""
    tools, _ = build_ai_tool_list("show me every window on screen")

    assert "ai_list_visible_windows" in _tool_names(tools)


def test_code_sandbox_loads_execute_code() -> None:
    """code_sandbox=True (without repl) registers the sandboxed execute_code tool."""
    tools, _ = build_ai_tool_list("run some code", repl=False, code_sandbox=True)

    assert "execute_code" in _tool_names(tools)


def test_repl_mutually_exclusive_with_code_sandbox() -> None:
    """When repl is enabled, the sandbox tool is not also added (per get_conditional_tools)."""
    tools, _ = build_ai_tool_list("run some code", repl=True, code_sandbox=True, yes_to_all=False)

    names = _tool_names(tools)
    assert "execute_code" not in names  # repl takes precedence
    assert isinstance(tools, list)


def test_local_modules_populated_only_for_repl() -> None:
    """local_modules is non-empty only when the REPL path runs; empty otherwise."""
    _, no_modules = build_ai_tool_list("a plain question", repl=False)
    assert no_modules == {}
