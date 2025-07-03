"""LLM command implementation."""

from __future__ import annotations

import typer

from par_gpt.commands.base import BaseCommand, ChatHistoryMixin, LLMCommandMixin, LoopableCommandMixin


class LLMCommand(BaseCommand, LLMCommandMixin, LoopableCommandMixin, ChatHistoryMixin):
    """Basic LLM mode with no tools."""

    def execute(self, ctx: typer.Context) -> None:
        """Execute the LLM command."""
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
                self._process_llm_interaction(chat_model, question, env_info, chat_history, state, cb)

        except Exception as e:
            self.handle_exception(e, state)
        finally:
            # Show timing information if requested
            self.show_timing_summary(state)

    def _process_llm_interaction(
        self,
        chat_model,
        question: str,
        env_info: str,
        chat_history: list,
        state: dict,
        callback_context,
    ) -> None:
        """Process the LLM interaction loop."""

        def process_question(q: str, s: dict) -> tuple[str, str, any]:
            """Process a single question."""
            content, thinking, result = self.do_single_llm_call(
                chat_model=chat_model,
                user_input=q,
                state=s,
                system_prompt=s["system_prompt"],
                no_system_prompt=(chat_model.name is not None and chat_model.name[:2] in ["o1", "o3"])
                or (len(chat_history) > 0 and chat_history[0][0] == "system"),
                env_info=env_info,
                image=s["context"] if s["context_is_image"] else None,
                chat_history=chat_history,
            )

            # Add to chat history
            chat_history.append(("assistant", content))
            self.save_chat_history(chat_history, s)

            return content, thinking, result

        # Handle the interactive loop
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


def create_llm_command():
    """Create and return the LLM command function for Typer."""

    def llm_command(ctx: typer.Context) -> None:
        """Basic LLM mode with no tools."""
        command = LLMCommand()
        command.execute(ctx)

    return llm_command
