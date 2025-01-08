"""Main application"""

from __future__ import annotations

import importlib
import os
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Annotated

import clipman as clipboard
import typer
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import BaseTool
from par_ai_core.llm_config import LlmConfig, LlmMode
from par_ai_core.llm_image_utils import (
    UnsupportedImageTypeError,
    image_to_base64,
    try_get_image_type,
)
from par_ai_core.llm_providers import (
    LlmProvider,
    provider_default_models,
    provider_env_key_names,
    provider_light_models,
    provider_vision_models,
)
from par_ai_core.output_utils import DisplayOutputFormat, display_formatted_output
from par_ai_core.par_logging import console_err
from par_ai_core.pricing_lookup import PricingDisplay, show_llm_cost
from par_ai_core.provider_cb_info import get_parai_callback
from par_ai_core.utils import has_stdin_content
from par_ai_core.web_tools import fetch_url_and_convert_to_markdown, web_search
from rich.markdown import Markdown
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text

from par_gpt.ai_tools.ai_tools import (
    ai_brave_search,
    ai_figlet,
    ai_github_create_repo,
    ai_github_list_repos,
    ai_github_publish_repo,
    ai_serper_search,
    ai_fetch_rss,
    ai_fetch_hacker_news,
)

from . import __application_binary__, __application_title__, __env_var_prefix__, __version__
from .agents import do_code_review_agent, do_prompt_generation_agent, do_single_llm_call, do_tool_agent
from .ai_tools.ai_tools import (
    ai_copy_from_clipboard,
    ai_copy_to_clipboard,
    ai_display_image_in_terminal,
    ai_fetch_url,
    ai_get_weather_current,
    ai_get_weather_forecast,
    ai_open_url,
    ai_reddit_search,
    ai_youtube_get_transcript,
    ai_youtube_search,
    git_commit_tool,
)
from .ai_tools.par_python_repl import ParPythonAstREPLTool
from .repo.repo import GitRepo
from .utils import download_cache, mk_env_context, show_image_in_terminal

app = typer.Typer()
console = console_err


load_dotenv()
load_dotenv(Path(f"~/.{__application_binary__}.env").expanduser())


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__application_title__}: {__version__}")
        raise typer.Exit()


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def main(
    ai_provider: Annotated[
        LlmProvider,
        typer.Option(
            "--ai-provider", "-a", envvar=f"{__env_var_prefix__}_AI_PROVIDER", help="AI provider to use for processing"
        ),
    ] = LlmProvider.GITHUB,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            envvar=f"{__env_var_prefix__}_MODEL",
            help="AI model to use for processing. If not specified, a default model will be used.",
        ),
    ] = None,
    light_model: Annotated[
        bool,
        typer.Option(
            "--light-model",
            "-l",
            envvar=f"{__env_var_prefix__}_LIGHT_MODEL",
            help="Use a light model for processing. If not specified, a default model will be used.",
        ),
    ] = False,
    ai_base_url: Annotated[
        str | None,
        typer.Option(
            "--ai-base-url",
            "-b",
            envvar=f"{__env_var_prefix__}_AI_BASE_URL",
            help="Override the base URL for the AI provider.",
        ),
    ] = None,
    temperature: Annotated[
        float,
        typer.Option(
            "--temperature",
            "-t",
            envvar=f"{__env_var_prefix__}_TEMPERATURE",
            help="Temperature to use for processing. If not specified, a default temperature will be used.",
        ),
    ] = 0.5,
    user_agent_appid: Annotated[
        str | None,
        typer.Option(
            "--user-agent-appid",
            "-U",
            envvar=f"{__env_var_prefix__}_USER_AGENT_APPID",
            help="Extra data to include in the User-Agent header for the AI provider.",
        ),
    ] = None,
    pricing: Annotated[
        PricingDisplay,
        typer.Option("--pricing", "-p", envvar=f"{__env_var_prefix__}_PRICING", help="Enable pricing summary display"),
    ] = PricingDisplay.NONE,
    display_format: Annotated[
        DisplayOutputFormat,
        typer.Option(
            "--display-output",
            "-d",
            envvar=f"{__env_var_prefix__}_DISPLAY_OUTPUT",
            help="Display output in terminal (none, plain, md, csv, or json)",
        ),
    ] = DisplayOutputFormat.MD,
    context_location: Annotated[
        str,
        typer.Option(
            "--context-location",
            "-f",
            help="Location of context to use for processing.",
        ),
    ] = "",
    system_prompt: Annotated[
        str | None,
        typer.Option(
            "--system-prompt",
            "-s",
            help="System prompt to use for processing. If not specified, a default system prompt will be used.",
        ),
    ] = None,
    user_prompt: Annotated[
        str | None,
        typer.Option(
            "--user-prompt",
            "-u",
            help="User prompt to use for processing. If not specified, a default user prompt will be used.",
        ),
    ] = None,
    agent_mode: Annotated[
        bool,
        typer.Option(
            "--agent-mode",
            "-g",
            envvar=f"{__env_var_prefix__}_AGENT_MODE",
            help="Enable agent mode.",
        ),
    ] = False,
    max_iterations: Annotated[
        int,
        typer.Option(
            "--max-iterations",
            "-i",
            envvar=f"{__env_var_prefix__}_MAX_ITERATIONS",
            help="Maximum number of iterations to run when in agent mode.",
        ),
    ] = 5,
    max_context_size: Annotated[
        int,
        typer.Option(
            "--max-context-size",
            "-M",
            envvar=f"{__env_var_prefix__}_MAX_CONTEXT_SIZE",
            help="Maximum context size when provider supports it. 0 = default.",
        ),
    ] = 0,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-D",
            envvar=f"{__env_var_prefix__}_DEBUG",
            help="Enable debug mode",
        ),
    ] = False,
    show_tool_calls: Annotated[
        bool,
        typer.Option(
            "--show-tool-calls",
            "-T",
            envvar=f"{__env_var_prefix__}_SHOW_TOOL_CALLS",
            help="Show tool calls",
        ),
    ] = False,
    show_config: Annotated[
        bool,
        typer.Option(
            "--show-config",
            "-S",
            envvar=f"{__env_var_prefix__}_SHOW_CONFIG",
            help="Show config",
        ),
    ] = False,
    yes_to_all: Annotated[
        bool,
        typer.Option(
            "--yes-to-all",
            "-y",
            envvar=f"{__env_var_prefix__}_YES_TO_ALL",
            help="Yes to all prompts",
        ),
    ] = False,
    copy_to_clipboard: Annotated[
        bool,
        typer.Option(
            "--copy-to-clipboard",
            "-c",
            help="Copy output to clipboard",
        ),
    ] = False,
    copy_from_clipboard: Annotated[
        bool,
        typer.Option(
            "--copy-from-clipboard",
            "-C",
            help="Copy context or context location from clipboard",
        ),
    ] = False,
    no_repl: Annotated[
        bool,
        typer.Option(
            "--no-repl",
            envvar=f"{__env_var_prefix__}_NO_REPL",
            help="Disable REPL tool",
        ),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
    unknown_args: typer.Context = typer.Option(None),
) -> None:
    """Main function."""
    # console.print((Path(__file__).parent / "prompts" / "meta_prompt.xml").is_file())
    # console.print(typer.get_app_dir(__application_binary__))
    # exit(0)
    # for unknown_arg in unknown_args.args:
    #     typer.echo(f"Got extra arg: {unknown_arg}")
    # return
    try:
        if ai_provider not in [LlmProvider.OLLAMA, LlmProvider.LLAMACPP, LlmProvider.BEDROCK]:
            key_name = provider_env_key_names[ai_provider]
            if not os.environ.get(key_name):
                console.print(f"[bold red]{key_name} environment variable not set. Exiting...")
                raise typer.Exit(1)
        if copy_from_clipboard:
            context_location = clipboard.paste()
            console.print("[bold green]Context copied from clipboard")

        context_is_url: bool = context_location.startswith("http")
        if context_is_url:
            console.print("[bold green]Context is URL and will be downloaded")

        context_is_file: bool = not context_is_url and "\n" not in context_location and Path(context_location).is_file()
        if context_is_file:
            console.print("[bold green]Context is file and will be read")

        if context_location and not context_is_url and not context_is_file and not copy_from_clipboard:
            console.print("[bold red]Context source not found. Exiting...")
            raise typer.Exit(1)

        context: str = ""
        if copy_from_clipboard and not context_is_url and not context_is_file:
            context = context_location
            context_location = ""

        sio_all: StringIO = StringIO()
        if not context_location and not copy_from_clipboard and has_stdin_content():
            console.print("[bold green]Context is stdin and will be read")
            for line in sys.stdin:
                sio_all.write(line)
            context = sio_all.getvalue().strip()

        context_is_image = False
        if context_location:
            if context_is_url:
                try:
                    image_type = try_get_image_type(context_location)
                    image_path = download_cache.download(context_location)
                    context = image_to_base64(image_path.read_bytes(), image_type)
                    context_is_image = True
                    show_image_in_terminal(image_path)
                except UnsupportedImageTypeError as _:
                    context = fetch_url_and_convert_to_markdown(str(context_location))[0].strip()
            else:
                try:
                    image_type = try_get_image_type(context_location)
                    image_path = Path(context_location)
                    context = image_to_base64(image_path.read_bytes(), image_type)
                    context_is_image = True
                    show_image_in_terminal(image_path)
                except UnsupportedImageTypeError as _:
                    context = Path(context_location).read_text(encoding="utf-8").strip()

        if not model:
            if light_model:
                model = provider_light_models[ai_provider]
            else:
                if context_is_image:
                    model = provider_vision_models[ai_provider]
                else:
                    model = provider_default_models[ai_provider]
            console.print(f"[bold green]Auto selected model: {model}")

        if not user_prompt and len(unknown_args.args) > 0:
            user_prompt = unknown_args.args.pop(0)

        if not context and not user_prompt:
            console.print("[bold red]No context or user prompt provided. Exiting...")
            raise typer.Exit(1)

        question = user_prompt or context
        if re.match(r"(get|show|list|display) (env|environment|extra context)", question, flags=re.IGNORECASE):
            console.print(Markdown(mk_env_context()))
            return
        if re.match(r"(git|gen|generate|create|do|show|display) commit", question, flags=re.IGNORECASE):
            llm_config = LlmConfig(
                provider=ai_provider,
                model_name=model,
                temperature=0,
                mode=LlmMode.CHAT,
                streaming=False,
                user_agent_appid=user_agent_appid,
                num_ctx=max_context_size,
                env_prefix=__env_var_prefix__,
                base_url=ai_base_url,
            ).set_env()
            with get_parai_callback(show_end=debug, show_tool_calls=debug or show_tool_calls, show_pricing=pricing):
                repo = GitRepo(llm_config=llm_config)
                if not repo.is_dirty():
                    console.print("[bold yellow]No changes to commit. Exiting...")
                    return
                # console.print(repo.get_dirty_files())
                # return
                if re.match(r"(display|show)\s?(git|gen|generate|create|do)? commit", question, flags=re.IGNORECASE):
                    console.print(repo.get_commit_message(repo.get_diffs(unknown_args.args), context=context))
                else:
                    repo.commit(unknown_args.args, context=context)
                return

        if user_prompt and context and not context_is_image:
            question = "\n<context>\n" + context + "\n</context>\n" + question

        if show_config:
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
                        ("AI Provider Base URL: ", "cyan"),
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
                        ("Agent Mode: ", "cyan"),
                        (f"{agent_mode}", "green"),
                        "\n",
                        ("Debug: ", "cyan"),
                        (f"{debug}", "green"),
                        "\n",
                    ),
                    title="[bold]GPT Configuration",
                    border_style="bold",
                )
            )

        llm_config = LlmConfig(
            provider=ai_provider,
            model_name=model,
            temperature=temperature,
            base_url=ai_base_url,
            streaming=False,
            user_agent_appid=user_agent_appid,
            num_ctx=max_context_size,
            env_prefix=__env_var_prefix__,
        ).set_env()

        chat_model = llm_config.build_chat_model()
        question = question.strip()
        question_lower = question.lower()

        env_info = mk_env_context({}, console)
        with get_parai_callback(show_end=debug, show_tool_calls=debug or show_tool_calls) as cb:
            if agent_mode:
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
                    # "rich.console",
                    "rich.panel",
                    "rich.markdown",
                    "rich.pretty",
                    "rich.table",
                    "rich.text",
                    "rich.color",
                ]
                local_modules = {module_name: importlib.import_module(module_name) for module_name in module_names}

                ai_tools: list[BaseTool] = [
                    ai_open_url,
                    ai_fetch_url,
                    git_commit_tool,
                    ai_display_image_in_terminal,
                    ai_youtube_get_transcript,
                    # ai_joke,
                ]  # type: ignore

                if "figlet" in question_lower:
                    ai_tools.append(ai_figlet)

                if not no_repl:
                    ai_tools.append(
                        ParPythonAstREPLTool(
                            prompt_before_exec=not yes_to_all, show_exec_code=True, locals=local_modules
                        ),
                    )

                if os.environ.get("GOOGLE_API_KEY") and "youtube" in question_lower:
                    ai_tools.append(ai_youtube_search)

                # use TavilySearchResults with fallback to serper and google search if api keys are set
                if os.environ.get("TAVILY_API_KEY"):
                    ai_tools.append(
                        TavilySearchResults(
                            max_results=3,
                            include_answer=True,
                            topic="news",  # type: ignore
                            name="tavily_news_results_json",
                            description="Search news and current events",
                        )
                    )
                    ai_tools.append(
                        TavilySearchResults(
                            max_results=3,
                            include_answer=True,
                            name="tavily_search_results_json",
                            description="General search for content not directly related to current events",
                        )
                    )
                elif os.environ.get("SERPER_API_KEY"):
                    ai_tools.append(ai_serper_search)
                elif os.environ.get("GOOGLE_CSE_ID") and os.environ.get("GOOGLE_CSE_API_KEY"):
                    ai_tools.append(web_search)  # type: ignore

                if os.environ.get("BRAVE_API_KEY"):
                    ai_tools.append(ai_brave_search)

                if os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"):
                    ai_tools.append(ai_reddit_search)

                if "clipboard" in question_lower:
                    ai_tools.append(ai_copy_to_clipboard)
                    ai_tools.append(ai_copy_from_clipboard)
                if "rss" in question_lower:
                    ai_tools.append(ai_fetch_rss)
                if "hackernews" in question_lower:
                    ai_tools.append(ai_fetch_hacker_news)

                if os.environ.get("WEATHERAPI_KEY") and ("weather" in question_lower or " wx " in question_lower):
                    ai_tools.append(ai_get_weather_current)
                    ai_tools.append(ai_get_weather_forecast)
                if os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") and "github" in question_lower:
                    ai_tools.append(ai_github_list_repos)
                    ai_tools.append(ai_github_create_repo)
                    ai_tools.append(ai_github_publish_repo)

                console.print(Panel.fit(", ".join([tool.name for tool in ai_tools]), title="AI Tools"))

                content, result = do_tool_agent(
                    chat_model=chat_model,
                    ai_tools=ai_tools,
                    modules=module_names,
                    env_info=env_info,
                    user_input=question,
                    image=context if context_is_image else None,
                    system_prompt=system_prompt,
                    max_iterations=max_iterations,
                    debug=debug,
                    console=console,
                )
            else:
                if "code review" in question_lower:
                    content, result = do_code_review_agent(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        env_info=env_info,
                        display_format=display_format,
                        debug=debug,
                        console=console,
                    )
                elif "generate prompt" in question_lower:
                    content, result = do_prompt_generation_agent(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        debug=debug,
                        console=console,
                    )
                else:
                    content, result = do_single_llm_call(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        no_system_prompt=chat_model.name is not None and chat_model.name.startswith("o1"),
                        env_info=env_info,
                        image=context if context_is_image else None,
                        display_format=display_format,
                        debug=debug,
                        console=console,
                    )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if copy_to_clipboard:
            clipboard.copy(content)
            console.print("[bold green]Copied to clipboard")

        if debug:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(usage_metadata, console=console, show_pricing=pricing)

        display_formatted_output(content, display_format, console=console)

    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
