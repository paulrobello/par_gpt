"""Simple command implementations."""

from __future__ import annotations

from typing import Any, cast

import typer

from par_gpt.commands.base import BaseCommand


class ShowEnvCommand(BaseCommand):
    """Show environment context command."""

    def execute(self, ctx: typer.Context) -> None:
        """Execute the show-env command."""
        self.console.print(self.mk_env_context())


def create_show_env_command():
    """Create and return the show-env command function for Typer."""

    def show_env() -> None:
        """Show environment context."""
        command = ShowEnvCommand()

        # Create a minimal context for this command
        class FakeContext:
            obj: dict[str, Any] = {}

        command.execute(cast(typer.Context, FakeContext()))

    return show_env
