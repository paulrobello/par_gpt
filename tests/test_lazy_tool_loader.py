"""Routing tests for the lazy AI-tool loader's declarative skill registry.

These tests exercise the on-demand tool selection in
``src/par_gpt/lazy_tool_loader.py`` (ARC-006 surface) without invoking any LLM.
They assert the skill-registry contract:

    * ``build_ai_tool_list`` returns the documented ``tuple[list, dict]``;
    * the always-on core tools are present regardless of the question;
    * the ``SKILLS`` registry is well-formed (lowercased keywords, known skills);
    * skill keyword triggers load the right tools, and the BROADENED recall
      keywords (push/pull request for git, snap for capture, ascii art for
      figlet, monitor for screen) fire as intended;
    * credential-gated skills (weather/image_gen/github) are skipped without
      their key and loaded with it (the on-demand "skills" model is preserved:
      nothing keyword-gated becomes always-on);
    * YouTube's split credential (transcript always, search needs GOOGLE_API_KEY);
    * a question with no skill keywords loads ONLY the core set (lean/on-demand).

To keep routing deterministic regardless of the host environment, the
provider/search/weather/github env vars are cleared via an autouse fixture.
The REPL path (``repl=True``) is intentionally avoided so no heavy modules are
imported; the routing concern is the skill branches, which are repl-independent.
"""

from __future__ import annotations

import pytest

from par_gpt.lazy_tool_loader import SKILLS, LazyToolLoader, Skill, build_ai_tool_list

# Env vars that gate provider-specific tool registration in get_conditional_tools
# and the skill credential predicates.
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
# Declarative SKILLS registry structure
# ---------------------------------------------------------------------------


def test_skills_registry_is_well_formed() -> None:
    """SKILLS is a tuple of Skill with lowercased keywords and known members."""
    assert isinstance(SKILLS, tuple)
    assert all(isinstance(s, Skill) for s in SKILLS)

    names = {s.name for s in SKILLS}
    expected = {
        "figlet",
        "youtube",
        "git",
        "clipboard",
        "rss",
        "hackernews",
        "window",
        "screen",
        "capture",
        "image_gen",
        "weather",
        "github",
    }
    assert names == expected

    for skill in SKILLS:
        # Substring matching is done against a lowercased question, so every
        # keyword must itself be lowercased to match.
        assert all(kw == kw.lower() for kw in skill.keywords), f"{skill.name} has non-lowercase keyword"
        # Every skill must resolve tools somehow: either a named tuple or a loader.
        assert skill.tools or skill.loader is not None, f"{skill.name} has no tools and no loader"


# ---------------------------------------------------------------------------
# Skill-triggered routing (positive)
# ---------------------------------------------------------------------------


def test_git_skill_loads_on_git_keyword() -> None:
    """The original 'git commit' phrasing still routes to git_commit_tool."""
    tools, _ = build_ai_tool_list("please git commit my staged changes")

    assert "git_commit_tool" in _tool_names(tools)


def test_broadened_recall_push_loads_git() -> None:
    """Broadened recall: the bare 'push' keyword now loads git_commit_tool.

    'push these changes to the remote' contains no old keyword
    (git/commit/checkout), so this proves the new 'push' trigger in isolation.
    """
    tools, _ = build_ai_tool_list("push these changes to the remote")

    assert "git_commit_tool" in _tool_names(tools)


def test_broadened_recall_pull_request_loads_git() -> None:
    """Broadened recall: 'pull request' loads git_commit_tool."""
    tools, _ = build_ai_tool_list("open a pull request for this branch")

    assert "git_commit_tool" in _tool_names(tools)


def test_figlet_skill_loads_on_figlet() -> None:
    """The 'figlet' keyword loads ai_figlet."""
    tools, _ = build_ai_tool_list("make a figlet banner that says HI")

    assert "ai_figlet" in _tool_names(tools)


def test_broadened_recall_ascii_art_loads_figlet() -> None:
    """Broadened recall: 'ascii art' synonym loads ai_figlet."""
    tools, _ = build_ai_tool_list("render some ascii art that says HI")

    assert "ai_figlet" in _tool_names(tools)


def test_capture_skill_loads_on_screenshot() -> None:
    """The 'screenshot' keyword loads both capture tools."""
    tools, _ = build_ai_tool_list("take a screenshot of my screen")

    names = _tool_names(tools)
    assert "ai_capture_screen_image" in names
    assert "ai_capture_window_image" in names


def test_broadened_recall_snap_loads_capture() -> None:
    """Broadened recall: 'snap a screenshot' loads capture tools."""
    tools, _ = build_ai_tool_list("snap a screenshot")

    names = _tool_names(tools)
    assert "ai_capture_screen_image" in names
    assert "ai_capture_window_image" in names


def test_window_skill_loads_on_window() -> None:
    """The 'window' keyword loads the visible-windows lister."""
    tools, _ = build_ai_tool_list("show me every window on screen")

    assert "ai_list_visible_windows" in _tool_names(tools)


def test_broadened_recall_monitor_loads_screen() -> None:
    """Broadened recall: 'monitor' synonym loads the screen lister."""
    tools, _ = build_ai_tool_list("list my monitors")

    assert "ai_list_available_screens" in _tool_names(tools)


def test_hackernews_two_word_trigger() -> None:
    """Broadened recall: 'hacker news' (two words) loads the hackernews tool."""
    tools, _ = build_ai_tool_list("show me the top hacker news stories")

    assert "ai_fetch_hacker_news" in _tool_names(tools)


# ---------------------------------------------------------------------------
# Skill-triggered routing (negative / no false load)
# ---------------------------------------------------------------------------


def test_unrelated_question_does_not_load_git_tool() -> None:
    """A question without git keywords must not load the git tool."""
    tools, _ = build_ai_tool_list("tell me a joke about cats")

    assert "git_commit_tool" not in _tool_names(tools)


def test_no_skill_keyword_loads_only_core_set() -> None:
    """On-demand/lean: a question with no skill keyword and no provider key
    loads ONLY the always-on core tools (nothing keyword-gated is always-on)."""
    tools, _ = build_ai_tool_list("what is the capital of france")

    assert _tool_names(tools) == {
        "user_prompt",
        "ai_open_url",
        "ai_fetch_url",
        "ai_display_image_in_terminal",
    }


# ---------------------------------------------------------------------------
# Credential-gated skills (on-demand model preserved)
# ---------------------------------------------------------------------------


def test_weather_skill_skipped_without_key() -> None:
    """weather keyword matches but the skill is skipped when WEATHERAPI_KEY is unset."""
    tools, _ = build_ai_tool_list("what is the weather forecast for tomorrow")

    names = _tool_names(tools)
    assert "ai_get_weather_current" not in names
    assert "ai_get_weather_forecast" not in names


def test_weather_skill_loaded_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With WEATHERAPI_KEY set, the weather keyword loads both weather tools."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key")
    tools, _ = build_ai_tool_list("what is the weather forecast for tomorrow")

    names = _tool_names(tools)
    assert "ai_get_weather_current" in names
    assert "ai_get_weather_forecast" in names


def test_image_gen_skill_skipped_without_provider_key() -> None:
    """image keyword matches but the skill is skipped without OPENAI/OPENROUTER key."""
    tools, _ = build_ai_tool_list("generate an image of a cat")

    assert "ai_image_gen_dali" not in _tool_names(tools)


def test_image_gen_skill_loaded_with_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With OPENAI_API_KEY set, the image keyword loads the image-gen tool."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    tools, _ = build_ai_tool_list("generate an image of a cat")

    assert "ai_image_gen_dali" in _tool_names(tools)


def test_github_skill_skipped_without_pat() -> None:
    """github keyword matches but the skill is skipped without GITHUB_PERSONAL_ACCESS_TOKEN."""
    tools, _ = build_ai_tool_list("list my github repos")

    names = _tool_names(tools)
    assert "ai_github_list_repos" not in names
    assert "ai_github_create_repo" not in names
    assert "ai_github_publish_repo" not in names


def test_github_skill_loaded_with_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    """With GITHUB_PERSONAL_ACCESS_TOKEN set, the github keyword loads all 3 tools."""
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "test-pat")
    tools, _ = build_ai_tool_list("list my github repos")

    names = _tool_names(tools)
    assert "ai_github_list_repos" in names
    assert "ai_github_create_repo" in names
    assert "ai_github_publish_repo" in names


# ---------------------------------------------------------------------------
# YouTube split-credential skill (loader overrides tools tuple)
# ---------------------------------------------------------------------------


def test_youtube_transcript_loaded_without_google_key() -> None:
    """The 'youtube' keyword always loads the transcript tool (no key needed)."""
    tools, _ = build_ai_tool_list("get the youtube transcript for this video")

    names = _tool_names(tools)
    assert "ai_youtube_get_transcript" in names
    assert "ai_youtube_search" not in names


def test_youtube_search_loaded_with_google_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With GOOGLE_API_KEY set, the youtube keyword also loads the search tool."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    tools, _ = build_ai_tool_list("search youtube for cats")

    names = _tool_names(tools)
    assert "ai_youtube_get_transcript" in names
    assert "ai_youtube_search" in names


# ---------------------------------------------------------------------------
# Flag-gated tools (kept explicit, not in the registry)
# ---------------------------------------------------------------------------


def test_code_sandbox_loads_execute_code() -> None:
    """code_sandbox=True (without repl) registers the sandboxed execute_code tool."""
    tools, _ = build_ai_tool_list("run some code", repl=False, code_sandbox=True)

    assert "execute_code" in _tool_names(tools)


def test_repl_mutually_exclusive_with_code_sandbox() -> None:
    """When repl is enabled, the sandbox tool is not also added (repl wins)."""
    tools, _ = build_ai_tool_list("run some code", repl=True, code_sandbox=True, yes_to_all=False)

    names = _tool_names(tools)
    assert "execute_code" not in names  # repl takes precedence
    assert isinstance(tools, list)


def test_local_modules_populated_only_for_repl() -> None:
    """local_modules is non-empty only when the REPL path runs; empty otherwise."""
    _, no_modules = build_ai_tool_list("a plain question", repl=False)
    assert no_modules == {}
