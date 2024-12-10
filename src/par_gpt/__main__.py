"""Main application"""

from __future__ import annotations

import importlib
import os
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Annotated

import pyperclip
import typer
from langchain_core.tools import BaseTool

from rich.console import Console
from rich.markdown import Markdown

from dotenv import load_dotenv
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text


from langchain_community.tools import BraveSearch, TavilySearchResults


from .ai_tools.par_python_repl import ParPythonAstREPLTool
from .lib.llm_image_utils import (
    try_get_image_type,
    UnsupportedImageTypeError,
    image_to_base64,
)
from .lib.provider_cb_info import get_parai_callback
from .lib.web_tools import web_search, fetch_url_and_convert_to_markdown
from .utils import download_cache, show_image_in_terminal, mk_env_context
from .agents import do_tool_agent, do_single_llm_call, do_code_review_agent, do_prompt_generation_agent

from .ai_tools.ai_tools import (
    ai_fetch_url,
    git_commit_tool,
    ai_open_url,
    ai_get_weather_current,
    ai_get_weather_forecast,
    ai_display_image_in_terminal,
    ai_copy_to_clipboard,
)
from .repo.repo import GitRepo
from .lib.output_utils import DisplayOutputFormat, display_formatted_output
from .lib.utils import has_stdin_content
from .lib.llm_config import LlmConfig, LlmMode
from .lib.pricing_lookup import show_llm_cost, PricingDisplay
from .lib.llm_providers import (
    LlmProvider,
    provider_env_key_names,
    provider_default_models,
    provider_light_models,
    provider_vision_models,
)
from . import __application_title__, __version__, __application_binary__

app = typer.Typer()
console = Console(stderr=True)

ENV_VAR_PREFIX = "PARGPT"

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
            "--ai-provider", "-a", envvar=f"{ENV_VAR_PREFIX}_AI_PROVIDER", help="AI provider to use for processing"
        ),
    ] = LlmProvider.GITHUB,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            envvar=f"{ENV_VAR_PREFIX}_MODEL",
            help="AI model to use for processing. If not specified, a default model will be used.",
        ),
    ] = None,
    light_model: Annotated[
        bool,
        typer.Option(
            "--light-model",
            "-l",
            envvar=f"{ENV_VAR_PREFIX}_LIGHT_MODEL",
            help="Use a light model for processing. If not specified, a default model will be used.",
        ),
    ] = False,
    ai_base_url: Annotated[
        str | None,
        typer.Option(
            "--ai-base-url",
            "-b",
            envvar=f"{ENV_VAR_PREFIX}_AI_BASE_URL",
            help="Override the base URL for the AI provider.",
        ),
    ] = None,
    temperature: Annotated[
        float,
        typer.Option(
            "--temperature",
            "-t",
            envvar=f"{ENV_VAR_PREFIX}_TEMPERATURE",
            help="Temperature to use for processing. If not specified, a default temperature will be used.",
        ),
    ] = 0.5,
    user_agent_appid: Annotated[
        str | None,
        typer.Option(
            "--user-agent-appid",
            "-U",
            envvar=f"{ENV_VAR_PREFIX}_USER_AGENT_APPID",
            help="Extra data to include in the User-Agent header for the AI provider.",
        ),
    ] = None,
    pricing: Annotated[
        PricingDisplay,
        typer.Option("--pricing", "-p", envvar=f"{ENV_VAR_PREFIX}_PRICING", help="Enable pricing summary display"),
    ] = PricingDisplay.NONE,
    display_format: Annotated[
        DisplayOutputFormat,
        typer.Option(
            "--display-output",
            "-d",
            envvar=f"{ENV_VAR_PREFIX}_DISPLAY_OUTPUT",
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
            envvar=f"{ENV_VAR_PREFIX}_AGENT_MODE",
            help="Enable agent mode.",
        ),
    ] = False,
    max_iterations: Annotated[
        int,
        typer.Option(
            "--max-iterations",
            "-i",
            envvar=f"{ENV_VAR_PREFIX}_MAX_ITERATIONS",
            help="Maximum number of iterations to run when in agent mode.",
        ),
    ] = 5,
    max_context_size: Annotated[
        int,
        typer.Option(
            "--max-context-size",
            "-M",
            envvar=f"{ENV_VAR_PREFIX}_MAX_CONTEXT_SIZE",
            help="Maximum context size when provider supports it. 0 = default.",
        ),
    ] = 0,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-D",
            envvar=f"{ENV_VAR_PREFIX}_DEBUG",
            help="Enable debug mode",
        ),
    ] = False,
    show_tool_calls: Annotated[
        bool,
        typer.Option(
            "--show-tool-calls",
            "-T",
            envvar=f"{ENV_VAR_PREFIX}_SHOW_TOOL_CALLS",
            help="Show tool calls",
        ),
    ] = False,
    show_config: Annotated[
        bool,
        typer.Option(
            "--show-config",
            "-S",
            envvar=f"{ENV_VAR_PREFIX}_SHOW_CONFIG",
            help="Show config",
        ),
    ] = False,
    yes_to_all: Annotated[
        bool,
        typer.Option(
            "--yes-to-all",
            "-y",
            envvar=f"{ENV_VAR_PREFIX}_YES_TO_ALL",
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
            envvar=f"{ENV_VAR_PREFIX}_NO_REPL",
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
        if ai_provider not in [LlmProvider.OLLAMA, LlmProvider.BEDROCK]:
            key_name = provider_env_key_names[ai_provider]
            if not os.environ.get(key_name):
                console.print(f"[bold red]{key_name} environment variable not set. Exiting...")
                raise typer.Exit(1)
        if copy_from_clipboard:
            context_location = pyperclip.paste()
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
                model_name=provider_light_models[ai_provider],
                temperature=0,
                mode=LlmMode.CHAT,
                num_ctx=max_context_size,
            )
            with get_parai_callback(
                llm_config, show_end=debug, show_tool_calls=debug or show_tool_calls, show_pricing=pricing
            ):
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
        )

        chat_model = llm_config.build_chat_model()
        chat_model.name = llm_config.model_name

        env_info = mk_env_context({}, console)
        with get_parai_callback(llm_config=llm_config, show_end=debug, show_tool_calls=debug or show_tool_calls) as cb:
            if agent_mode:
                module_names = [
                    "requests",
                    "git",
                    "pandas",
                    "faker",
                    "numpy",
                    "matplotlib",
                    "bs4",
                    "html2text",
                    "pydantic",
                    "pyperclip",
                ]
                local_modules = {module_name: importlib.import_module(module_name) for module_name in module_names}

                ai_tools: list[BaseTool] = [
                    ai_open_url,
                    ai_fetch_url,
                    git_commit_tool,
                    ai_display_image_in_terminal,
                ]  # type: ignore

                if not no_repl:
                    ai_tools.append(
                        ParPythonAstREPLTool(
                            prompt_before_exec=not yes_to_all, show_exec_code=True, locals=local_modules
                        ),
                    )

                # use TavilySearchResults if API key is set with fallback to google search if its key is set
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
                elif os.environ.get("GOOGLE_CSE_ID") and os.environ.get("GOOGLE_CSE_API_KEY"):
                    ai_tools.append(web_search)  # type: ignore
                if os.environ.get("BRAVE_API_KEY"):
                    ai_tools.append(
                        BraveSearch.from_api_key(
                            api_key=os.environ.get("BRAVE_API_KEY") or "", search_kwargs={"count": 3}
                        )
                    )
                if "clipboard" in question:
                    ai_tools.append(ai_copy_to_clipboard)

                if ("weather" in question or " wx " in question) and os.environ.get("WEATHERAPI_KEY"):
                    ai_tools.append(ai_get_weather_current)
                    ai_tools.append(ai_get_weather_forecast)

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
                    io=console,
                )
            else:
                if "code review" in question:
                    content, result = do_code_review_agent(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        env_info=env_info,
                        display_format=display_format,
                        debug=debug,
                        io=console,
                    )
                elif "generate prompt" in question:
                    content, result = do_prompt_generation_agent(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        debug=debug,
                        io=console,
                    )
                else:
                    content, result = do_single_llm_call(
                        chat_model=chat_model,
                        user_input=question,
                        system_prompt=system_prompt,
                        env_info=env_info,
                        image=context if context_is_image else None,
                        display_format=display_format,
                        debug=debug,
                        io=console,
                    )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if copy_to_clipboard:
            pyperclip.copy(content)
            console.print("[bold green]Copied to clipboard")

        if debug:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(llm_config, usage_metadata, console=console, show_pricing=pricing)

        display_formatted_output(content, display_format, out_console=console)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
