"""Image processing utilities for consistent image handling."""

from __future__ import annotations

from pathlib import Path

from par_ai_core.llm_image_utils import (
    UnsupportedImageTypeError,
    image_to_base64,
    try_get_image_type,
)
from par_ai_core.par_logging import console_err
from rich.console import Console
from rich_pixels import Pixels

from par_utils import CacheManager

# Create cache manager instance for backward compatibility
cache_manager = CacheManager()


class ImageProcessor:
    """Handles image processing operations consistently across the application."""

    def __init__(self, console: Console | None = None):
        """
        Initialize image processor.

        Args:
            console: Console for output. Defaults to console_err.
        """
        self.console = console or console_err

    def process_image_path(self, image_source: str | Path) -> tuple[Path, str]:
        """
        Process an image path or URL and return the local path and base64 content.

        Args:
            image_source: Path to image file or URL.

        Returns:
            Tuple of (local_path, base64_content).

        Raises:
            UnsupportedImageTypeError: If image type is not supported.
            Exception: If image processing fails.
        """
        # Convert to string for URL checking
        source_str = str(image_source)

        # Check if it's a URL
        if source_str.startswith(("http://", "https://")):
            # Download image
            try:
                local_path = cache_manager.download(source_str)
            except Exception as e:
                self.console.print(f"[red]Failed to download image: {e}[/red]")
                raise
        else:
            local_path = Path(image_source)
            if not local_path.exists():
                raise FileNotFoundError(f"Image file not found: {local_path}")

        # Get image type and convert to base64
        try:
            image_type = try_get_image_type(local_path)
            image_data = local_path.read_bytes()
            base64_content = image_to_base64(image_data, image_type)
            return local_path, base64_content
        except UnsupportedImageTypeError as e:
            self.console.print(f"[red]Unsupported image type: {e}[/red]")
            raise
        except Exception as e:
            self.console.print(f"[red]Failed to process image: {e}[/red]")
            raise

    def display_image(
        self,
        image_path: Path,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> None:
        """
        Display an image in the terminal.

        Args:
            image_path: Path to the image file.
            max_width: Maximum width for display.
            max_height: Maximum height for display.
        """
        try:
            # Only pass resize if both dimensions are provided
            resize_dims = None
            if max_width is not None and max_height is not None:
                resize_dims = (max_width, max_height)

            pixels = Pixels.from_image_path(image_path, resize=resize_dims)
            self.console.print(pixels)
        except Exception as e:
            self.console.print(f"[red]Failed to display image: {e}[/red]")

    def process_and_display(
        self,
        image_source: str | Path,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> str:
        """
        Process an image and display it in the terminal.

        Args:
            image_source: Path to image file or URL.
            max_width: Maximum width for display.
            max_height: Maximum height for display.

        Returns:
            Base64 encoded image content.
        """
        local_path, base64_content = self.process_image_path(image_source)
        self.display_image(local_path, max_width, max_height)
        return base64_content

    def validate_image_path(self, image_path: Path) -> bool:
        """
        Validate that a path points to a valid image file.

        Args:
            image_path: Path to validate.

        Returns:
            True if valid image, False otherwise.
        """
        if not image_path.exists():
            return False

        try:
            try_get_image_type(image_path)
            return True
        except UnsupportedImageTypeError:
            return False


# Convenience functions
def process_image(
    image_source: str | Path,
    console: Console | None = None,
) -> tuple[Path, str]:
    """
    Process an image path or URL and return the local path and base64 content.

    Args:
        image_source: Path to image file or URL.
        console: Optional console for output.

    Returns:
        Tuple of (local_path, base64_content).
    """
    processor = ImageProcessor(console)
    return processor.process_image_path(image_source)


def show_image_in_terminal(
    image_path: Path,
    console: Console | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
) -> None:
    """
    Display an image in the terminal.

    Args:
        image_path: Path to the image file.
        console: Optional console for output.
        max_width: Maximum width for display.
        max_height: Maximum height for display.
    """
    processor = ImageProcessor(console)
    processor.display_image(image_path, max_width, max_height)
