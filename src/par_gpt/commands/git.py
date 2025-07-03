"""Git command implementation."""

from __future__ import annotations

import re

import typer

from par_gpt.commands.base import BaseCommand
from par_gpt.lazy_import_manager import lazy_import


class GitCommand(BaseCommand):
    """Git commit helper command."""

    def execute(self, ctx: typer.Context) -> None:
        """Execute the git command."""
        state = ctx.obj

        # Get user prompt from args
        if not state["user_prompt"] and len(ctx.args) > 0:
            state["user_prompt"] = ctx.args.pop(0)

        # Combine prompt and context
        question = self.combine_prompt_and_context(state["user_prompt"], state["context"], state["context_is_image"])

        self.validate_question(question)
        question = question.strip()

        try:
            # Get provider callback
            with self.get_provider_callback(state):
                get_git_repo = lazy_import("par_gpt.repo.repo", "GitRepo")
                repo = get_git_repo()(llm_config=state["llm_config"])

                if not repo.is_dirty():
                    self.console.print("[bold yellow]No changes to commit. Exiting...")
                    return

                # Check if user wants to display or commit
                if re.match(r"(display|show)\s?(git|gen|generate|create|do)? commit", question, flags=re.IGNORECASE):
                    commit_msg = repo.get_commit_message(repo.get_diffs(ctx.args), context=state["context"])
                    self.console.print(commit_msg)
                else:
                    repo.commit(ctx.args, context=state["context"])

        except Exception as e:
            self.handle_exception(e, state)


def create_git_command():
    """Create and return the git command function for Typer."""

    def git_command(ctx: typer.Context) -> None:
        """Git commit helper."""
        command = GitCommand()
        command.execute(ctx)

    return git_command
