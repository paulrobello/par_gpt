"""Terminal image display utilities."""

from __future__ import annotations

import sys
from pathlib import Path

from par_ai_core.par_logging import console_err
from rich.console import Console

from par_utils import PathSecurityError, validate_relative_path

from ._singletons import cache_manager


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
    # Import heavy dependencies locally for better startup performance
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

        if dimension in ["auto", "small", "medium", "large"]:
            if sixel_supported:
                width = console.width * 8
                height = console.height * 16
            else:
                width = console.width * 2
                height = console.height * 2
            if dimension == "small":
                width = round(width * 0.25)
                height = round(height * 0.25)
            elif dimension == "medium":
                width = round(width * 0.5)
                height = round(height * 0.5)
            elif dimension == "large":
                width = round(width * 0.75)
                height = round(height * 0.75)
        else:
            if "x" in dimension:
                width, height = (int(x) for x in dimension.split("x"))
            else:
                width = height = int(dimension)
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
            c = sixel_converter.SixelConverter(
                image_path, w=new_image_width, h=new_image_height, chromakey=transparent, alpha_threshold=0, fast=True
            )
            if console.stderr:
                c.write(sys.__stderr__)
            else:
                c.write(sys.__stdout__)

            return "Image shown in terminal"
        pixels = Pixels.from_image(image, resize=(new_image_width, new_image_height - 2))
        console.print(pixels)
        return "Image shown in terminal"
    except Exception as e:
        console.print(e)
        console.print_exception()

        return f"Error: {str(e)}"
