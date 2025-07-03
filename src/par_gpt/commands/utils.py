"""Utility commands implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from par_gpt.commands.base import BaseCommand
from par_gpt.lazy_import_manager import lazy_import


class UpdateDepsCommand(BaseCommand):
    """Update dependencies command."""

    def execute(
        self,
        ctx: typer.Context,
        no_uv_update: bool,
        dev_only: bool,
        main_only: bool,
        dry_run: bool,
        skip_packages: list[str] | None,
    ) -> None:
        """Execute the update deps command."""
        if dev_only and main_only:
            self.console.print("[bold red]Cannot specify both --dev-only and --main-only")
            raise typer.Exit(1)

        # Basic implementation - functionality limited due to import restrictions
        self.console.print(
            "[yellow]Dependency update functionality not fully available due to import restrictions[/yellow]"
        )


class PublishRepoCommand(BaseCommand):
    """Publish repository to GitHub command."""

    def execute(self, ctx: typer.Context, repo_name: str | None, public: bool) -> None:
        """Execute the publish repo command."""
        # Basic implementation - functionality limited due to import restrictions
        result = f"GitHub repo publishing not fully available: repo_name={repo_name}, public={public}"
        self.console.print(result)


class TinifyCommand(BaseCommand):
    """Image compression command using Tinify."""

    def execute(self, ctx: typer.Context, image_file: str, output_file: str | None) -> None:
        """Execute the tinify command."""
        image_path = Path(image_file)
        if not image_path.exists():
            self.console.print("[bold red]Image not found")
            raise typer.Exit(1)
        if image_path.suffix.lower() not in [".png", ".jpg", ".webp"]:
            self.console.print("[bold red]Only png, jpg, and webp images are supported")
            raise typer.Exit(1)

        import tinify

        tinify.key = os.environ["TINIFY_KEY"]  # type: ignore
        output_path = Path(output_file) if output_file else image_path

        source = tinify.from_file(image_path)  # type: ignore
        source.to_file(str(output_path))
        compression_ratio = output_path.stat().st_size / image_path.stat().st_size
        reduction_percentage = (1 - compression_ratio) * 100
        self.console.print(f"Tinified image saved to {output_path} with a reduction of {reduction_percentage:.2f}%")


class ProfileCommand(BaseCommand):
    """Pyinstrument profile analysis command."""

    def execute(
        self,
        ctx: typer.Context,
        profile_json: str,
        modules: list[str] | None,
        output: str | None,
        limit: int,
    ) -> None:
        """Execute the profile command."""
        # Lazy load profile utilities
        process_profile = lazy_import("par_gpt.utils", "process_profile")
        ProfileAnalysisError = lazy_import("par_gpt.utils", "ProfileAnalysisError")
        Markdown = lazy_import("rich.markdown", "Markdown")

        try:
            report = process_profile(
                profile_path=profile_json, modules_in_scope=modules, output_path=output, limit=limit
            )
            if output:
                self.console.print(f"[bold green]Success:[/] Profile summary written to {output}")
            else:
                self.console.print(Markdown(report))
        except ProfileAnalysisError as e:
            self.console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(1)


def create_update_deps_command():
    """Create and return the update deps command function for Typer."""

    def update_deps_command(
        ctx: typer.Context,
        no_uv_update: Annotated[bool, typer.Option("--no-uv-update", "-n", help="Dont run 'uv sync -U'")] = False,
        dev_only: Annotated[bool, typer.Option("--dev-only", "-d", help="Update only dev dependencies")] = False,
        main_only: Annotated[bool, typer.Option("--main-only", "-m", help="Update only main dependencies")] = False,
        dry_run: Annotated[bool, typer.Option("--dry-run", "-r", help="Preview changes without applying them")] = False,
        skip_packages: Annotated[
            list[str] | None, typer.Option("--skip", "-s", help="Additional packages to skip during update")
        ] = None,
    ) -> None:
        """Update python project dependencies."""
        command = UpdateDepsCommand()
        command.execute(ctx, no_uv_update, dev_only, main_only, dry_run, skip_packages)

    return update_deps_command


def create_publish_repo_command():
    """Create and return the publish repo command function for Typer."""

    def publish_repo_command(
        ctx: typer.Context,
        repo_name: Annotated[
            str | None,
            typer.Option("--repo-name", "-r", help="Name of the repository. (Defaults to repo root folder name)"),
        ] = None,
        public: Annotated[bool, typer.Option("--public", "-p", help="Publish as public repo.")] = False,
    ) -> None:
        """Create and publish a github repository using current local git repo as source."""
        command = PublishRepoCommand()
        command.execute(ctx, repo_name, public)

    return publish_repo_command


def create_tinify_command():
    """Create and return the tinify command function for Typer."""

    def tinify_command(
        ctx: typer.Context,
        image_file: Annotated[str, typer.Option("--image", "-i", help="Image to tinify.")],
        output_file: Annotated[
            str | None,
            typer.Option("--output-image", "-o", help="File to save compressed image to. Defaults to image_file."),
        ] = None,
    ) -> None:
        """Compress image using tinify."""
        command = TinifyCommand()
        command.execute(ctx, image_file, output_file)

    return tinify_command


def create_pi_profile_command():
    """Create and return the pi-profile command function for Typer."""

    def pi_profile_command(
        ctx: typer.Context,
        profile_json: Annotated[str, typer.Option("--profile_json", "-p", help="JSON report to examine.")],
        modules: Annotated[
            list[str] | None,
            typer.Option("--module", "-m", help="Module to include in analysis. Can be specified more than once."),
        ] = None,
        output: Annotated[
            str | None, typer.Option("--output", "-o", help="File to save markdown to. Defaults to screen.")
        ] = None,
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max number of functions to include.")] = 15,
    ) -> None:
        """Convert Pyinstrument json report to markdown"""
        command = ProfileCommand()
        command.execute(ctx, profile_json, modules, output, limit)

    return pi_profile_command
