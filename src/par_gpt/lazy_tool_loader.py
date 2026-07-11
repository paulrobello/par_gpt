"""Lazy loading system for AI tools to improve startup performance."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from langchain_core.tools import BaseTool

# ---------------------------------------------------------------------------
# Declarative skill registry (ARC-006)
#
# Tools load ON DEMAND, triggered by the question, to keep every invocation
# lightweight (progressive disclosure, like Claude Code's skills). This table
# replaces the old keyword ``if``-chain. Each Skill maps trigger phrases to the
# tools it loads, optionally gated by a credential predicate.
#
# Keyword choices favor precision over recall where the two conflict: bare
# words that match common English are omitted (e.g. "repo" matches "report";
# "copy"/"paste"/"clip" match "copyright"/"toothpaste"/"eclipse") in favor of
# intent phrases. False positives are cheap (one extra *available* tool that the
# model may simply not call), but the stated goal is to minimize them, so
# synonyms are added only where they carry real intent signal.
#
# Flag-gated tools (--repl, --code-sandbox), the credential-only search-provider
# cascade, and the credential-only image_search/reddit extras stay EXPLICIT in
# get_conditional_tools: those are "pick the configured backend" / "the user
# selected a mode", not keyword skills, and forcing them into the table would
# hurt readability more than it would help.
# ---------------------------------------------------------------------------


def _has_openai_or_openrouter() -> bool:
    """True when an image-generation-capable provider key is configured.

    Imported lazily so it never runs at startup; only evaluated when the
    image_gen skill's keyword already matched (see Skill.matches).
    """
    from par_ai_core.llm_providers import LlmProvider, is_provider_api_key_set

    return is_provider_api_key_set(LlmProvider.OPENAI) or is_provider_api_key_set(LlmProvider.OPENROUTER)


def _has_weather_key() -> bool:
    return bool(os.environ.get("WEATHERAPI_KEY"))


def _has_github_pat() -> bool:
    return bool(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"))


def _youtube_loader(loader: LazyToolLoader) -> list[BaseTool]:
    """YouTube is a split-credential skill: transcript always loads on
    "youtube"; search only loads when GOOGLE_API_KEY is set. Modeled as a
    custom loader (not a flat tool list + credential gate) because the
    credential split is INTRA-skill, not a simple on/off gate.
    """
    tools: list[BaseTool] = []
    if os.environ.get("GOOGLE_API_KEY"):
        tools.append(loader._import_tool("ai_youtube_search"))
    tools.append(loader._import_tool("ai_youtube_get_transcript"))
    return tools


@dataclass(frozen=True)
class Skill:
    """One on-demand tool group: trigger phrases + tools + optional credential gate.

    See SKILLS for the registry; matches()/load() drive the loop in
    get_conditional_tools. ``loader`` (when set) overrides ``tools`` for the
    irregular split-credential cases.
    """

    name: str
    keywords: tuple[str, ...]
    tools: tuple[str, ...] = ()
    credential: Callable[[], bool] | None = None
    loader: Callable[[LazyToolLoader], list[BaseTool]] | None = None

    def matches(self, question_lower: str) -> bool:
        """Keyword substring match AND credential gate (if any).

        Keyword is checked first: it is a cheap substring test and short-
        circuits the credential check (which may trigger an import), so a
        question that does not mention the skill never pays for it.
        """
        if not any(kw in question_lower for kw in self.keywords):
            return False
        return self.credential is None or self.credential()

    def load(self, loader: LazyToolLoader) -> list[BaseTool]:
        """Resolve the skill's tools: custom loader for irregular cases, else
        import each named tool through the loader."""
        if self.loader is not None:
            return self.loader(loader)
        return [loader._import_tool(name) for name in self.tools]


SKILLS: tuple[Skill, ...] = (
    Skill(
        name="figlet",
        keywords=("figlet", "ascii art", "ascii banner", "banner text"),
        tools=("ai_figlet",),
    ),
    Skill(
        name="youtube",
        keywords=("youtube",),
        loader=_youtube_loader,
    ),
    Skill(
        name="git",
        keywords=(
            "git",
            "commit",
            "push",
            "pull",
            "branch",
            "merge",
            "rebase",
            "stash",
            "diff",
            "checkout",
            "clone",
            "pull request",
            "repository",
        ),
        tools=("git_commit_tool",),
    ),
    Skill(
        name="clipboard",
        keywords=("clipboard", "copy and paste", "copy/paste", "paste text", "copy text"),
        tools=("ai_copy_to_clipboard", "ai_copy_from_clipboard"),
    ),
    Skill(
        name="rss",
        keywords=("rss", "rss feed", "atom feed", "feed url"),
        tools=("ai_fetch_rss",),
    ),
    Skill(
        name="hackernews",
        keywords=("hackernews", "hacker news"),
        tools=("ai_fetch_hacker_news",),
    ),
    Skill(
        name="window",
        keywords=("window",),
        tools=("ai_list_visible_windows",),
    ),
    Skill(
        name="screen",
        keywords=("screen", "display", "monitor"),
        tools=("ai_list_available_screens",),
    ),
    Skill(
        name="capture",
        keywords=("capture", "screenshot", "snap", "record screen", "grab screen"),
        tools=("ai_capture_window_image", "ai_capture_screen_image"),
    ),
    Skill(
        name="image_gen",
        keywords=("image", "dalle", "dall-e", "generate image", "create image", "generate a picture"),
        tools=("ai_image_gen_dali",),
        credential=_has_openai_or_openrouter,
    ),
    Skill(
        name="weather",
        keywords=("weather", "forecast", "temperature", " wx "),
        tools=("ai_get_weather_current", "ai_get_weather_forecast"),
        credential=_has_weather_key,
    ),
    Skill(
        name="github",
        keywords=("github", "github.com", "git hub", "gh repo", "create a repo", "publish a repo"),
        tools=("ai_github_list_repos", "ai_github_create_repo", "ai_github_publish_repo"),
        credential=_has_github_pat,
    ),
)


class LazyToolLoader:
    """Lazy loader for AI tools to reduce startup time."""

    def __init__(self) -> None:
        """Initialize the lazy tool loader."""
        self._tool_cache: dict[str, BaseTool | list[BaseTool]] = {}
        self._module_cache: dict[str, Any] = {}

    def _import_tool(self, tool_name: str) -> BaseTool:
        """Import a specific tool lazily."""
        if tool_name in self._tool_cache:
            cached_tool = self._tool_cache[tool_name]
            if isinstance(cached_tool, list):
                # This shouldn't happen for single tools, but handle gracefully
                raise ValueError(f"Expected single tool for {tool_name}, got list")
            return cached_tool

        # Import from ai_tools.ai_tools module
        if "ai_tools.ai_tools" not in self._module_cache:
            from par_gpt.ai_tools import ai_tools

            self._module_cache["ai_tools.ai_tools"] = ai_tools

        ai_tools_module = self._module_cache["ai_tools.ai_tools"]
        tool = getattr(ai_tools_module, tool_name)
        # Type cast to ensure tool is BaseTool for cache
        base_tool = cast(BaseTool, tool)
        self._tool_cache[tool_name] = base_tool
        return base_tool

    def _import_repl_tool(self, **kwargs) -> BaseTool:
        """Import REPL tool lazily."""
        cache_key = "repl_tool"
        if cache_key in self._tool_cache:
            cached_tool = self._tool_cache[cache_key]
            if isinstance(cached_tool, list):
                # This shouldn't happen for single tools, but handle gracefully
                raise ValueError(f"Expected single tool for {cache_key}, got list")
            return cached_tool

        from par_gpt.ai_tools.par_python_repl import ParPythonAstREPLTool

        # Import modules for REPL
        module_names = [
            "re",
            "json",
            "time",
            "datetime",
            "random",
            "string",
            "pathlib",
            "requests",
            "git",
            "pandas",
            "faker",
            "numpy",
            "matplotlib",
            "bs4",
            "html2text",
            "pydantic",
            "clipman",
            "pyfiglet",
            "rich",
            "rich.panel",
            "rich.markdown",
            "rich.pretty",
            "rich.table",
            "rich.text",
            "rich.color",
        ]
        local_modules = {module_name: importlib.import_module(module_name) for module_name in module_names}

        yes_to_all = kwargs.get("yes_to_all", False)
        # Security: never skip the host REPL confirmation, even under --yes-to-all.
        # Host exec() of AI-generated code is irreversible and reachable via prompt
        # injection (fetched URLs/search results). Use --code-sandbox for automated runs.
        if yes_to_all:
            from par_ai_core.par_logging import console_err

            console_err.print(
                "[bold yellow]Security:[/] --yes-to-all is not applied to the host Python REPL "
                "(--repl); execution confirmation stays enabled. Use --code-sandbox for "
                "unsupervised code execution.",
            )
        tool = ParPythonAstREPLTool(
            prompt_before_exec=True,
            show_exec_code=True,
            locals=local_modules,
        )
        self._tool_cache[cache_key] = tool
        return tool

    def _import_tavily_tools(self) -> list[BaseTool]:
        """Import Tavily search tools lazily."""
        cache_key = "tavily_tools"
        if cache_key in self._tool_cache:
            cached_tools = self._tool_cache[cache_key]
            if isinstance(cached_tools, list):
                return cached_tools
            else:
                # This shouldn't happen, but handle gracefully
                raise ValueError(f"Expected tool list for {cache_key}, got single tool")

        import warnings

        from langchain_community.tools import TavilySearchResults

        # Suppress deprecation warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            try:
                from langchain_core._api import LangChainDeprecationWarning

                warnings.simplefilter("ignore", LangChainDeprecationWarning)
            except ImportError:
                pass

            tools = [
                TavilySearchResults(
                    max_results=3,
                    include_answer=True,
                    topic="news",  # type: ignore
                    name="tavily_news_results_json",
                    description="Search news and current events",
                ),
                TavilySearchResults(
                    max_results=3,
                    include_answer=True,
                    name="tavily_search_results_json",
                    description="General search for content not directly related to current events",
                ),
            ]

        # Type cast for the cache
        tools_as_base = cast(list[BaseTool], tools)
        self._tool_cache[cache_key] = tools_as_base
        return tools_as_base

    def get_core_tools(self, *, enable_redis: bool = False) -> list[BaseTool]:
        """Get core tools that are always available."""
        core_tools = [
            self._import_tool("user_prompt"),
            self._import_tool("ai_open_url"),
            self._import_tool("ai_fetch_url"),
            self._import_tool("ai_display_image_in_terminal"),
        ]

        # Only add memory tool if Redis is enabled
        if enable_redis:
            core_tools.append(self._import_tool("ai_memory_db"))

        return core_tools

    def get_conditional_tools(self, question: str, **kwargs) -> tuple[list[BaseTool], dict[str, Any]]:
        """Get tools based on the question and the active flags.

        Three explicit (non-table) gates run first, then the declarative
        SKILLS registry drives keyword-gated on-demand loading:

        1. Flag gates: --repl (host Python REPL) / --code-sandbox (execute_code).
        2. Search-provider cascade: pick the one configured backend
           (credential-only, mutually exclusive, no keyword).
        3. Credential-only extras: image_search (SERPER), reddit (REDDIT_*).

        Everything else is a keyword Skill in SKILLS below.
        """
        tools: list[BaseTool] = []
        local_modules: dict[str, Any] = {}
        question_lower = question.lower()

        # --- Flag-gated tools ------------------------------------------------
        # REPL and code-sandbox are mutually exclusive; repl wins when both set.
        if kwargs.get("repl", False):
            tools.append(self._import_repl_tool(**kwargs))
            # Return local modules for REPL
            module_names = [
                "re",
                "json",
                "time",
                "datetime",
                "random",
                "string",
                "pathlib",
                "requests",
                "git",
                "pandas",
                "faker",
                "numpy",
                "matplotlib",
                "bs4",
                "html2text",
                "pydantic",
                "clipman",
                "pyfiglet",
                "rich",
                "rich.panel",
                "rich.markdown",
                "rich.pretty",
                "rich.table",
                "rich.text",
                "rich.color",
            ]
            local_modules = {module_name: importlib.import_module(module_name) for module_name in module_names}
        elif kwargs.get("code_sandbox", False):
            tools.append(self._import_tool("execute_code"))

        # --- Search-provider cascade (pick configured backend) --------------
        if os.environ.get("TAVILY_API_KEY"):
            tools.extend(self._import_tavily_tools())
        elif os.environ.get("SERPER_API_KEY"):
            tools.append(self._import_tool("ai_serper_search"))
        elif os.environ.get("GOOGLE_CSE_ID") and os.environ.get("GOOGLE_CSE_API_KEY"):
            # Import web_search from par_ai_core
            from par_ai_core.search_utils import web_search

            tools.append(web_search)  # type: ignore
        elif os.environ.get("BRAVE_API_KEY"):
            tools.append(self._import_tool("ai_brave_search"))

        # --- Credential-only extras (no keyword) ----------------------------
        if os.environ.get("SERPER_API_KEY"):
            tools.append(self._import_tool("ai_image_search"))
        if os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"):
            tools.append(self._import_tool("ai_reddit_search"))

        # --- Declarative keyword-gated skills -------------------------------
        # Dedup by tool identity (defensive: skills own disjoint tool sets
        # today, but this keeps the loop correct if that ever changes).
        seen: set[int] = set()
        for skill in SKILLS:
            if not skill.matches(question_lower):
                continue
            for tool in skill.load(self):
                if id(tool) not in seen:
                    seen.add(id(tool))
                    tools.append(tool)

        return tools, local_modules


# Global lazy loader instance
_lazy_loader = LazyToolLoader()


def build_ai_tool_list(
    question: str,
    *,
    repl: bool = False,
    code_sandbox: bool = False,
    yes_to_all: bool = False,
    enable_redis: bool = False,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Build AI tool list using lazy loading."""
    from par_ai_core.par_logging import console_err
    from rich.panel import Panel

    # Time the tool loading operations
    from par_utils import timer

    with timer("core_tools_loading"):
        core_tools = _lazy_loader.get_core_tools(enable_redis=enable_redis)

    with timer("conditional_tools_loading", {"question_length": len(question)}):
        conditional_tools, local_modules = _lazy_loader.get_conditional_tools(
            question, repl=repl, code_sandbox=code_sandbox, yes_to_all=yes_to_all
        )

    all_tools = core_tools + conditional_tools

    # Display loaded tools (like original function)
    console_err.print(Panel.fit(", ".join([tool.name for tool in all_tools]), title="AI Tools"))

    return all_tools, local_modules
