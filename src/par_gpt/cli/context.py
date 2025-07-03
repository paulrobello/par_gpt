"""Context processing logic for PAR GPT CLI."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from typing import Any

import typer
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_utils import LazyImportManager, PathSecurityError

# Create a global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


class ContextProcessor:
    """Handles context processing from various sources."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize context processor."""
        self.console = console or console_err

    def process_clipboard(self, copy_from_clipboard: bool, context_location: str) -> str:
        """Process clipboard content if requested."""
        if copy_from_clipboard and context_location:
            self.console.print("[bold red]copy_from_clipboard and context_location are mutually exclusive. Exiting...")
            raise typer.Exit(1)

        if copy_from_clipboard:
            # Lazy load clipboard functionality
            clipboard = lazy_import("clipman")
            cv = clipboard.paste()
            if not cv:
                self.console.print("[bold red]Failed to copy from clipboard. Exiting...")
                raise typer.Exit(1)
            context_location = cv
            self.console.print("[bold green]Context copied from clipboard")

        return context_location

    def validate_context_location(self, context_location: str) -> tuple[bool, bool]:
        """Validate context location and return (is_url, is_file) flags."""
        context_is_url: bool = context_location.startswith("http")
        if context_is_url:
            self.console.print("[bold green]Context is URL and will be fetched...")
            return True, False

        # Validate context_location for path traversal before checking if it's a file
        context_is_file: bool = False
        if not context_is_url and "\n" not in context_location:
            try:
                # Check for path traversal attempts
                if "../" in context_location or "..\\" in context_location:
                    self.console.print("[red]Error: Path traversal detected in context location[/red]")
                    raise typer.Exit(1)
                # For relative paths, validate them
                if not Path(context_location).is_absolute():
                    # Lazy load path security functions
                    validate_relative_path = lazy_import("par_gpt.utils.path_security", "validate_relative_path")
                    validate_relative_path(context_location, max_depth=5)
                context_is_file = Path(context_location).is_file()
            except PathSecurityError as e:
                self.console.print(f"[red]Error: Invalid context path: {e}[/red]")
                raise typer.Exit(1) from e

        if context_is_file:
            self.console.print("[bold green]Context is file and will be read...")

        if context_location and not context_is_url and not context_is_file:
            self.console.print(f"[bold red]Context source '{context_location}' not found. Exiting...")
            raise typer.Exit(1)

        return context_is_url, context_is_file

    def process_stdin(self, context_location: str, copy_from_clipboard: bool) -> str:
        """Process stdin content if available."""
        context: str = ""
        if copy_from_clipboard and not self.validate_context_location(context_location)[0]:  # not URL
            context = context_location
            return context

        sio_all: StringIO = StringIO()
        # Lazy load stdin utilities
        has_stdin_content = lazy_import("par_ai_core.utils", "has_stdin_content")
        if not context_location and not copy_from_clipboard and has_stdin_content():
            self.console.print("[bold green]Context is stdin and will be read...")
            for line in sys.stdin:
                sio_all.write(line)
            context = sio_all.getvalue().strip()

        return context

    def process_context_content(
        self,
        context_location: str,
        context_is_url: bool,
        context_is_file: bool,
        show_times: bool = False,
        show_times_detailed: bool = False,
    ) -> tuple[str, bool]:
        """Process context content from URL or file and return (content, is_image)."""
        context = ""
        context_is_image = False

        if not context_location:
            return context, context_is_image

        self.console.print("[bold green]Detecting if context is an image...")

        # Helper function to show image in terminal
        def show_image_in_terminal_helper(image_path: Path) -> None:
            """Basic image display - functionality limited due to import restrictions."""
            self.console.print(f"[dim]Image at: {image_path}[/dim]")

        from par_utils import timer

        with timer("context_processing"):
            context, context_is_image = self._process_content_core(
                context_location, context_is_url, context_is_file, show_image_in_terminal_helper
            )

        return context, context_is_image

    def _process_content_core(
        self,
        context_location: str,
        context_is_url: bool,
        context_is_file: bool,
        show_image_helper: Any,
    ) -> tuple[str, bool]:
        """Core content processing logic."""
        context = ""
        context_is_image = False

        if context_is_url:
            try:
                # Lazy load image utilities
                try_get_image_type = lazy_import("par_ai_core.llm_image_utils", "try_get_image_type")
                image_to_base64 = lazy_import("par_ai_core.llm_image_utils", "image_to_base64")
                UnsupportedImageTypeError = lazy_import("par_ai_core.llm_image_utils", "UnsupportedImageTypeError")
                from par_utils import CacheManager

                cache_manager = CacheManager()

                image_type = try_get_image_type(context_location)
                self.console.print(f"[bold green]Image type {image_type} detected.")
                image_path = cache_manager.download(context_location)
                context = image_to_base64(image_path.read_bytes(), image_type)
                context_is_image = True
                show_image_helper(image_path)
            except UnsupportedImageTypeError:
                # Lazy load web utilities
                fetch_url_and_convert_to_markdown = lazy_import(
                    "par_ai_core.web_tools", "fetch_url_and_convert_to_markdown"
                )
                context = fetch_url_and_convert_to_markdown(context_location)[0].strip()
        else:
            try:
                # Lazy load image utilities
                try_get_image_type = lazy_import("par_ai_core.llm_image_utils", "try_get_image_type")
                image_to_base64 = lazy_import("par_ai_core.llm_image_utils", "image_to_base64")
                UnsupportedImageTypeError = lazy_import("par_ai_core.llm_image_utils", "UnsupportedImageTypeError")

                image_type = try_get_image_type(context_location)
                self.console.print(f"[bold green]Image type {image_type} detected.")
                image_path = Path(context_location)
                context = image_to_base64(image_path.read_bytes(), image_type)
                context_is_image = True
                show_image_helper(image_path)
            except UnsupportedImageTypeError:
                context = Path(context_location).read_text(encoding="utf-8").strip()

        return context, context_is_image

    def validate_chat_history_path(self, chat_history: str | None) -> Path | None:
        """Validate and process chat history path."""
        if not chat_history:
            return None

        from par_gpt.utils.path_security import sanitize_filename, validate_relative_path

        try:
            # Sanitize the filename to prevent dangerous characters
            safe_history_name = sanitize_filename(chat_history)

            # Check for path traversal in the original input
            if "../" in chat_history or "..\\" in chat_history:
                self.console.print("[red]Error: Path traversal detected in chat history path[/red]")
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
            self.console.print(f"[red]Error: Invalid chat history path: {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            self.console.print(f"[red]Error processing chat history path: {e}[/red]")
            raise typer.Exit(1) from e

    def combine_user_prompt_and_context(
        self,
        user_prompt: str | None,
        context: str,
        context_is_image: bool,
    ) -> str:
        """Combine user prompt with context appropriately."""
        if user_prompt and context and not context_is_image:
            return "\n<context>\n" + context + "\n</context>\n" + user_prompt
        return user_prompt or context or ""
