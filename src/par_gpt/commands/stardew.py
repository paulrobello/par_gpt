"""Stardew pixel art generation command implementation."""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from typing import Annotated

import typer

from par_gpt import __env_var_prefix__
from par_gpt.commands.base import BaseCommand
from par_gpt.lazy_import_manager import lazy_import
from par_gpt.utils.path_security import PathSecurityError


class StardewCommand(BaseCommand):
    """Generate pixel art avatar variation command."""

    def execute(
        self,
        ctx: typer.Context,
        prompt: str,
        system_prompt: str,
        src: Path | None,
        out_folder: Path | None,
        out: str | None,
        display: bool,
    ) -> None:
        """Execute the stardew command."""
        state = ctx.obj
        DEFAULT_SRC: Path = Path(__file__).parent.parent / "img" / "stardew-image-base.jpeg"

        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise typer.BadParameter("OPENAI_API_KEY environment variable not set")

        try:
            client = OpenAI(api_key=api_key)

            # Determine source image path
            src_path = src if src else DEFAULT_SRC
            if not src_path.exists():
                raise typer.BadParameter(f"Source image not found: {src_path}")

            # Build the AI prompt
            ai_prompt = system_prompt.format(user_prompt=prompt)
            if state["debug"]:
                self.console.print(ai_prompt)

            image_file = src_path.open("rb")

            try:
                self.console.print("[bold green]Generating image, this can take up to a minute...[/bold green]")
                # Call the image edit API
                response = client.images.edit(
                    model="gpt-image-1",
                    image=image_file,
                    prompt=ai_prompt,
                    size="1024x1024",
                    quality="auto",
                )
            finally:
                image_file.close()

            if state["debug"]:
                Pretty = lazy_import("rich.pretty", "Pretty")
                self.console.print(Pretty(response))

            if not response.data or not len(response.data) or not response.data[0].b64_json:
                raise ValueError("no b64_json in response")

            image_base64 = response.data[0].b64_json
            img_data = base64.b64decode(image_base64)

            # Determine output file name with security validation
            out_path = self._get_safe_output_path(out, prompt, out_folder)

            # Write the image file
            with out_path.open("wb") as f:
                f.write(img_data)

            self.console.print(f"[bold green]Image saved to {out_path}[/bold green]")

            # Display in terminal if requested
            if display:
                from rich_pixels import Pixels

                dim: int = min(self.console.width, self.console.height * 2 - 5)
                pixels = Pixels.from_image_path(out_path, (dim, dim))  # type: ignore[call-arg]
                self.console.print(pixels)

        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {e}")
            if state["debug"]:
                import traceback
                self.console.print(traceback.format_exc())
            raise typer.Exit(code=1)

    def _get_safe_output_path(self, out: str | None, prompt: str, out_folder: Path | None) -> Path:
        """Get safe output path with security validation."""
        # Lazy load path security utilities
        sanitize_filename = lazy_import("par_gpt.utils.path_security", "sanitize_filename")
        validate_relative_path = lazy_import("par_gpt.utils.path_security", "validate_relative_path")
        validate_within_base = lazy_import("par_gpt.utils.path_security", "validate_within_base")

        if out:
            try:
                # Validate the output path for security
                if "../" in out or "..\\" in out:
                    self.console.print("[red]Error: Path traversal detected in output path[/red]")
                    raise typer.Exit(1)

                # Sanitize the filename
                safe_out = sanitize_filename(out)
                out_path = Path(safe_out)

                # For relative paths, validate them
                if not out_path.is_absolute():
                    validate_relative_path(str(out_path), max_depth=3)

            except PathSecurityError as e:
                self.console.print(f"[red]Error: Invalid output path: {e}[/red]")
                raise typer.Exit(1) from e
        else:
            safe_name = re.sub(r"[^a-z0-9_]", "_", prompt.lower())
            out_path = Path(f"{safe_name}.png")

        # Validate the final output path if using out_folder
        if out_folder and not out_path.is_absolute():
            try:
                # Ensure the output path stays within the specified folder
                out_path = validate_within_base(out_path, out_folder)
            except PathSecurityError as e:
                self.console.print(f"[red]Error: Output path escapes designated folder: {e}[/red]")
                raise typer.Exit(1) from e

        return out_path


def create_stardew_command():
    """Create and return the stardew command function for Typer."""
    
    def stardew_command(
        ctx: typer.Context,
        prompt: Annotated[str, typer.Option(..., "-p", "--prompt", help="User request for avatar variation.")],
        system_prompt: Annotated[
            str,
            typer.Option(
                "-S", "--system-prompt", 
                envvar=f"{__env_var_prefix__}_SD_SYSTEM_PROMPT", 
                help="System prompt to use"
            ),
        ] = "Make this character {user_prompt}. ensure you maintain the pixel art style.",
        src: Annotated[
            Path | None,
            typer.Option(
                "-s", "--src", 
                envvar=f"{__env_var_prefix__}_SD_SRC_IMAGE", 
                help="Source image to use as reference."
            ),
        ] = None,
        out_folder: Annotated[
            Path | None,
            typer.Option(
                "-O", "--out-folder", 
                envvar=f"{__env_var_prefix__}_SD_OUT_FOLDER", 
                help="Output folder for generated images."
            ),
        ] = None,
        out: Annotated[str | None, typer.Option("-o", "--out", help="Output image name.")] = None,
        display: Annotated[
            bool,
            typer.Option(
                "-d", "--display", 
                envvar=f"{__env_var_prefix__}_SD_DISPLAY_IMAGE", 
                help="Display resulting image in the terminal."
            ),
        ] = False,
    ) -> None:
        """Generate pixel art avatar variation."""
        command = StardewCommand()
        command.execute(ctx, prompt, system_prompt, src, out_folder, out, display)
    
    return stardew_command