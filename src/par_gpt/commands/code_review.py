"""Code review command implementation."""

from __future__ import annotations

import typer

from par_gpt.commands.base import BaseCommand, LLMCommandMixin
from par_utils import LazyImportManager

# Create a global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


class CodeReviewCommand(BaseCommand, LLMCommandMixin):
    """Code review command."""

    def execute(self, ctx: typer.Context) -> None:
        """Execute the code review command."""
        state = ctx.obj

        # Get user prompt from args
        if not state["user_prompt"] and len(ctx.args) > 0:
            state["user_prompt"] = ctx.args.pop(0)

        # Default question if none provided
        question = state["user_prompt"] or state["context"] or "Please review code"

        # Combine prompt and context
        question = self.combine_prompt_and_context(question, state["context"], state["context_is_image"]).strip()

        try:
            # Build chat model
            chat_model = self.build_chat_model_with_timing(state)
            env_info = self.mk_env_context({})

            # Get provider callback
            with self.get_provider_callback(state) as cb:
                # Execute code review agent
                do_code_review_agent = lazy_import("par_gpt.agents", "do_code_review_agent")
                content, thinking, result = do_code_review_agent(
                    chat_model=chat_model,
                    user_input=question,
                    system_prompt=state["system_prompt"],
                    env_info=env_info,
                    display_format=state["display_format"],
                    debug=state["debug"],
                    console=self.console,
                )

                # Handle output
                self.handle_output(content, thinking, result, state)

                # Show cost information
                show_llm_cost = lazy_import("par_ai_core.pricing_lookup", "show_llm_cost")
                show_llm_cost(cb.usage_metadata, console=self.console, show_pricing=state["pricing"])

        except Exception as e:
            self.handle_exception(e, state)


def create_code_review_command():
    """Create and return the code review command function for Typer."""

    def code_review_command(ctx: typer.Context) -> None:
        """Review code."""
        command = CodeReviewCommand()
        command.execute(ctx)

    return code_review_command
