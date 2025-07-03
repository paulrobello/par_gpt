"""Security validation utilities for PAR GPT CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_gpt.utils.path_security import (
    PathSecurityError,
    sanitize_filename,
    validate_relative_path,
    validate_within_base,
)


def validate_context_path_security(context_location: str, console: Console | None = None) -> None:
    """Validate context location for path traversal attacks."""
    if console is None:
        console = console_err

    if not context_location or context_location.startswith("http") or "\n" in context_location:
        return

    try:
        # Check for path traversal attempts
        if "../" in context_location or "..\\" in context_location:
            console.print("[red]Error: Path traversal detected in context location[/red]")
            raise typer.Exit(1)

        # For relative paths, validate them
        if not Path(context_location).is_absolute():
            validate_relative_path(context_location, max_depth=5)

    except PathSecurityError as e:
        console.print(f"[red]Error: Invalid context path: {e}[/red]")
        raise typer.Exit(1) from e


def validate_chat_history_path_security(chat_history: str, console: Console | None = None) -> Path:
    """Validate chat history path for security and return safe Path object."""
    if console is None:
        console = console_err

    try:
        # Sanitize the filename to prevent dangerous characters
        safe_history_name = sanitize_filename(chat_history)

        # Check for path traversal in the original input
        if "../" in chat_history or "..\\" in chat_history:
            console.print("[red]Error: Path traversal detected in chat history path[/red]")
            raise typer.Exit(1)

        # For absolute paths starting with . or /, validate them
        if chat_history[0] in [".", "/"]:
            # Validate relative paths
            if not chat_history.startswith("/"):
                validate_relative_path(chat_history, max_depth=3)
            history_file = Path(chat_history)
        else:
            # For non-path-like names, treat as filename in current directory
            # Use the sanitized version for safety
            history_file = (Path(".") / safe_history_name).resolve()

        return history_file

    except PathSecurityError as e:
        console.print(f"[red]Error: Invalid chat history path: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error processing chat history path: {e}[/red]")
        raise typer.Exit(1) from e


def validate_output_path_security(
    output_path: str,
    output_folder: Path | None = None,
    console: Console | None = None,
) -> Path:
    """Validate output path for security and return safe Path object."""
    if console is None:
        console = console_err

    try:
        # Validate the output path for security
        if "../" in output_path or "..\\" in output_path:
            console.print("[red]Error: Path traversal detected in output path[/red]")
            raise typer.Exit(1)

        # Sanitize the filename
        safe_output = sanitize_filename(output_path)
        path_obj = Path(safe_output)

        # For relative paths, validate them
        if not path_obj.is_absolute():
            validate_relative_path(str(path_obj), max_depth=3)

        # Validate the final output path if using output_folder
        if output_folder and not path_obj.is_absolute():
            path_obj = validate_within_base(path_obj, output_folder)

        return path_obj

    except PathSecurityError as e:
        console.print(f"[red]Error: Invalid output path: {e}[/red]")
        raise typer.Exit(1) from e


def check_mutual_exclusivity(
    copy_from_clipboard: bool,
    context_location: str,
    console: Console | None = None,
) -> None:
    """Check for mutually exclusive options."""
    if console is None:
        console = console_err

    if copy_from_clipboard and context_location:
        console.print("[bold red]copy_from_clipboard and context_location are mutually exclusive. Exiting...")
        raise typer.Exit(1)
