"""Lazy loading system for AI tools to improve startup performance."""

from __future__ import annotations

import importlib
import os
from typing import Any, cast

from langchain_core.tools import BaseTool


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
            "os",
            "sys",
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

        tool = ParPythonAstREPLTool(
            prompt_before_exec=not kwargs.get("yes_to_all", False),
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
        """Get tools based on keywords in the question."""
        tools: list[BaseTool] = []
        local_modules: dict[str, Any] = {}
        question_lower = question.lower()

        # REPL tool
        if kwargs.get("repl", False):
            tools.append(self._import_repl_tool(**kwargs))
            # Return local modules for REPL
            module_names = [
                "os",
                "sys",
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

        # Code sandbox tool
        if not kwargs.get("repl", False) and kwargs.get("code_sandbox", False):
            tools.append(self._import_tool("execute_code"))

        # Keyword-based tool loading
        if "figlet" in question_lower:
            tools.append(self._import_tool("ai_figlet"))

        if os.environ.get("GOOGLE_API_KEY") and "youtube" in question_lower:
            tools.append(self._import_tool("ai_youtube_search"))
        if "youtube" in question_lower:
            tools.append(self._import_tool("ai_youtube_get_transcript"))

        if "git" in question_lower or "commit" in question_lower or "checkout" in question_lower:
            tools.append(self._import_tool("git_commit_tool"))

        # Search tools
        if os.environ.get("TAVILY_API_KEY"):
            tools.extend(self._import_tavily_tools())
        elif os.environ.get("SERPER_API_KEY"):
            tools.append(self._import_tool("ai_serper_search"))
        elif os.environ.get("GOOGLE_CSE_ID") and os.environ.get("GOOGLE_CSE_API_KEY"):
            # Import web_search from par_ai_core
            from par_ai_core.web_tools import web_search

            tools.append(web_search)  # type: ignore
        elif os.environ.get("BRAVE_API_KEY"):
            tools.append(self._import_tool("ai_brave_search"))

        if os.environ.get("SERPER_API_KEY"):
            tools.append(self._import_tool("ai_image_search"))

        if os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"):
            tools.append(self._import_tool("ai_reddit_search"))

        if "clipboard" in question_lower:
            tools.append(self._import_tool("ai_copy_to_clipboard"))
            tools.append(self._import_tool("ai_copy_from_clipboard"))

        if "rss" in question_lower:
            tools.append(self._import_tool("ai_fetch_rss"))

        if "hackernews" in question_lower:
            tools.append(self._import_tool("ai_fetch_hacker_news"))

        if "window" in question_lower:
            tools.append(self._import_tool("ai_list_visible_windows"))

        if "screen" in question_lower or "display" in question_lower:
            tools.append(self._import_tool("ai_list_available_screens"))

        if "capture" in question_lower or "screenshot" in question_lower:
            tools.append(self._import_tool("ai_capture_window_image"))
            tools.append(self._import_tool("ai_capture_screen_image"))

        # Image generation tools
        from par_ai_core.llm_providers import LlmProvider, is_provider_api_key_set

        if (
            is_provider_api_key_set(LlmProvider.OPENAI) or is_provider_api_key_set(LlmProvider.OPENROUTER)
        ) and "image" in question_lower:
            tools.append(self._import_tool("ai_image_gen_dali"))

        # Weather tools
        if os.environ.get("WEATHERAPI_KEY") and ("weather" in question_lower or " wx " in question_lower):
            tools.append(self._import_tool("ai_get_weather_current"))
            tools.append(self._import_tool("ai_get_weather_forecast"))

        # GitHub tools
        if os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") and "github" in question_lower:
            tools.append(self._import_tool("ai_github_list_repos"))
            tools.append(self._import_tool("ai_github_create_repo"))
            tools.append(self._import_tool("ai_github_publish_repo"))

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

    core_tools = _lazy_loader.get_core_tools(enable_redis=enable_redis)
    conditional_tools, local_modules = _lazy_loader.get_conditional_tools(
        question, repl=repl, code_sandbox=code_sandbox, yes_to_all=yes_to_all
    )

    all_tools = core_tools + conditional_tools

    # Display loaded tools (like original function)
    console_err.print(Panel.fit(", ".join([tool.name for tool in all_tools]), title="AI Tools"))

    return all_tools, local_modules
