"""Sandbox command implementation."""

from __future__ import annotations

from typing import Annotated

import typer

from par_gpt.commands.base import BaseCommand
from par_gpt.lazy_import_manager import lazy_import
from sandbox import SandboxAction


class SandboxCommand(BaseCommand):
    """Sandbox management command."""

    def execute(self, ctx: typer.Context, action: SandboxAction) -> None:
        """Execute the sandbox command."""
        # Lazy load sandbox utilities
        install_sandbox = lazy_import("sandbox", "install_sandbox")
        stop_sandbox = lazy_import("sandbox", "stop_sandbox")
        start_sandbox = lazy_import("sandbox", "start_sandbox")

        if action == SandboxAction.BUILD:
            install_sandbox(console=self.console)
        elif action == SandboxAction.STOP:
            stop_sandbox(console=self.console)
        elif action == SandboxAction.START:
            start_sandbox(console=self.console)


def create_sandbox_command():
    """Create and return the sandbox command function for Typer."""
    
    def sandbox_command(
        ctx: typer.Context,
        action: Annotated[
            SandboxAction,
            typer.Option(
                "--action",
                "-a",
                help="Sandbox action to perform.",
            ),
        ],
    ) -> None:
        """Build and run code runner docker sandbox."""
        command = SandboxCommand()
        command.execute(ctx, action)
    
    return sandbox_command