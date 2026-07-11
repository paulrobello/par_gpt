"""Environment context generation utilities."""

from __future__ import annotations

import getpass
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_utils import PathSecurityError, validate_relative_path


def mk_env_context(extra_context: dict[str, Any] | str | Path | None = None, console: Console | None = None) -> str:
    """
    Create environment context with optional extra context.

    Args:
        extra_context: Optional extra context to add to the context
            Path will be read and parsed as JSON with fallback to plain text
            Dictionary will append / overwrite existing context
            String will be appended as-is
        console: Optional console to use

    Returns:
        str: The environment context as Markdown string
    """

    if not console:
        console = console_err

    if extra_context is None:
        extra_context = {}

    extra_context_text = ""

    if isinstance(extra_context, Path):
        # Validate the path for security
        try:
            extra_context_str = str(extra_context)
            # Check for path traversal attempts
            if "../" in extra_context_str or "..\\" in extra_context_str:
                raise PathSecurityError("Path traversal detected in extra context path")
            # For relative paths, validate them
            if not extra_context.is_absolute():
                validate_relative_path(extra_context_str, max_depth=5)
        except PathSecurityError as e:
            console.print(f"[red]Security error: {e}[/red]")
            raise ValueError(f"Invalid extra context path: {e}") from e

        if not extra_context.is_file():
            raise ValueError(f"Extra context file not found or is not a file: {extra_context}")
        try:
            extra_context = orjson.loads(extra_context.read_text(encoding="utf-8"))
        except Exception as _:
            extra_context = extra_context.read_text(encoding="utf-8").strip()

    if isinstance(extra_context, dict):
        for k, v in extra_context.items():
            extra_context[k] = str(v)
    elif isinstance(extra_context, (str | list)):
        extra_context_text = str(extra_context)
        extra_context = {}

    extra_context_text = "\n" + extra_context_text.strip()

    if not console:
        console = Console(stderr=True)

    return (
        (
            "<extra_context>\n"
            + "\n".join(
                [
                    f"<{k}>{v}</{k}>"
                    for k, v in (
                        {
                            "username": getpass.getuser(),
                            "home_directory": Path("~").expanduser().as_posix(),
                            "current_directory": Path(os.getcwd()).expanduser().as_posix(),
                            "current_date_and_time": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "platform": platform.platform(aliased=True, terse=True),
                            "shell": Path(os.environ.get("SHELL", "bash")).stem,
                            "term": os.environ.get("TERM", "xterm-256color"),
                            "terminal_dimensions": f"{console.width}x{console.height}",
                        }
                        | extra_context
                    ).items()  # type: ignore
                ]
            )
            + "\n"
        )
        + extra_context_text
        + "\n</extra_context>\n"
    )
