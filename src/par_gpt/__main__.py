"""Main application"""

from __future__ import annotations

import copy
import getpass
import importlib
import orjson as json
import os
import platform
import re
import sys
from datetime import datetime, UTC
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Annotated, Any

import pyperclip
import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq

from rich.console import Console
from rich.markdown import Markdown

from dotenv import load_dotenv
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text

from langchain_community.tools.tavily_search import TavilySearchResults

from .ai_tools.par_python_repl import ParPythonAstREPLTool
from .lib.llm_image_utils import (
    try_get_image_type,
    UnsupportedImageTypeError,
    image_to_base64,
    image_to_chat_message,
)
from .lib.provider_cb_info import get_parai_callback
from .lib.web_tools import web_search, fetch_url_and_convert_to_markdown
from .utils import download_cache, show_image_in_terminal
from .agents import do_tool_agent


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
from .lib.output_utils import DisplayOutputFormat, display_formatted_output, get_output_format_prompt
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


# console.print(show_image_in_terminal("https://www.creativefabrica.com/wp-content/uploads/2021/03/31/weather-icon-illustration03-Graphics-10205167-1-1-580x375.jpg"))
# exit()
class ContextSource(StrEnum):
    """Context source."""

    NONE = "none"
    STDIN = "stdin"
    FILE = "file"
    URL = "url"


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
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            envvar=f"{ENV_VAR_PREFIX}_DEBUG",
            help="Enable debug mode",
        ),
    ] = False,
    show_config: Annotated[
        bool,
        typer.Option(
            "--show-config",
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
            help="Copy output to clipboard",
        ),
    ] = False,
    copy_from_clipboard: Annotated[
        bool,
        typer.Option(
            "--copy-from-clipboard",
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
    # console.print(typer.get_app_dir(__application_binary__))
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
        context_is_url: bool = context_location.startswith("http")
        context_is_file: bool = not context_is_url and Path(context_location).is_file()
        if context_location and not context_is_url and not context_is_file and not copy_from_clipboard:
            console.print("[bold red]Context source not found. Exiting...")
            raise typer.Exit(1)

        context: str = ""
        if copy_from_clipboard and not context_is_url and not context_is_file:
            context = context_location
            context_location = ""

        sio_all: StringIO = StringIO()

        if not context_location and not copy_from_clipboard and has_stdin_content():
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
                    context = Path(context_location).read_text().strip()

        if not model:
            if light_model:
                model = provider_light_models[ai_provider]
            else:
                if context_is_image:
                    model = provider_vision_models[ai_provider]
                else:
                    model = provider_default_models[ai_provider]

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
            )
            with get_parai_callback(llm_config, show_end=debug, show_pricing=pricing):
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
            provider=ai_provider, model_name=model, temperature=temperature, base_url=ai_base_url, streaming=False
        )

        chat_model = llm_config.build_chat_model()

        env_info = mk_env_context()
        with get_parai_callback(llm_config, show_end=debug) as cb:
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
                    question=question,
                    image=context if context_is_image else None,
                    system_prompt=system_prompt,
                    max_iterations=max_iterations,
                    debug=debug,
                    io=console,
                )
            else:
                content, result = do_single_llm_call(
                    chat_model=chat_model,
                    question=question,
                    system_prompt=system_prompt,
                    env_info=env_info,
                    image=context if context_is_image else None,
                    display_format=display_format,
                    debug=debug,
                )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if copy_to_clipboard:
            pyperclip.copy(content)

        if debug:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(llm_config, usage_metadata, console=console, show_pricing=pricing)

        display_formatted_output(content, display_format, out_console=console)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


def mk_env_context(extra_context: dict[str, Any] | str | Path | None = None) -> str:
    """
    Create environment context with optional extra context.

    Args:
        extra_context: Optional extra context to add to the context
            Path will be read and parsed as JSON with fallback to plain text
            Dictionary will append / overwrite existing context
            String will be appended as-is

    Returns:
        str: The environment context as Markdown string
    """
    if extra_context is None:
        extra_context = {}

    extra_context_text = ""

    if isinstance(extra_context, Path):
        if not extra_context.is_file():
            raise ValueError(f"Extra context file not found or is not a file: {extra_context}")
        try:
            extra_context = json.loads(extra_context.read_text(encoding="utf-8"))
        except Exception as _:
            extra_context = extra_context.read_text(encoding="utf-8").strip()

    if isinstance(extra_context, dict):
        for k, v in extra_context.items():
            extra_context[k] = str(v)
    elif isinstance(extra_context, (str | list)):
        extra_context_text = str(extra_context)
        extra_context = {}

    extra_context_text = "\n" + extra_context_text.strip()

    return (
        "# Extra Context\n"
        + "\n".join(
            [
                f"- {k}: {v}"
                for k, v in (
                    {
                        "username": getpass.getuser(),
                        "home directory": Path("~").expanduser().as_posix(),
                        "current directory": Path(os.getcwd()).expanduser().as_posix(),
                        "current date and time": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "platform": platform.platform(aliased=True, terse=True),
                        "shell": Path(os.environ.get("SHELL", "bash")).stem,
                        "term": os.environ.get("TERM", "xterm-256color"),
                        "console dimensions": f"{console.width}x{console.height}",
                    }
                    | extra_context
                ).items()  # type: ignore
            ]
        )
        + "\n"
    ) + extra_context_text


def do_single_llm_call(
    *,
    chat_model: BaseChatModel,
    question: str,
    image: str | None = None,
    system_prompt: str | None,
    env_info: str,
    display_format: DisplayOutputFormat,
    debug: bool,
):
    default_system_prompt = (
        "ROLE: You are a helpful assistant. Try to be concise and brief unless the user requests otherwise."
    )

    chat_history: list[tuple[str, str | list[dict[str, Any]]]] = [
        ("system", (system_prompt or default_system_prompt).strip() + "\n" + get_output_format_prompt(display_format)),
        ("user", env_info),
    ]
    # Groq does not support images if a system prompt is specified
    if isinstance(chat_model, ChatGroq) and image:
        chat_history.pop(0)

    chat_history_debug = copy.deepcopy(chat_history)
    if image:
        chat_history.append(("user", [{"type": "text", "text": question}, image_to_chat_message(image)]))
        chat_history_debug.append(("user", [{"type": "text", "text": question}, ({"IMAGE": "DATA"})]))
    else:
        chat_history.append(("user", question))
        chat_history_debug.append(("user", question))

    if debug:
        console.print(Panel.fit(Pretty(chat_history_debug), title="GPT Prompt"))
    result = chat_model.invoke(chat_history)  # type: ignore
    content = str(result.content).replace("```markdown", "").replace("```", "").strip()
    result.content = content
    return content, result


if __name__ == "__main__":
    app()
