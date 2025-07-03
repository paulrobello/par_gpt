"""Base command class with common patterns for PAR GPT commands."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Any

import typer
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_utils import LazyImportManager

# Create a global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


class BaseCommand(ABC):
    """Base class for PAR GPT commands with common functionality."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize base command."""
        self.console = console or console_err

    def get_user_prompt_from_args(self, state: dict[str, Any], args: list[str]) -> str | None:
        """Extract user prompt from state or command args."""
        if not state.get("user_prompt") and len(args) > 0:
            return args.pop(0)
        return state.get("user_prompt")

    def combine_prompt_and_context(
        self,
        user_prompt: str | None,
        context: str,
        context_is_image: bool = False,
    ) -> str:
        """Combine user prompt and context appropriately."""
        if user_prompt and context and not context_is_image:
            return "\n<context>\n" + context + "\n</context>\n" + user_prompt
        return user_prompt or context or ""

    def validate_question(self, question: str) -> None:
        """Validate that a question/prompt is provided."""
        if not question:
            self.console.print("[bold red]No context or user prompt provided. Exiting...")
            raise typer.Exit(1)

    def build_chat_model_with_timing(self, state: dict[str, Any]) -> Any:
        """Build chat model with timing."""
        from par_utils import timer

        with timer("build_chat_model"):
            return state["llm_config"].build_chat_model()

    def get_provider_callback(self, state: dict[str, Any]) -> Any:
        """Get provider callback for LLM operations."""
        get_parai_callback = lazy_import("par_ai_core.provider_cb_info", "get_parai_callback")
        return get_parai_callback(
            show_end=state["debug"],
            show_tool_calls=state.get("show_tool_calls", state["debug"]),
            show_pricing=state["pricing"],
            verbose=state["debug"],
            console=self.console,
        )

    def mk_env_context(self, extra_context: Any = None) -> str:
        """Create environment context."""
        import os
        import platform
        import sys
        from datetime import UTC, datetime

        context = f"""# Environment Information

**Date**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Platform**: {platform.system()} {platform.release()}
**Python**: {sys.version}
**Working Directory**: {os.getcwd()}

"""
        if isinstance(extra_context, dict):
            for key, value in extra_context.items():
                context += f"**{key}**: {value}\n"
        elif isinstance(extra_context, str):
            context += extra_context
        elif extra_context:
            context += str(extra_context)

        return context

    def handle_output(
        self,
        content: str,
        thinking: str | None,
        result: Any,
        state: dict[str, Any],
    ) -> None:
        """Handle common output processing."""
        # Output to stdout if not a tty
        if not sys.stdout.isatty():
            print(content)

        # Copy to clipboard if requested
        if state["copy_to_clipboard"]:
            clipboard = lazy_import("clipman")
            clipboard.copy(content)
            self.console.print("[bold green]Copied to clipboard")

        # Show debug information
        if state["debug"]:
            Panel = lazy_import("rich.panel", "Panel")
            Pretty = lazy_import("rich.pretty", "Pretty")
            self.console.print(Panel.fit(Pretty(result), title="[bold]GPT Response", border_style="bold"))

        # Show thinking if available
        if thinking and state["display_format"].value != "none":
            Panel = lazy_import("rich.panel", "Panel")
            self.console.print(Panel(thinking, title="thinking", style="cyan"))

        # Display formatted output
        display_formatted_output = lazy_import("par_ai_core.output_utils", "display_formatted_output")
        display_formatted_output(content, state["display_format"], console=self.console)

        # TTS if enabled
        if state.get("tts_man"):
            state["tts_man"].speak(content)

    def show_timing_summary(self, state: dict[str, Any]) -> None:
        """Show timing summary if requested."""
        if state.get("show_times") or state.get("show_times_detailed"):
            from par_utils import show_timing_summary

            show_timing_summary(detailed=state.get("show_times_detailed", False))

    def handle_exception(self, e: Exception, state: dict[str, Any]) -> None:
        """Handle command exceptions consistently."""
        self.console.print("[bold red]Error:")
        self.console.print(str(e), markup=False)

        if state.get("debug"):
            import traceback

            self.console.print(traceback.format_exc())

        raise typer.Exit(code=1)

    @abstractmethod
    def execute(self, ctx: typer.Context) -> None:
        """Execute the command. Must be implemented by subclasses."""
        pass


class LLMCommandMixin:
    """Mixin for commands that use LLM functionality."""

    def do_single_llm_call(
        self,
        chat_model: Any,
        user_input: str,
        state: dict[str, Any],
        system_prompt: str | None = None,
        no_system_prompt: bool = False,
        env_info: str | None = None,
        image: str | None = None,
        chat_history: list[tuple[str, str | list[dict[str, Any]]]] | None = None,
    ) -> tuple[str, str, Any]:
        """Perform a single LLM call with timing."""
        do_single_llm_call = lazy_import("par_gpt.agents", "do_single_llm_call")
        from par_utils import timer

        with timer("llm_invoke"):
            return do_single_llm_call(
                chat_model=chat_model,
                user_input=user_input,
                system_prompt=system_prompt,
                no_system_prompt=no_system_prompt,
                env_info=env_info,
                image=image,
                display_format=state["display_format"],
                debug=state["debug"],
                console=self.console,
                use_tts=state["tts"],
                chat_history=chat_history,
            )


class LoopableCommandMixin:
    """Mixin for commands that support loop modes."""

    def handle_interactive_loop(
        self,
        state: dict[str, Any],
        callback_context: Any,
        chat_history: list[tuple[str, str | list[dict[str, Any]]]] | None = None,
        process_question_func: callable | None = None,
    ) -> None:
        """Handle interactive loop for commands that support it."""
        from par_gpt.cli.options import LoopMode

        question = ""
        while True:
            if state.get("voice_input_man"):
                question = state["voice_input_man"].get_text()
                if not question:
                    continue
                if question.lower() == "exit":
                    return
            else:
                while not question:
                    Prompt = lazy_import("rich.prompt", "Prompt")
                    from par_utils import user_timer

                    with user_timer("user_input_prompt"):
                        question = Prompt.ask("Type 'exit' or press ctrl+c to quit.\nEnter question").strip()
                    if question.lower() == "exit":
                        return

            if process_question_func:
                content, thinking, result = process_question_func(question, state)
            else:
                # Default processing
                content, thinking, result = "", "", None

            self.handle_output(content, thinking, result, state)

            if chat_history is not None:
                chat_history.append(("assistant", content))
                if state.get("history_file"):
                    json = lazy_import("orjson")
                    state["history_file"].write_bytes(json.dumps(chat_history, str, json.OPT_INDENT_2))

            question = ""

            if state["loop_mode"] != LoopMode.INFINITE:
                break

            if state["loop_mode"] == LoopMode.INFINITE:
                show_llm_cost = lazy_import("par_ai_core.pricing_lookup", "show_llm_cost")
                from par_ai_core.pricing_lookup import PricingDisplay

                show_llm_cost(callback_context.usage_metadata, console=self.console, show_pricing=PricingDisplay.PRICE)


class ChatHistoryMixin:
    """Mixin for commands that handle chat history."""

    def load_chat_history(self, state: dict[str, Any]) -> list[tuple[str, str | list[dict[str, Any]]]]:
        """Load chat history from file if available."""
        chat_history = []
        history_file = state.get("history_file")
        if history_file and history_file.is_file():
            json = lazy_import("orjson")
            chat_history = json.loads(history_file.read_bytes() or "[]")
            self.console.print("Loaded chat history from:", history_file)

            # Update system prompt if provided
            if chat_history and chat_history[0][0] == "system":
                if state.get("system_prompt"):
                    chat_history[0][1] = state["system_prompt"]

        return chat_history

    def save_chat_history(
        self,
        chat_history: list[tuple[str, str | list[dict[str, Any]]]],
        state: dict[str, Any],
    ) -> None:
        """Save chat history to file if configured."""
        history_file = state.get("history_file")
        if history_file:
            json = lazy_import("orjson")
            history_file.write_bytes(json.dumps(chat_history, str, json.OPT_INDENT_2))
