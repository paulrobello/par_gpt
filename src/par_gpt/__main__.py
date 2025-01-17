"""Main application"""

from __future__ import annotations

import importlib
import os
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, cast

import clipman as clipboard
import typer
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import BaseTool
from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_image_utils import (
    UnsupportedImageTypeError,
    image_to_base64,
    try_get_image_type,
)
from par_ai_core.llm_providers import (
    LlmProvider,
    is_provider_api_key_set,
    provider_base_urls,
    provider_default_models,
    provider_env_key_names,
    provider_light_models,
    provider_vision_models,
)
from par_ai_core.output_utils import DisplayOutputFormat, display_formatted_output
from par_ai_core.par_logging import console_err
from par_ai_core.pricing_lookup import PricingDisplay, show_llm_cost
from par_ai_core.provider_cb_info import get_parai_callback
from par_ai_core.utils import (
    get_file_list_for_context,
    has_stdin_content,
)
from par_ai_core.web_tools import fetch_url_and_convert_to_markdown, web_search
from rich.panel import Panel
from rich.pretty import Pretty
from rich.prompt import Prompt
from rich.text import Text

from par_gpt.ai_tools.ai_tools import (
    ai_brave_search,
    ai_fetch_hacker_news,
    ai_fetch_rss,
    ai_figlet,
    ai_github_create_repo,
    ai_github_list_repos,
    ai_github_publish_repo,
    ai_image_search,
    ai_list_visible_windows,
    ai_serper_search,
    execute_code,
)
from par_gpt.tts_manger import TTSManger, TTSProvider, summarize_for_tts
from par_gpt.voice_input_manger import VoiceInputManager

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
from .utils import (
    cache_manager,
    mk_env_context,
    show_image_in_terminal,
)

app = typer.Typer()
console = console_err


load_dotenv(Path(f"~/.{__application_binary__}.env").expanduser())


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__application_title__}: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    ai_provider: Annotated[
        LlmProvider,
        typer.Option(
            "--ai-provider", "-a", envvar=f"{__env_var_prefix__}_AI_PROVIDER", help="AI provider to use for processing"
        ),
    ] = LlmProvider.OPENAI,
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
    max_context_size: Annotated[
        int,
        typer.Option(
            "--max-context-size",
            "-M",
            envvar=f"{__env_var_prefix__}_MAX_CONTEXT_SIZE",
            help="Maximum context size when provider supports it. 0 = default.",
        ),
    ] = 0,
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
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-D",
            envvar=f"{__env_var_prefix__}_DEBUG",
            help="Enable debug mode",
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
    tts: Annotated[
        bool,
        typer.Option(
            "--tts",
            "-T",
            envvar=f"{__env_var_prefix__}_TTS",
            help="Use TTS for LLM response.",
        ),
    ] = False,
    tts_provider: Annotated[
        TTSProvider | None,
        typer.Option(
            "--tts-provider",
            envvar=f"{__env_var_prefix__}_TTS_PROVIDER",
            help="Provider to use for TTS. Defaults to kokoro",
        ),
    ] = None,
    tts_voice: Annotated[
        str | None,
        typer.Option(
            "--tts-voice",
            envvar=f"{__env_var_prefix__}_TTS_VOICE",
            help="Voice to use for TTS. Depends on TTS provider chosen.",
        ),
    ] = None,
    tts_list_voices: Annotated[
        bool | None,
        typer.Option(
            "--tts-list-voices",
            help="List voices for selected TTS provider.",
        ),
    ] = None,
    voice_input: Annotated[
        bool,
        typer.Option(
            "--voice-input",
            help="Use voice input.",
        ),
    ] = False,
    version: Annotated[  # pylint: disable=unused-argument
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
):
    """
    PAR GPT
    """
    # console.print(Pretty(ctx.invoked_subcommand))
    if ai_provider not in [LlmProvider.OLLAMA, LlmProvider.LLAMACPP, LlmProvider.BEDROCK]:
        key_name = provider_env_key_names[ai_provider]
        if not os.environ.get(key_name):
            console.print(f"[bold red]{key_name} environment variable not set. Exiting...")
            raise typer.Exit(1)

    if copy_from_clipboard and context_location:
        console.print("[bold red]copy_from_clipboard and context_location are mutually exclusive. Exiting...")
        raise typer.Exit(1)

    if copy_from_clipboard:
        context_location = clipboard.paste()
        console.print("[bold green]Context copied from clipboard")

    context_is_url: bool = context_location.startswith("http")
    if context_is_url:
        console.print("[bold green]Context is URL and will be fetched...")

    context_is_file: bool = not context_is_url and "\n" not in context_location and Path(context_location).is_file()
    if context_is_file:
        console.print("[bold green]Context is file and will be read...")

    if context_location and not context_is_url and not context_is_file and not copy_from_clipboard:
        console.print(f"[bold red]Context source '{context_location}' not found. Exiting...")
        raise typer.Exit(1)

    context: str = ""
    if copy_from_clipboard and not context_is_url and not context_is_file:
        context = context_location
        context_location = ""

    sio_all: StringIO = StringIO()
    if not context_location and not copy_from_clipboard and has_stdin_content():
        console.print("[bold green]Context is stdin and will be read...")
        for line in sys.stdin:
            sio_all.write(line)
        context = sio_all.getvalue().strip()

    context_is_image = False
    if context_location:
        console.print("[bold green]Detecting if context is an image...")
        if context_is_url:
            try:
                image_type = try_get_image_type(context_location)
                console.print(f"[bold green]Image type {image_type} detected.")
                image_path = cache_manager.download(context_location)
                context = image_to_base64(image_path.read_bytes(), image_type)
                context_is_image = True
                show_image_in_terminal(image_path)
            except UnsupportedImageTypeError as _:
                context = fetch_url_and_convert_to_markdown(context_location)[0].strip()
        else:
            try:
                image_type = try_get_image_type(context_location)
                console.print(f"[bold green]Image type {image_type} detected.")
                image_path = Path(context_location)
                context = image_to_base64(image_path.read_bytes(), image_type)
                context_is_image = True
                show_image_in_terminal(image_path)
            except UnsupportedImageTypeError as _:
                context = Path(context_location).read_text(encoding="utf-8").strip()

    if not model:
        if light_model:
            model = provider_light_models[ai_provider]
            model_type = "light"
        else:
            if context_is_image:
                model = provider_vision_models[ai_provider]
                model_type = "vision"
            else:
                model = provider_default_models[ai_provider]
                model_type = "default"
        if not model:
            console.print(f"[bold red]No supported {model_type} model found for {ai_provider}. Exiting...")
            raise typer.Exit(1)

        console.print(f"[bold green]Auto selected {model_type} model: {model}")

    if ai_base_url == "none":
        ai_base_url = provider_base_urls[ai_provider]
    llm_config = LlmConfig(
        provider=ai_provider,
        model_name=model,
        temperature=temperature,
        base_url=ai_base_url,
        streaming=False,
        user_agent_appid=user_agent_appid,
        num_ctx=max_context_size or None,
        env_prefix=__env_var_prefix__,
    ).set_env()
    tts_man: TTSManger | None = None
    if tts:
        if tts_list_voices:
            voices = TTSManger(tts_provider or TTSProvider.KOKORO, console=console).list_voices()
            console.print("\nAvailable voices:", voices)
            exit(0)
        tts_man = TTSManger(tts_provider or TTSProvider.KOKORO, voice_name=tts_voice, console=console)
    voice_input_man: VoiceInputManager | None = None
    if voice_input:
        voice_input_man = VoiceInputManager(wake_word="jenny", verbose=debug or True, sanity_check_sentence=False)

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
                    ("TTS: ", "cyan"),
                    (f"{tts}", "green"),
                    "\n",
                    ("TTS Provider: ", "cyan"),
                    (f"{tts_provider}", "green"),
                    "\n",
                    ("TTS Voice: ", "cyan"),
                    (f"{tts_voice or 'Default'}", "green"),
                    "\n",
                    ("Voice Input: ", "cyan"),
                    (f"{voice_input}", "green"),
                    "\n",
                    ("Debug: ", "cyan"),
                    (f"{debug}", "green"),
                    "\n",
                ),
                title="[bold]GPT Configuration",
                border_style="bold",
            )
        )

    state = {
        "debug": debug,
        "ai_provider": ai_provider,
        "model": model,
        "ai_base_url": ai_base_url,
        "pricing": pricing,
        "is_sixel_supported": False,  # query_terminal_support(),
        "llm_config": llm_config,
        "store_url": os.environ["VECTOR_STORE_URL"],
        "collection_name": "par_gpt",
        "temperature": temperature,
        "user_agent_appid": user_agent_appid,
        "display_format": display_format,
        "context_location": context_location,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "max_context_size": max_context_size,
        "copy_to_clipboard": copy_to_clipboard,
        "copy_from_clipboard": copy_from_clipboard,
        "show_config": show_config,
        "context": context,
        "context_is_image": context_is_image,
        "tts": tts,
        "tts_provider": tts_provider,
        "tts_voice": tts_voice,
        "tts_man": tts_man,
        "voice_input_man": voice_input_man,
    }

    ctx.obj = state


@app.command()
def show_env() -> None:
    """Show environment context."""
    console.print(mk_env_context())


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def llm(
    ctx: typer.Context,
) -> None:
    """Basic LLM mode with no tools."""
    state = ctx.obj
    # console.print((Path(__file__).parent / "prompts" / "meta_prompt.xml").is_file())
    # console.print(typer.get_app_dir(__application_binary__))
    # exit(0)
    # for unknown_arg in unknown_args.args:
    #     typer.echo(f"Got extra arg: {unknown_arg}")
    # return

    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"]

    if not question:
        console.print("[bold red]No context or user prompt provided. Exiting...")
        raise typer.Exit(1)

    if state["user_prompt"] and state["context"] and not state["context_is_image"]:
        question = "\n<context>\n" + state["context"] + "\n</context>\n" + question

    question = question.strip()

    try:
        chat_model = state["llm_config"].build_chat_model()

        env_info = mk_env_context({}, console)
        with get_parai_callback(show_end=state["debug"], show_tool_calls=state["debug"]) as cb:
            content, result = do_single_llm_call(
                chat_model=chat_model,
                user_input=question,
                system_prompt=state["system_prompt"],
                no_system_prompt=chat_model.name is not None and chat_model.name.startswith("o1"),
                env_info=env_info,
                image=state["context"] if state["context_is_image"] else None,
                display_format=state["display_format"],
                debug=state["debug"],
                console=console,
                use_tts=state["tts"],
            )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if state["copy_to_clipboard"]:
            clipboard.copy(content)
            console.print("[bold green]Copied to clipboard")

        if state["debug"]:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(usage_metadata, console=console, show_pricing=state["pricing"])

        display_formatted_output(content, state["display_format"], console=console)
        if state["tts_man"]:
            state["tts_man"].speak(content)

    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def git(
    ctx: typer.Context,
) -> None:
    """Git commit helper."""
    state = ctx.obj

    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"]

    if not question:
        console.print("[bold red]No context or user prompt provided. Exiting...")
        raise typer.Exit(1)

    if state["user_prompt"] and state["context"] and not state["context_is_image"]:
        question = "\n<context>\n" + state["context"] + "\n</context>\n" + question

    question = question.strip()

    try:
        with get_parai_callback(show_end=state["debug"], show_tool_calls=state["debug"], show_pricing=state["pricing"]):
            repo = GitRepo(llm_config=state["llm_config"])
            if not repo.is_dirty():
                console.print("[bold yellow]No changes to commit. Exiting...")
                return
            # console.print(repo.get_dirty_files())
            # return
            if re.match(r"(display|show)\s?(git|gen|generate|create|do)? commit", question, flags=re.IGNORECASE):
                console.print(repo.get_commit_message(repo.get_diffs(ctx.args), context=state["context"]))
            else:
                repo.commit(ctx.args, context=state["context"])
    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def code_review(
    ctx: typer.Context,
) -> None:
    """Review code."""
    state = ctx.obj
    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"]
    if not question:
        question = "Please review code"

    if state["user_prompt"] and state["context"] and not state["context_is_image"]:
        question = "\n<context>\n" + state["context"] + "\n</context>\n" + question

    question = question.strip()

    try:
        chat_model = state["llm_config"].build_chat_model()

        env_info = mk_env_context({}, console)
        with get_parai_callback(show_end=state["debug"], show_tool_calls=state["debug"]) as cb:
            content, result = do_code_review_agent(
                chat_model=chat_model,
                user_input=question,
                system_prompt=state["system_prompt"],
                env_info=env_info,
                display_format=state["display_format"],
                debug=state["debug"],
                console=console,
            )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if state["copy_to_clipboard"]:
            clipboard.copy(content)
            console.print("[bold green]Copied to clipboard")

        if state["debug"]:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(usage_metadata, console=console, show_pricing=state["pricing"])

        display_formatted_output(content, state["display_format"], console=console)
    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def generate_prompt(
    ctx: typer.Context,
) -> None:
    """Use meta prompting to generate a new prompt."""
    state = ctx.obj

    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"]

    if not question:
        console.print("[bold red]No context or user prompt provided. Exiting...")
        raise typer.Exit(1)

    if state["user_prompt"] and state["context"] and not state["context_is_image"]:
        question = "\n<context>\n" + state["context"] + "\n</context>\n" + question

    question = question.strip()

    try:
        chat_model = state["llm_config"].build_chat_model()

        with get_parai_callback(show_end=state["debug"], show_tool_calls=state["debug"]) as cb:
            content, result = do_prompt_generation_agent(
                chat_model=chat_model,
                user_input=question,
                system_prompt=state["system_prompt"],
                debug=state["debug"],
                console=console,
            )

            usage_metadata = cb.usage_metadata

        if not sys.stdout.isatty():
            print(content)

        if state["copy_to_clipboard"]:
            clipboard.copy(content)
            console.print("[bold green]Copied to clipboard")

        if state["debug"]:
            console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        show_llm_cost(usage_metadata, console=console, show_pricing=state["pricing"])

        display_formatted_output(content, state["display_format"], console=console)

    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


def build_ai_tool_list(
    question: str, *, repl: bool = False, code_sandbox: bool = False, yes_to_all: bool = False
) -> tuple[list[BaseTool], dict[str, Any]]:
    ai_tools: list[BaseTool] = [
        ai_open_url,
        ai_fetch_url,
        ai_display_image_in_terminal,
        # ai_joke,
    ]  # type: ignore
    question_lower = question.lower()

    if repl:
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

        ai_tools.append(
            ParPythonAstREPLTool(prompt_before_exec=not yes_to_all, show_exec_code=True, locals=local_modules),
        )
    else:
        local_modules = {}

    if not repl and code_sandbox:
        ai_tools.append(execute_code)

    if "figlet" in question_lower:
        ai_tools.append(ai_figlet)

    if os.environ.get("GOOGLE_API_KEY") and "youtube" in question_lower:
        ai_tools.append(ai_youtube_search)
    if "youtube" in question_lower:
        ai_tools.append(ai_youtube_get_transcript)
    if "git" in question_lower or "commit" in question_lower:
        ai_tools.append(git_commit_tool)

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
    elif os.environ.get("BRAVE_API_KEY"):
        ai_tools.append(ai_brave_search)

    if os.environ.get("SERPER_API_KEY"):
        ai_tools.append(ai_image_search)

    if os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"):
        ai_tools.append(ai_reddit_search)

    if "clipboard" in question_lower:
        ai_tools.append(ai_copy_to_clipboard)
        ai_tools.append(ai_copy_from_clipboard)
    if "rss" in question_lower:
        ai_tools.append(ai_fetch_rss)
    if "hackernews" in question_lower:
        ai_tools.append(ai_fetch_hacker_news)
    if "window" in question_lower:
        ai_tools.append(ai_list_visible_windows)

    if os.environ.get("WEATHERAPI_KEY") and ("weather" in question_lower or " wx " in question_lower):
        ai_tools.append(ai_get_weather_current)
        ai_tools.append(ai_get_weather_forecast)
    if os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") and "github" in question_lower:
        ai_tools.append(ai_github_list_repos)
        ai_tools.append(ai_github_create_repo)
        ai_tools.append(ai_github_publish_repo)

    console.print(Panel.fit(", ".join([tool.name for tool in ai_tools]), title="AI Tools"))
    return ai_tools, local_modules


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def agent(
    ctx: typer.Context,
    max_iterations: Annotated[
        int,
        typer.Option(
            "--max-iterations",
            "-i",
            envvar=f"{__env_var_prefix__}_MAX_ITERATIONS",
            help="Maximum number of iterations to run when in agent mode.",
        ),
    ] = 5,
    show_tool_calls: Annotated[
        bool,
        typer.Option(
            "--show-tool-calls",
            "-T",
            envvar=f"{__env_var_prefix__}_SHOW_TOOL_CALLS",
            help="Show tool calls",
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
    repl: Annotated[
        bool,
        typer.Option(
            "--repl",
            envvar=f"{__env_var_prefix__}_REPL",
            help="Enable REPL tool",
        ),
    ] = False,
    code_sandbox: Annotated[
        bool,
        typer.Option(
            "--code-sandbox",
            envvar=f"{__env_var_prefix__}_CODE_SANDBOX",
            help="Enable code sandbox tool. Requires a running code sandbox container.",
        ),
    ] = False,
) -> None:
    """Full agent with dynamic tools."""
    state = ctx.obj
    # console.print((Path(__file__).parent / "prompts" / "meta_prompt.xml").is_file())
    # console.print(typer.get_app_dir(__application_binary__))
    # exit(0)
    # for unknown_arg in unknown_args.args:
    #     typer.echo(f"Got extra arg: {unknown_arg}")
    # return

    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"] or ""

    if not question and not state["voice_input_man"]:
        console.print("[bold red]No context or user prompt provided. Exiting...")
        raise typer.Exit(1)

    if state["user_prompt"] and state["context"] and not state["context_is_image"]:
        question = "\n<context>\n" + state["context"] + "\n</context>\n" + question

    question = question.strip()
    try:
        chat_model = state["llm_config"].build_chat_model()

        env_info = mk_env_context({}, console)

        with get_parai_callback(
            show_end=state["debug"],
            show_tool_calls=state["debug"] or show_tool_calls,
            console=console,
            show_pricing=state["pricing"],
        ) as cb:
            if state["voice_input_man"]:
                chat_history = []
                while True:
                    prompt = state["voice_input_man"].get_text()
                    if not prompt:
                        continue
                    if prompt.lower().strip() == "exit":
                        break
                    ai_tools, local_modules = build_ai_tool_list(
                        question, repl=repl, code_sandbox=code_sandbox, yes_to_all=yes_to_all
                    )
                    chat_history.append(("user", prompt))
                    if state["tts_man"]:
                        state["tts_man"].speak("Working on it...")
                    content, result = do_tool_agent(
                        chat_model=chat_model,
                        ai_tools=ai_tools,
                        modules=list(local_modules.keys()),
                        env_info=env_info,
                        user_input=question,
                        image=state["context"] if state["context_is_image"] else None,
                        system_prompt=state["system_prompt"],
                        max_iterations=max_iterations,
                        debug=state["debug"],
                        chat_history=chat_history,
                        console=console,
                        use_tts=state["tts"],
                    )
                    chat_history.append(("assistant", content))
                    console_err.print(Panel.fit(Pretty(content), title="[bold]GPT Response", border_style="bold"))
                    if state["tts_man"]:
                        state["tts_man"].speak(summarize_for_tts(content))
                    show_llm_cost(cb.usage_metadata, console=console, show_pricing=PricingDisplay.PRICE)
                state["voice_input_man"].shutdown()
            else:
                ai_tools, local_modules = build_ai_tool_list(
                    question, repl=repl, code_sandbox=code_sandbox, yes_to_all=yes_to_all
                )
                content, result = do_tool_agent(
                    chat_model=chat_model,
                    ai_tools=ai_tools,
                    modules=list(local_modules.keys()),
                    env_info=env_info,
                    user_input=question,
                    image=state["context"] if state["context_is_image"] else None,
                    system_prompt=state["system_prompt"],
                    max_iterations=max_iterations,
                    debug=state["debug"],
                    console=console,
                    use_tts=state["tts"],
                )

                if not sys.stdout.isatty():
                    print(content)

                if state["copy_to_clipboard"]:
                    clipboard.copy(content)
                    console.print("[bold green]Copied to clipboard")

                if state["debug"]:
                    console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

                display_formatted_output(content, state["display_format"], console=console)
                if state["tts_man"]:
                    state["tts_man"].speak(summarize_for_tts(content))

    except Exception as e:
        console.print("[bold red]Error:")
        console.print(str(e), markup=False)
        raise typer.Exit(code=1)


# @app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def aider(
    ctx: typer.Context,
    file_names: Annotated[
        str | None,
        typer.Option(
            "--file-names",
            "-f",
            help="Comma-separated list of edit file paths or glob patterns",
        ),
    ] = None,
    read_names: Annotated[
        str | None,
        typer.Option(
            "--read-names",
            "-r",
            help="Comma-separated list of read only file paths or glob patterns",
        ),
    ] = None,
    main_model: Annotated[
        str | None,
        typer.Option(
            "--main-model",
            "-m",
            envvar=f"{__env_var_prefix__}_AIDER_MAIN_MODEL",
            help="Main model to use for processing. If not specified, a default model will be used.",
        ),
    ] = None,
) -> None:
    """Use Aider code editing assistant."""
    state = ctx.obj
    if not state["user_prompt"] and len(ctx.args) > 0:
        state["user_prompt"] = ctx.args.pop(0)

    question = state["user_prompt"] or state["context"]

    if not question:
        console.print("[bold red]No context or user prompt provided. Exiting...")
        raise typer.Exit(1)

    if not main_model:
        if is_provider_api_key_set(LlmProvider.ANTHROPIC):
            main_model = provider_default_models[LlmProvider.ANTHROPIC]
        elif is_provider_api_key_set(LlmProvider.OPENAI):
            main_model = provider_default_models[LlmProvider.OPENAI]
        elif is_provider_api_key_set(LlmProvider.MISTRAL):
            # main_model = provider_default_models[LlmProvider.MISTRAL]
            main_model = "mistral/codestral-latest"

    if not main_model:
        console.print("[bold red]No main model specified and not default found. Exiting...")
        raise typer.Exit(1)

    # split file globs on comma and resolve paths
    write_files: list[str] = file_names.split(",") if file_names else []
    write_files = [f.strip() for f in write_files if f.strip()]
    if write_files:
        write_files = [f.as_posix() for f in get_file_list_for_context(cast(list[str | Path], write_files))]

    if not write_files:
        console.print("[bold red]No write files specified. Exiting...")
        raise typer.Exit(1)

    # split file globs on comma and resolve paths
    read_files: list[str] = read_names.split(",") if read_names else []
    read_files = [f.strip() for f in read_files if f.strip()]
    if read_files:
        read_files = [f.as_posix() for f in get_file_list_for_context(cast(list[str | Path], read_files))]

    w_flist = "\n".join(write_files)
    r_flist = "\n".join(read_files)
    console_err.print(Panel(f"""Write:\n{w_flist}\nRead:\n{r_flist}""", title="File context", highlight=True))
    if (
        Prompt.ask(
            "Started editing? (y/n): ", choices=["y", "n"], default="y", case_sensitive=False, console=console_err
        )
        != "y"
    ):
        console.print("[bold red]Editing aborted. Exiting...")
        return
    console.print("[bold green]Starting aider...")

    # coder = Coder.create(
    #     main_model=AiderModel(main_model),
    #     io=InputOutput(yes=True),
    #     fnames=write_files,
    #     read_only_fnames=read_files,
    #     auto_commits=False,
    #     suggest_shell_commands=False,
    #     detect_urls=False,
    #     auto_lint=False,
    #     auto_test=False,
    #     ignore_mentions=True,
    # )
    # coder.run(question)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def code_test(
    ctx: typer.Context,
) -> None:
    """Used for experiments. DO NOT RUN"""
    state = ctx.obj
    img = Path("~/.par_gpt/cache/d9bae1270340f598bebe4b5c311c08210ef5cd4a.jpg").expanduser()
    console_err.print(f"Displaying image: {img}", img.exists())
    # show_image_in_terminal(img, "small", console=console)
    show_image_in_terminal(img, "medium", console=console)
    # show_image_in_terminal(img, "large", console=console)
    # show_image_in_terminal(img, "auto", console=console)

    # content = serper_search("axolotl", type="images", max_results=1, scrape=True, include_images=True)[0]["raw_content"].replace("\n", "")
    # console_err.print(content)
    # return
    # md_url_matcher = r"(!\[.*?\]\(.*?\.(?:gif|jpg|jpeg|png|webp).*?\))"
    # md_url_matcher = r'(!\[.*?\]\(https?://[^\s]+?\))'
    # image_matcher = r".+\.(png|gif|jpe?g)"

    # md_links = re.findall(md_url_matcher, content, re.IGNORECASE)
    # md_links = [link for link in md_links if re.match(image_matcher, link, re.IGNORECASE)]
    # console_err.print(md_links)
    # console_err.print(fetch_url_and_convert_to_markdown("https://www.nationalgeographic.com/animals/amphibians/facts/axolotl", include_images=True))
    return
    # from sandbox import SandboxRun
    #
    # runner = SandboxRun(
    #     container_name="par_gpt_sandbox-python_runner-1", console=console_err, start_if_needed=True, verbose=True
    # )
    # code_from_llm = "print('hello, world!')\n"
    # result = runner.copy_file_to_container("hello.py", code_from_llm)
    # console_err.print(result)
    # # result = runner.copy_file_from_container("hello.py", "hello_from_container.py")
    # result = runner.copy_file_from_container("hello.py")
    # console_err.print(result)
    # if result.status and result.data:
    #     # code_from_container = Path(result.message).read_text()
    #     code_from_container = result.data.read().decode()
    #     console_err.print(code_from_llm, code_from_container, code_from_container == code_from_llm)
    # result = runner.execute_code_in_container(code_from_llm)
    # console_err.print(result)
    # console.print(get_file_list_for_context(code_python_file_globs))

    # app_name = "iTerm2"
    # img = capture_window_image(app_name, None, None, ImageCaptureOutputType.BASE64)
    # img = capture_window_image_mac(app_name, None, ImageCaptureOutputType.BASE64)

    chat_model = state["llm_config"].build_chat_model()
    chat_history = []
    default_system_prompt = "<purpose>You are a helpful assistant. Try to be concise and brief unless the user requests otherwise. If an output_instructions section is provided, follow its instructions for output.</purpose>"
    output_format = """<output_instructions>
    <instruction>Your output will be used by TTS please avoid emojis, special characters or other un-pronounceable things.</instruction>
    </output_instructions>
    """
    chat_history.append(
        (
            "system",
            (default_system_prompt).strip() + "\n" + output_format,
        )
    )

    with get_parai_callback(show_tool_calls=state["debug"], show_pricing=PricingDisplay.DETAILS):
        while state["voice_input_man"] is not None:
            prompt = state["voice_input_man"].get_text()
            if not prompt:
                continue
            if prompt.lower().strip() == "exit":
                break
            chat_history.append(("user", prompt))
            content, result = do_single_llm_call(
                chat_model=chat_model,
                user_input=prompt,
                image=None,
                display_format=state["display_format"],
                no_system_prompt=True,
                chat_history=chat_history,
                debug=state["debug"],
                use_tts=state["tts"],
                console=console,
            )
            chat_history.append(("assistant", content))
            console_err.print(Panel.fit(Pretty(content), title="[bold]GPT Response", border_style="bold"))
            if state["tts_man"]:
                state["tts_man"].speak(summarize_for_tts(content))
        if state["voice_input_man"]:
            state["voice_input_man"].shutdown()


if __name__ == "__main__":
    app()
