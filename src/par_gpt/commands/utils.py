"""Utility commands implementation."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from par_gpt.commands.base import BaseCommand
from par_utils import LazyImportManager

# Create a global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def lazy_import(module_path: str, item_name: str | None = None):
    """Backward compatibility function for lazy imports."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


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

        # Import the actual implementation from utils
        try:
            update_pyproject_deps = lazy_import("par_gpt.utils", "update_pyproject_deps")

            # Call the actual implementation
            update_pyproject_deps(
                do_uv_update=not no_uv_update,
                console=self.console,
                dev_only=dev_only,
                main_only=main_only,
                dry_run=dry_run,
                skip_packages=skip_packages,
            )
        except ImportError as e:
            self.console.print(f"[bold red]Import error: {e}")
            self.console.print("[yellow]Falling back to manual dependency update...")
            self.console.print("[cyan]Please run: make depsupdate")
            raise typer.Exit(1)
        except Exception as e:
            self.console.print(f"[bold red]Error updating dependencies: {e}")
            raise typer.Exit(1)


class PublishRepoCommand(BaseCommand):
    """Publish repository to GitHub command."""

    def execute(self, ctx: typer.Context, repo_name: str | None, public: bool) -> None:
        """Execute the publish repo command."""
        # Import the actual implementation from utils
        try:
            github_publish_repo = lazy_import("par_gpt.utils", "github_publish_repo")

            # Call the actual implementation
            result = github_publish_repo(repo_name=repo_name, public=public)
            self.console.print(result)
        except ImportError as e:
            self.console.print(f"[bold red]Import error: {e}")
            self.console.print("[yellow]GitHub publishing functionality not available...")
            self.console.print("[cyan]Please check your GitHub configuration and credentials")
            raise typer.Exit(1)
        except Exception as e:
            self.console.print(f"[bold red]Error publishing to GitHub: {e}")
            raise typer.Exit(1)


class TinifyCommand(BaseCommand):
    """Image compression command using Tinify."""

    def _compress_single_image(self, image_path: Path, output_path: Path | None = None) -> tuple[Path, float]:
        """Compress a single image and return output path and reduction percentage.

        Args:
            image_path: Path to the image to compress.
            output_path: Optional path to save compressed image. If None, compresses in-place.

        Returns:
            Tuple of (output_path, reduction_percentage).
        """
        import tinify

        # Store original file size before any compression
        original_size = image_path.stat().st_size

        # Handle in-place vs separate output file compression
        if output_path:
            # Direct compression to specified output file
            source = tinify.from_file(str(image_path))  # type: ignore
            source.to_file(str(output_path))
            compressed_size = output_path.stat().st_size
            final_output_path = output_path
        else:
            # In-place compression using temporary file
            with tempfile.NamedTemporaryFile(suffix=image_path.suffix, delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                source = tinify.from_file(str(image_path))  # type: ignore
                source.to_file(str(temp_path))
                compressed_size = temp_path.stat().st_size

                # Replace original file with compressed version
                temp_path.replace(image_path)
                final_output_path = image_path
            finally:
                # Clean up temp file if it still exists
                if temp_path.exists():
                    temp_path.unlink()

        # Calculate reduction percentage using original size
        compression_ratio = compressed_size / original_size
        reduction_percentage = (1 - compression_ratio) * 100

        return final_output_path, reduction_percentage

    def execute(
        self,
        ctx: typer.Context,
        image_file: str | None,
        output_file: str | None,
        pattern: str | None,
        output_dir: str | None,
    ) -> None:
        """Execute the tinify command."""
        # Validate mutually exclusive options
        if image_file and pattern:
            self.console.print("[bold red]Cannot specify both --image and --pattern")
            raise typer.Exit(1)

        if not image_file and not pattern:
            self.console.print("[bold red]Must specify either --image or --pattern")
            raise typer.Exit(1)

        if pattern and output_file:
            self.console.print("[bold red]Cannot use --output-image with --pattern. Use --output-dir instead.")
            raise typer.Exit(1)

        import tinify

        # Validate API key
        try:
            tinify.key = os.environ["TINIFY_KEY"]  # type: ignore
        except KeyError:
            self.console.print("[bold red]TINIFY_KEY environment variable not set")
            raise typer.Exit(1)

        # Pattern mode: process multiple files
        if pattern:
            # Find all matching files
            matching_files = list(Path.cwd().glob(pattern))

            # Filter for supported image types
            supported_extensions = {".png", ".jpg", ".jpeg", ".webp"}
            image_files = [f for f in matching_files if f.is_file() and f.suffix.lower() in supported_extensions]

            if not image_files:
                self.console.print(f"[bold yellow]No images found matching pattern: {pattern}")
                raise typer.Exit(0)

            # Validate or create output directory if specified
            out_dir: Path | None = None
            if output_dir:
                out_dir = Path(output_dir)
                if not out_dir.exists():
                    out_dir.mkdir(parents=True, exist_ok=True)
                    self.console.print(f"[cyan]Created output directory: {out_dir}")

            self.console.print(f"[cyan]Found {len(image_files)} image(s) matching pattern: {pattern}")

            # Process all matching images
            total_original_size = 0
            total_compressed_size = 0
            successful = 0
            failed = 0

            for img_path in image_files:
                try:
                    original_size = img_path.stat().st_size
                    total_original_size += original_size

                    # Determine output path
                    if out_dir:
                        output_path = out_dir / img_path.name
                    else:
                        output_path = None  # In-place compression

                    # Compress the image
                    final_output_path, reduction_pct = self._compress_single_image(img_path, output_path)

                    compressed_size = final_output_path.stat().st_size
                    total_compressed_size += compressed_size

                    self.console.print(
                        f"[green]✓[/green] {img_path.name}: {reduction_pct:.2f}% reduction "
                        f"({original_size:,} → {compressed_size:,} bytes)"
                    )
                    successful += 1

                except Exception as e:
                    self.console.print(f"[red]✗[/red] {img_path.name}: {e}")
                    failed += 1

            # Print summary
            self.console.print("\n[bold cyan]Summary:[/bold cyan]")
            self.console.print(f"  Total files processed: {successful + failed}")
            self.console.print(f"  Successful: [green]{successful}[/green]")
            if failed > 0:
                self.console.print(f"  Failed: [red]{failed}[/red]")

            if total_original_size > 0:
                total_reduction_pct = (1 - total_compressed_size / total_original_size) * 100
                self.console.print(
                    f"  Total size: {total_original_size:,} → {total_compressed_size:,} bytes "
                    f"({total_reduction_pct:.2f}% reduction)"
                )

            if failed > 0:
                raise typer.Exit(1)

        # Single file mode
        else:
            assert image_file is not None  # For type checker
            image_path = Path(image_file)
            if not image_path.exists():
                self.console.print("[bold red]Image not found")
                raise typer.Exit(1)
            if image_path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
                self.console.print("[bold red]Only png, jpg, jpeg, and webp images are supported")
                raise typer.Exit(1)

            output_path = Path(output_file) if output_file else None
            final_output_path, reduction_percentage = self._compress_single_image(image_path, output_path)

            self.console.print(
                f"Tinified image saved to {final_output_path} with a reduction of {reduction_percentage:.2f}%"
            )


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
        image_file: Annotated[
            str | None, typer.Option("--image", "-i", help="Image to tinify. Mutually exclusive with --pattern.")
        ] = None,
        output_file: Annotated[
            str | None,
            typer.Option(
                "--output-image",
                "-o",
                help="File to save compressed image to. Defaults to in-place. Single file mode only.",
            ),
        ] = None,
        pattern: Annotated[
            str | None,
            typer.Option(
                "--pattern",
                "-p",
                help="Glob pattern to match multiple images (e.g., '*.png', 'images/**/*.jpg'). Mutually exclusive with --image.",
            ),
        ] = None,
        output_dir: Annotated[
            str | None,
            typer.Option(
                "--output-dir",
                "-d",
                help="Directory to save compressed images when using --pattern. If not specified, compresses in-place.",
            ),
        ] = None,
    ) -> None:
        """Compress image(s) using tinify.

        Supports two modes:
        1. Single file mode: Use --image to compress one image
        2. Pattern mode: Use --pattern to compress multiple images matching a glob pattern

        Examples:
          # Compress single image in-place
          par_gpt tinify --image photo.png

          # Compress single image to new file
          par_gpt tinify --image photo.png --output-image compressed.png

          # Compress all PNG files in current directory
          par_gpt tinify --pattern "*.png"

          # Compress all images recursively and save to output directory
          par_gpt tinify --pattern "**/*.{png,jpg}" --output-dir compressed/
        """
        command = TinifyCommand()
        command.execute(ctx, image_file, output_file, pattern, output_dir)

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
