"""Generate prompt command implementation."""

from __future__ import annotations

import typer

from par_gpt.commands.base import BaseCommand, LLMCommandMixin
from par_gpt.lazy_import_manager import lazy_import


class GeneratePromptCommand(BaseCommand, LLMCommandMixin):
    """Generate prompt using meta prompting command."""

    def execute(self, ctx: typer.Context) -> None:
        """Execute the generate prompt command."""
        state = ctx.obj

        # Get user prompt from args
        if not state["user_prompt"] and len(ctx.args) > 0:
            state["user_prompt"] = ctx.args.pop(0)

        # Combine prompt and context
        question = self.combine_prompt_and_context(state["user_prompt"], state["context"], state["context_is_image"])

        self.validate_question(question)
        question = question.strip()

        try:
            # Build chat model
            chat_model = self.build_chat_model_with_timing(state)

            # Get provider callback
            with self.get_provider_callback(state) as cb:
                # Execute prompt generation agent
                do_prompt_generation_agent = lazy_import("par_gpt.agents", "do_prompt_generation_agent")
                content, thinking, result = do_prompt_generation_agent(
                    chat_model=chat_model,
                    user_input=question,
                    system_prompt=state["system_prompt"],
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


def create_generate_prompt_command():
    """Create and return the generate prompt command function for Typer."""

    def generate_prompt_command(ctx: typer.Context) -> None:
        """Use meta prompting to generate a new prompt."""
        command = GeneratePromptCommand()
        command.execute(ctx)

    return generate_prompt_command
