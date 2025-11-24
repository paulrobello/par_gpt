"""Agent command implementation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

import typer

from par_gpt import __env_var_prefix__
from par_gpt.cli.options import AGENT_OPTION_DEFAULTS
from par_gpt.commands.base import BaseCommand, ChatHistoryMixin, LoopableCommandMixin
from par_utils import LazyImportManager

# Create a global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


class AgentCommand(BaseCommand, LoopableCommandMixin, ChatHistoryMixin):
    """Full agent with dynamic tools."""

    def execute(
        self, ctx: typer.Context, max_iterations: int, show_tool_calls: bool, repl: bool, code_sandbox: bool
    ) -> None:
        """Execute the agent command."""
        state = ctx.obj

        # Get user prompt from args
        if not state["user_prompt"] and len(ctx.args) > 0:
            state["user_prompt"] = ctx.args.pop(0)

        # Load chat history
        chat_history = self.load_chat_history(state)

        # Combine prompt and context
        question = self.combine_prompt_and_context(state["user_prompt"], state["context"], state["context_is_image"])

        try:
            # Build chat model with timing
            chat_model = self.build_chat_model_with_timing(state)
            env_info = self.mk_env_context({})

            # Get provider callback
            with self.get_provider_callback(state) as cb:
                self._process_agent_interaction(
                    chat_model,
                    question,
                    env_info,
                    chat_history,
                    state,
                    cb,
                    max_iterations,
                    show_tool_calls,
                    repl,
                    code_sandbox,
                )

        except Exception as e:
            self.handle_exception(e, state)
        finally:
            # Show timing information if requested
            self.show_timing_summary(state)

    def _process_agent_interaction(
        self,
        chat_model,
        question: str,
        env_info: str,
        chat_history: list,
        state: dict,
        callback_context,
        max_iterations: int,
        show_tool_calls: bool,
        repl: bool,
        code_sandbox: bool,
    ) -> None:
        """Process the agent interaction loop."""

        def process_question(q: str, s: dict) -> tuple[str, str, Any]:
            """Process a single question with agent tools."""
            # Build AI tool list based on question keywords
            build_ai_tool_list = lazy_import("par_gpt.lazy_tool_loader", "build_ai_tool_list")
            ai_tools, local_modules = build_ai_tool_list(
                q,
                repl=repl,
                code_sandbox=code_sandbox,
                yes_to_all=s["yes_to_all"],
                enable_redis=s["enable_redis"],
            )

            # Set tool context for AI tools to access global state
            from par_gpt.tool_context import set_tool_context

            set_tool_context(yes_to_all=s["yes_to_all"])

            # Execute agent with tools
            do_tool_agent = lazy_import("par_gpt.agents", "do_tool_agent")
            content, result = do_tool_agent(
                chat_model=chat_model,
                ai_tools=ai_tools,
                modules=list(local_modules.keys()),
                env_info=env_info,
                user_input=q,
                image=s["context"] if s["context_is_image"] else None,
                system_prompt=s["system_prompt"],
                max_iterations=max_iterations,
                debug=s["debug"],
                chat_history=chat_history,
                console=self.console,
            )

            # Add to chat history and save
            chat_history.append(("assistant", content))
            self.save_chat_history(chat_history, s)

            return content, "", result  # Agent doesn't return thinking separately

        # Handle regular interaction
        if question:
                # Process initial question
                content, thinking, result = process_question(question, state)
                self.handle_output(content, thinking, result, state)

                # Continue with loop if needed
                from par_gpt.cli.options import LoopMode

                if state["loop_mode"] == LoopMode.INFINITE:
                    self.handle_interactive_loop(state, callback_context, chat_history, process_question)
        else:
            # Start with interactive loop
            self.handle_interactive_loop(state, callback_context, chat_history, process_question)


def create_agent_command():
    """Create and return the agent command function for Typer."""

    def agent_command(
        ctx: typer.Context,
        max_iterations: Annotated[
            int,
            typer.Option(
                "--max-iterations",
                "-i",
                envvar=f"{__env_var_prefix__}_MAX_ITERATIONS",
                help="Maximum number of iterations to run when in agent mode.",
            ),
        ] = AGENT_OPTION_DEFAULTS["max_iterations"],
        show_tool_calls: Annotated[
            bool,
            typer.Option(
                "--show-tool-calls",
                "-T",
                envvar=f"{__env_var_prefix__}_SHOW_TOOL_CALLS",
                help="Show tool calls",
            ),
        ] = AGENT_OPTION_DEFAULTS["show_tool_calls"],
        repl: Annotated[
            bool,
            typer.Option(
                "--repl",
                envvar=f"{__env_var_prefix__}_REPL",
                help="⚠️  DANGER: Enable REPL tool for code execution on HOST SYSTEM. This allows AI to write and execute arbitrary code with your user permissions. Only use if you understand the security risks.",
            ),
        ] = AGENT_OPTION_DEFAULTS["repl"],
        code_sandbox: Annotated[
            bool,
            typer.Option(
                "--code-sandbox",
                "-c",
                envvar=f"{__env_var_prefix__}_CODE_SANDBOX",
                help="Enable code sandbox tool. Requires a running code sandbox container.",
            ),
        ] = AGENT_OPTION_DEFAULTS["code_sandbox"],
    ) -> None:
        """Full agent with dynamic tools."""
        command = AgentCommand()
        command.execute(ctx, max_iterations, show_tool_calls, repl, code_sandbox)

    return agent_command
