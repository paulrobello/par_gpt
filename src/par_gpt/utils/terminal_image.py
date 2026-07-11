"""Terminal image display utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from par_ai_core.par_logging import console_err
from rich.console import Console

from par_utils import PathSecurityError, validate_relative_path

from ._singletons import cache_manager

# Named scaling factors for ``show_image_in_terminal`` (QA-010).
# Terminal cells map to different pixel counts depending on the renderer.
SIXEL_CELL_MULTIPLIER: tuple[int, int] = (8, 16)  # (width, height) per cell for sixel
PIXEL_CELL_MULTIPLIER: tuple[int, int] = (2, 2)  # (width, height) per cell for rich_pixels
SIZE_FACTORS: dict[str, float] = {"small": 0.25, "medium": 0.5, "large": 0.75}


def _parse_dimension(
    dimension: str,
    console_width: int,
    console_height: int,
    sixel_supported: bool,
) -> tuple[int, int]:
    """Resolve a dimension spec into a ``(width, height)`` pixel target.

    Accepts the named presets ``auto``/``small``/``medium``/``large`` (scaled
    from the console cell size) or an explicit ``WIDTHxHEIGHT`` / single integer.
    Pure function: no I/O.
    """
    if dimension in ("auto", "small", "medium", "large"):
        cell_w, cell_h = SIXEL_CELL_MULTIPLIER if sixel_supported else PIXEL_CELL_MULTIPLIER
        width = console_width * cell_w
        height = console_height * cell_h
        if dimension != "auto":
            factor = SIZE_FACTORS[dimension]
            width = round(width * factor)
            height = round(height * factor)
        return width, height

    if "x" in dimension:
        width_str, height_str = dimension.split("x")
        return int(width_str), int(height_str)
    size = int(dimension)
    return size, size


def _render_sixel(
    converter_module: Any,
    image_path: Path,
    new_width: int,
    new_height: int,
    transparent: bool,
    console: Console,
) -> str:
    """Render ``image_path`` as sixel graphics and return the status string."""
    converter = converter_module.SixelConverter(
        str(image_path), w=new_width, h=new_height, chromakey=transparent, alpha_threshold=0, fast=True
    )
    if console.stderr:
        converter.write(sys.__stderr__)
    else:
        converter.write(sys.__stdout__)
    return "Image shown in terminal"


def _render_pixels(pixels_cls: Any, image: Any, new_width: int, new_height: int, console: Console) -> str:
    """Render ``image`` as terminal pixels (rich_pixels) and return the status string."""
    pixels = pixels_cls.from_image(image, resize=(new_width, new_height - 2))
    console.print(pixels)
    return "Image shown in terminal"


def show_image_in_terminal(
    image_path: str | Path,
    dimension: str = "auto",
    no_sixel: bool = False,
    transparent: bool = True,
    console: Console | None = None,
) -> str:
    """
    Show image in terminal.

    Args:
        image_path (str): Image path or URL
        dimension (str, optional): Image dimension in format of WIDTHxHEIGHT, small, medium, large or auto.
        no_sixel (bool, optional): Disable use of sixel even if its supported. Defaults to False.
        console (Console, optional): Console. Defaults to stderr.

    Returns:
        str: Status of the operation

    Raises:
        ValueError: If image_path not specified or invalid.
    """
    # Import heavy dependencies locally for better startup performance. These
    # imports double as an availability probe: if any of PIL / rich_pixels /
    # textual_image is missing we fall back to a status string. The bound names
    # are passed into the render helpers so the probe results are reused.
    try:
        from PIL import Image
        from rich_pixels import Pixels
        from textual_image.renderable.sixel import query_terminal_support as sixel_query_terminal_support

        try:
            from sixel import converter as sixel_converter

            sixel_supported = sixel_query_terminal_support()
        except Exception:
            sixel_supported = False
    except ImportError:
        # Fallback if dependencies not available
        return "Image display dependencies not available"

    if not console:
        console = console_err
    if not image_path:
        raise ValueError("Image path or URL is required")

    try:
        if not isinstance(image_path, str):
            image_path = str(image_path)
        if image_path.startswith("//"):
            image_path = "https:" + image_path
        if image_path.startswith("http"):
            image_path = cache_manager.download(image_path)

        # Validate path for security before using it
        image_path_str = str(image_path)
        try:
            # Check for path traversal attempts
            if "../" in image_path_str or "..\\" in image_path_str:
                raise PathSecurityError("Path traversal detected in image path")
            # For relative paths, validate them
            if not Path(image_path_str).is_absolute():
                validate_relative_path(image_path_str, max_depth=5)
        except PathSecurityError as e:
            console.print(f"[red]Security error: {e}[/red]")
            return "Security error: Invalid image path"

        image_path = Path(image_path).expanduser()
        if not image_path.exists():
            return "Image not found"

        width, height = _parse_dimension(dimension, console.width, console.height, sixel_supported)
        if not width or not height:
            return "Invalid dimension"

        image = Image.open(image_path)
        w, h = image.size

        width_scale = width / w
        height_scale = height / h
        scale = min(width_scale, height_scale)
        new_image_width = round(w * scale)
        new_image_height = round(h * scale)
        # console.print(f"Image size {w} x {h} : Console {dimension}: {width} x {height} : {scale}")

        if sixel_supported and not no_sixel:
            return _render_sixel(sixel_converter, image_path, new_image_width, new_image_height, transparent, console)
        return _render_pixels(Pixels, image, new_image_width, new_image_height, console)
    except Exception as e:
        console.print(e)
        console.print_exception()

        return f"Error: {type(e).__name__}: {e}"
