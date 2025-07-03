"""Utils"""

from __future__ import annotations

import getpass
import io
import os
import platform
import subprocess
import sys
import tomllib
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Any, Literal, cast

import orjson as json

# Heavy imports moved inside functions for better startup performance
# requests import moved to functions that need it (weather functions)
import tomli_w
from packaging.requirements import Requirement
from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_image_utils import image_to_base64, image_to_chat_message, try_get_image_type
from par_ai_core.llm_providers import LlmProvider, is_provider_api_key_set, provider_base_urls, provider_env_key_names
from par_ai_core.par_logging import console_err
from pydantic import BaseModel, Field, SecretStr
from rich.console import Console
from strenum import StrEnum

# Heavy imports (PIL, rich_pixels, sixel) moved inside functions
from par_gpt import __env_var_prefix__
from par_gpt.repo.repo import ANY_GIT_ERROR, GitRepo
from par_utils import CacheManager, PathSecurityError, validate_relative_path

# Create cache manager instance for backward compatibility
cache_manager = CacheManager()

# Sixel imports moved inside show_image_in_terminal function


def get_weather_current(location: str, timeout: int = 10) -> dict[str, Any]:
    """
    Get current weather

    Args:
        location (str): Location
        timeout (int): Timeout in seconds

    Returns:
        str: Weather
    """
    # Lazy import requests
    import requests

    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/current.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&aqi=no",
        timeout=timeout,
    )
    return response.json()


def get_weather_forecast(location: str, num_days: int, timeout: int = 10) -> dict[str, Any]:
    """
    Get weather forecast for next days

    Args:
        location (str): Location
        num_days (int): Number of days
        timeout (int): Timeout in seconds

    Returns:
        str: Weather
    """
    # Lazy import requests
    import requests

    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/forecast.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&days={num_days}&aqi=no&alerts=no",
        timeout=timeout,
    )
    return response.json()


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
            extra_context = json.loads(extra_context.read_text(encoding="utf-8"))
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


FigletFontName = Literal[
    "ansi_shadow",
    "3d-ascii",
    "alpha",
    "big_money-se",
    "blocks",
    "bulbhead",
    "doh",
    "impossible",
    "isometric1",
    "slant_relief",
    "caligraphy",
    "jerusalem",
    "pawp",
    "peaks",
    "tinker-toy",
    "big",
    "bloody",
]


def figlet_vertical(
    text: str, font: FigletFontName = "ansi_shadow", colors: list[str] | None = None, console: Console | None = None
) -> str:
    """
    Create a figlet text and output it to the terminal

    Args:
        text (str): The text to convert to figlet
        font (str): The font to use (default: ansi_shadow)
        colors (list[str] | None): The colors to use as a top to bottom gradient (default: ["#FFFF00", "#FFB000", "#FF7800", "#FF3200", "#FF0000"])
        console (Console | None): The console to use

    Returns:
        str: The figlet text

    Notes:
        Calling this tool will send its output directly to the terminal. You do not need to capture the output.
    """
    # Import pyfiglet locally for better startup performance
    try:
        import pyfiglet
    except ImportError:
        return "pyfiglet not available"

    if not console:
        console = console_err

    text = pyfiglet.figlet_format(text, font=font, width=console.width)

    # Fire gradient colors
    colors = colors or [
        "#FFFF00",  # Bright yellow
        "#FFB000",  # Orange-yellow
        "#FF7800",  # Orange
        "#FF3200",  # Orange-red
        "#FF0000",  # Deep red
    ]

    # Split text into lines and compute lines per color
    lines = text.split("\n")
    num_lines = len(lines)
    lines_per_color = num_lines / len(colors)

    # Create gradient text
    styled_lines = []
    for i, line in enumerate(lines):
        color_index = int(i / lines_per_color)
        if color_index >= len(colors):
            color_index = len(colors) - 1
        styled_lines.append(f"[{colors[color_index]}]{line}")

    # Join print and capture output
    io_buffer = StringIO()
    with redirect_stdout(io_buffer):
        with redirect_stderr(io_buffer):
            console.print("\n".join(styled_lines))

    ret = io_buffer.getvalue()
    # the llm often messes up the colors so we output before we send to llm
    print(ret)

    return ret


def figlet_horizontal(
    text: str, font: FigletFontName = "ansi_shadow", colors: list[str] | None = None, console: Console | None = None
) -> str:
    """
    Create a figlet text and output it to the terminal

    Args:
        text (str): The text to convert to figlet
        font (str): The font to use (default: ansi_shadow)
        colors (list[str] | None): The colors to use as a gradient applied to each letter left to right (default: ["#FFFF00", "#FFB000", "#FF7800", "#FF3200", "#FF0000"])
        console (Console | None): The console to use

    Returns:
        str: The figlet text

    Notes:
        Calling this tool will send its output directly to the terminal. You do not need to capture the output.
    """
    # Import pyfiglet locally for better startup performance
    try:
        import pyfiglet
    except ImportError:
        return "pyfiglet not available"

    if not console:
        console = console_err

    # Known issue that fonts that overlap letters will not be overlapped as we render each letter separately
    max_height: int = 0
    figlet_chars: list[str] = []
    # used to pad figlet chars to max height
    space_char_indexes: list[int] = []
    # used to not change colors for space characters

    # loop over each letter and generate figlet letter
    for i, letter in enumerate(text):
        if letter == " ":
            space_char_indexes.append(i)
        figlet_chars.append(pyfiglet.figlet_format(letter, font=font, width=console.width))
        # figlet wraps at 80 chars by default override with actual console width

        # break char into lines to get max height for padding
        char_lines = figlet_chars[i].split("\n")
        if len(char_lines) > max_height:
            max_height = len(char_lines) - 1

    letters = []
    # pad figlet chars to max height
    for letter in figlet_chars:
        char_lines = letter.split("\n")
        if len(char_lines) < max_height:
            char_lines += [""] * (max_height - len(char_lines))
        letters.append("\n".join(char_lines))

    # Fire gradient colors
    colors = colors or [
        "#FFFF00",  # Bright yellow
        "#FFB000",  # Orange-yellow
        "#FF7800",  # Orange
        "#FF3200",  # Orange-red
        "#FF0000",  # Deep red
    ]

    # Create gradient text
    styled_lines = []
    for y in range(max_height):
        color_index: int = 0
        line: str = ""
        # loop over each letter and apply color for current line
        for i, letter in enumerate(letters):
            # escape format char [
            char_line = letter.split("\n")[y].replace("[", "\\[")
            # if last char is \, escape it so it does not interfere with color change
            if char_line and char_line[-1] == "\\":
                char_line += "\\"
            # apply color to current strip of text
            line += f"[{colors[color_index]}]{char_line}[/{colors[color_index]}]"
            # move to next color if not a space
            if i not in space_char_indexes:
                color_index = (color_index + 1) % len(colors)
        styled_lines.append(line)

    # Join print and capture output
    io_buffer = StringIO()
    with redirect_stdout(io_buffer):
        with redirect_stderr(io_buffer):
            console.print("\n".join(styled_lines))
            # print("\n".join(styled_lines))

    ret = io_buffer.getvalue()

    # the llm often messes up the colors so we output before we send to llm
    print(ret)

    return ret


class VisibleWindow(BaseModel):
    """Info about Visible Windows"""

    app_name: str = Field(..., description="Name of the application")
    app_title: str = Field(..., description="Current content of the application's title bar")
    window_id: int = Field(..., description="Window ID of the application. Required by some other tools")


class AvailableScreen(BaseModel):
    """Info about Available Screens/Displays"""

    screen_id: int = Field(..., description="Unique identifier for the screen")
    name: str = Field(..., description="Display name or description")
    width: int = Field(..., description="Screen width in pixels")
    height: int = Field(..., description="Screen height in pixels")
    is_primary: bool = Field(..., description="Whether this is the primary/main display")
    origin_x: int = Field(..., description="X coordinate of screen origin")
    origin_y: int = Field(..., description="Y coordinate of screen origin")


def list_visible_windows_mac() -> list[VisibleWindow]:
    """
    Returns a list of visible windows on macOS, with the active/frontmost window first.

    Uses NSWorkspace to identify the frontmost application and prioritizes its windows.
    Filters out menu bar apps, system utilities, and other non-application windows.

    Returns:
        list[VisibleWindow]: A list of VisibleWindows objects, sorted with active window first.
    """
    import Quartz

    # Get the frontmost application to identify active window
    frontmost_app_name = None
    frontmost_pid = None

    try:
        import AppKit

        workspace = AppKit.NSWorkspace.sharedWorkspace()  # type: ignore
        frontmost_app = workspace.frontmostApplication()  # type: ignore
        if frontmost_app:
            frontmost_app_name = frontmost_app.localizedName()  # type: ignore
            frontmost_pid = frontmost_app.processIdentifier()  # type: ignore
    except (ImportError, AttributeError):
        # Fallback if AppKit is not available or has issues
        pass

    windowList = Quartz.CGWindowListCopyWindowInfo(  # type: ignore
        Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
        Quartz.kCGNullWindowID,  # type: ignore
    )  # type: ignore

    # Build window info with metadata for intelligent sorting
    window_data = []

    # Menu bar apps and system utilities to filter out
    menu_bar_apps = {
        "MonitorControl",
        "Bartender 5",
        "JetBrains Toolbox",
        "Control Room",
        "1Blocker- Ad Blocker & Privacy",
        "CleanMyMac X Business",
        "CleanMyMac X",
        "iPhone Backup Extractor",
        "Wireless Diagnostics",
        "System Preferences",
        "Activity Monitor",
        "Console",
        "Keychain Access",
        "Digital Color Meter",
        "AirPort Utility",
        "Migration Assistant",
        "Boot Camp Assistant",
        "Stats",
        "TextSoap",
        "Paw",
        "Pockity",
        "Codeshot",
        "PDF Search- AI-Powered App",
    }

    # Window titles to ignore (often menu bar covers or system windows)
    ignore_titles = {
        "MenuBarRoundedCover",
        "MenuBarCover",
        "Item-0",
        "Menubar",
        "StatusBarApp",
        "Monitor Control Gamma Activity Enforcer",
    }

    for idx, window in enumerate(windowList):
        app_name = window.get("kCGWindowOwnerName", "")
        app_title = window.get("kCGWindowName", "")
        window_layer = window.get("kCGWindowLayer", 0)
        window_bounds = window.get("kCGWindowBounds", {})
        window_alpha = window.get("kCGWindowAlpha", 0)
        window_pid = window.get("kCGWindowOwnerPID", 0)

        # Skip windows without names
        if not app_name:
            continue

        # Skip menu bar apps and system utilities
        if app_name in menu_bar_apps:
            continue

        # Skip windows with ignored titles
        if app_title in ignore_titles:
            continue

        # Skip windows that are too small (likely menu bar items or system elements)
        width = window_bounds.get("Width", 0)
        height = window_bounds.get("Height", 0)
        if width < 100 or height < 100:
            continue

        # Skip windows at menu bar layer (layer 25 is typically menu bar)
        if window_layer >= 25:
            continue

        # Skip transparent windows (alpha < 0.1)
        if window_alpha < 0.1:
            continue

        # Skip windows with empty titles that are likely system windows
        if not app_title and app_name in {"Finder", "System Preferences"}:
            continue

        window_id = window["kCGWindowNumber"]

        # Calculate priority score - higher score = more likely to be the active window
        score = 0

        # Is this window from the frontmost app? Huge boost
        if frontmost_app_name and app_name == frontmost_app_name:
            score += 10000
        elif frontmost_pid and window_pid == frontmost_pid:
            score += 10000

        # Lower layer = more likely to be active (layer 0 is typical for active windows)
        if window_layer == 0:
            score += 1000
        else:
            score -= window_layer * 10

        # Fully opaque windows are more likely to be active
        if window_alpha >= 1.0:
            score += 100

        # Position in window list (earlier = more recently active)
        score -= idx

        # Larger windows get a small boost
        window_size = width * height
        if window_size > 0:
            score += min(window_size / 100000, 50)  # Cap the size bonus

        window_data.append(
            {
                "window": VisibleWindow(app_name=app_name, app_title=app_title, window_id=window_id),
                "score": score,
                "is_frontmost_app": app_name == frontmost_app_name or window_pid == frontmost_pid,
                "layer": window_layer,
                "size": window_size,
            }
        )

    # Sort by score (highest first) - this puts the active window first
    window_data.sort(key=lambda x: x["score"], reverse=True)

    # Extract just the VisibleWindow objects
    result = [item["window"] for item in window_data]

    return result


def list_visible_windows() -> list[VisibleWindow]:
    """
    Returns a list of visible windows.

    Returns:
        list[VisibleWindow]: A list of VisibleWindows objects representing the visible windows.
    """
    import platform

    if platform.system() == "Darwin":
        return list_visible_windows_mac()
    return []


def list_available_screens_mac() -> list[AvailableScreen]:
    """
    Returns a list of available screens/displays on macOS.

    Uses Quartz Core Graphics to detect all connected displays including
    physical monitors and virtual displays.

    Returns:
        list[AvailableScreen]: A list of AvailableScreen objects with primary display first.
    """
    import Quartz

    try:
        # Get all active displays
        max_displays = 32  # Reasonable upper limit for displays
        active_displays = Quartz.CGGetActiveDisplayList(max_displays, None, None)[1]  # type: ignore

        screens = []
        main_display_id = Quartz.CGMainDisplayID()  # type: ignore

        for display_id in active_displays:
            # Get display bounds
            bounds = Quartz.CGDisplayBounds(display_id)  # type: ignore
            width = int(bounds.size.width)
            height = int(bounds.size.height)
            origin_x = int(bounds.origin.x)
            origin_y = int(bounds.origin.y)

            # Check if this is the main display
            is_primary = display_id == main_display_id

            # Generate display name
            if is_primary:
                name = f"Primary Display ({width}x{height})"
            else:
                name = f"Secondary Display ({width}x{height})"

            # Add position info for multi-monitor setups
            if origin_x != 0 or origin_y != 0:
                name += f" at ({origin_x}, {origin_y})"

            screens.append(
                AvailableScreen(
                    screen_id=int(display_id),
                    name=name,
                    width=width,
                    height=height,
                    is_primary=is_primary,
                    origin_x=origin_x,
                    origin_y=origin_y,
                )
            )

        # Sort with primary display first
        screens.sort(key=lambda s: (not s.is_primary, s.screen_id))

        return screens

    except Exception as e:
        console_err.print(f"[red]Error detecting displays: {e}[/red]")
        # Fallback to single screen
        return [
            AvailableScreen(
                screen_id=0, name="Default Display", width=1920, height=1080, is_primary=True, origin_x=0, origin_y=0
            )
        ]


def list_available_screens() -> list[AvailableScreen]:
    """
    Returns a list of available screens/displays.

    Returns:
        list[AvailableScreen]: A list of AvailableScreen objects representing available displays.
    """
    import platform

    if platform.system() == "Darwin":
        return list_available_screens_mac()

    # Fallback for other platforms - single screen
    return [
        AvailableScreen(
            screen_id=0, name="Primary Display", width=1920, height=1080, is_primary=True, origin_x=0, origin_y=0
        )
    ]


class ImageCaptureOutputType(StrEnum):
    """
    Specifies the output format for captured images.
    """

    PIL = "PIL"
    BYTES = "BYTES"
    BASE64 = "BASE64"


def capture_window_image_mac(
    app_name: str | None = None,
    app_title: str | None = None,
    window_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
    skip_confirmation: bool = False,
):
    """
    Captures a screenshot of the specified window on macOS and saves it as a PNG image.
    You must specify at least one of app_name, app_title or window_id.
    Image will be PNG format in the specified output format.

    Args:
        app_name (str | None): Name of the application to find and capture. Defaults to None = Any.
        app_title (str | None): Title of the application to find and capture. Defaults to None = Any.
        window_id (int | None): Window ID of the application to find and capture. Defaults to None = Any.
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.
        skip_confirmation (bool): Skip security confirmation prompt. Defaults to False.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.

    Raises:
        ValueError: If required parameters are missing or if user denies confirmation.
    """
    import tempfile

    import Quartz

    app_name = (app_name or "").strip().lower()
    app_title = (app_title or "").strip().lower()
    if not app_name and not app_title and not window_id:
        raise ValueError("Either app_name, app_title, or window_id must be specified")

    if not window_id:
        windowList = Quartz.CGWindowListCopyWindowInfo(  # type: ignore
            Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
            Quartz.kCGNullWindowID,  # type: ignore
        )  # type: ignore

        for window in windowList:
            app = window.get("kCGWindowOwnerName", "").lower()
            title = window.get("kCGWindowName", "").lower()

            if app_name and (not app or app_name not in app):
                continue
            if app_title and (not title or app_title not in title):
                continue

            window_id = window["kCGWindowNumber"]

    with tempfile.NamedTemporaryFile(suffix=".png") as temp_image:
        # -x mutes sound and -l specifies windowId
        cmd = f"screencapture -x -t png -l {window_id} {temp_image.name}"

        # Security warning for command execution
        try:
            from par_gpt.utils.security_warnings import warn_command_execution

            if not warn_command_execution(
                command=cmd,
                operation_description=f"Capture screenshot of window (app: {app_name or 'any'}, title: {app_title or 'any'}, id: {window_id or 'detected'})",
                skip_confirmation=skip_confirmation,
            ):
                raise ValueError("Screenshot capture cancelled by user for security reasons")
        except ImportError:
            # Fallback if security warnings module is not available
            if not skip_confirmation:
                from rich.console import Console
                from rich.prompt import Prompt

                console = Console(stderr=True)
                console.print(f"[yellow]⚠️  About to execute system command:[/yellow] [cyan]{cmd}[/cyan]")
                response = Prompt.ask("Continue?", default="Y", console=console)
                if response.lower() not in ["y", "yes"]:
                    raise ValueError("Screenshot capture cancelled by user")

        # console_err.print(cmd)
        ret = os.system(cmd)
        if ret != 0:
            raise ValueError(
                f"Failed to capture screenshot of app '{app_name}' / title '{app_title}' / window ID '{window_id}'"
            )

        # Import PIL locally inside the function
        from PIL import Image

        screenshot = Image.open(temp_image.name)
        if not output_format or output_format == ImageCaptureOutputType.PIL:
            return screenshot

        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        if output_format == ImageCaptureOutputType.BYTES:
            return img_bytes.getvalue()

        return image_to_base64(img_bytes.getvalue(), "png")

    raise ValueError(f"No app '{app_name}' / title '{app_title}' / window ID {window_id} found")


def capture_window_image(
    app_name: str | None = None,
    app_title: str | None = None,
    window_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
    skip_confirmation: bool = False,
):
    """
    Captures a screenshot of the specified window and saves it as a PNG image.
    You must specify at least one of app_name, app_title or window_id.
    Image will be PNG format in the specified output format.

    Args:
        app_name (str | None): Name of the application to find and capture. Defaults to None = Any.
        app_title (str | None): Title of the application to find and capture. Defaults to None = Any.
        window_id (int | None): Window ID of the application to find and capture. Defaults to None = Any.
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.
        skip_confirmation (bool): Skip security confirmation prompt. Defaults to False.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.

    Raises:
        ValueError: If required parameters are missing or if user denies confirmation.
    """
    import platform

    if platform.system() == "Darwin":
        return capture_window_image_mac(app_name, app_title, window_id, output_format, skip_confirmation)

    app_name = (app_name or "").strip().lower()
    app_title = (app_title or "").strip().lower()
    if not app_name and not app_title:
        raise ValueError("Either app_name or app_title must be specified")

    import pyautogui
    import pywinctl as gw

    window_info = gw.getAllWindows()
    # console_err.print(window_info)
    if app_name and not app_title:
        windows = [t for t in window_info if app_name in t.getAppName().lower()]
    elif app_title and not app_name:
        windows = [t for t in window_info if app_title in t.title.lower()]
    else:
        windows = [t for t in window_info if app_name in t.getAppName().lower() and app_title in t.title.lower()]
    if not windows:
        raise ValueError(f"No app '{app_name}' / title '{app_title}' found")

    if len(windows) > 1:
        print(f"Multiple windows found with title '{app_title}':")
        for i, title in enumerate(windows, start=1):
            console_err.print(f"{i}. {title}")
        raise ValueError(f"Multiple app '{app_name}' windows found with title '{app_title}'")
    window = windows[0]
    window.activate()

    left, top, right, bottom = window.left, window.top, window.right, window.bottom
    screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
    if not output_format or output_format == ImageCaptureOutputType.PIL:
        return screenshot

    img_bytes = io.BytesIO()
    screenshot.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    if output_format == ImageCaptureOutputType.BYTES:
        return img_bytes.getvalue()

    return image_to_base64(img_bytes.getvalue(), "png")


def capture_screen_image_mac(
    screen_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
    skip_confirmation: bool = False,
):
    """
    Captures a screenshot of the specified screen/display on macOS.

    Args:
        screen_id (int | None): ID of the display to capture. Defaults to None (primary display).
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.
        skip_confirmation (bool): Skip security confirmation prompt. Defaults to False.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.

    Raises:
        ValueError: If screen capture fails or if user denies confirmation.
    """
    import tempfile

    # Get all screens to map system IDs to screencapture display numbers
    screens = list_available_screens_mac()
    if not screens:
        raise ValueError("No displays found")

    # If no screen_id specified, use primary display
    if screen_id is None:
        # Use primary display (should be first in list)
        screen_id = screens[0].screen_id

    # Map system screen_id to screencapture display number (1-based)
    # screencapture uses sequential numbering: -D 1 is main, -D 2 is secondary, etc.
    screencapture_display_num = None
    for i, screen in enumerate(screens, 1):
        if screen.screen_id == screen_id:
            screencapture_display_num = i
            break

    if screencapture_display_num is None:
        raise ValueError(f"Screen ID {screen_id} not found in available displays")

    with tempfile.NamedTemporaryFile(suffix=".png") as temp_image:
        # -x mutes sound, -D specifies display number (1-based), -t specifies format
        cmd = f"screencapture -x -t png -D {screencapture_display_num} {temp_image.name}"

        # Security warning for command execution
        try:
            from par_gpt.utils.security_warnings import warn_command_execution

            if not warn_command_execution(
                command=cmd,
                operation_description=f"Capture screenshot of display {screen_id} (screencapture display {screencapture_display_num})",
                skip_confirmation=skip_confirmation,
            ):
                raise ValueError("Screen capture cancelled by user for security reasons")
        except ImportError:
            # Fallback if security warnings module is not available
            if not skip_confirmation:
                from rich.console import Console
                from rich.prompt import Prompt

                console = Console(stderr=True)
                console.print(f"[yellow]⚠️  About to execute system command:[/yellow] [cyan]{cmd}[/cyan]")
                response = Prompt.ask("Continue?", default="Y", console=console)
                if response.lower() not in ["y", "yes"]:
                    raise ValueError("Screen capture cancelled by user")

        # Execute screenshot command
        ret = os.system(cmd)
        if ret != 0:
            raise ValueError(f"Failed to capture screenshot of display {screen_id}")

        # Import PIL locally inside the function
        from PIL import Image

        screenshot = Image.open(temp_image.name)
        if not output_format or output_format == ImageCaptureOutputType.PIL:
            return screenshot

        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        if output_format == ImageCaptureOutputType.BYTES:
            return img_bytes.getvalue()

        return image_to_base64(img_bytes.getvalue(), "png")


def capture_screen_image(
    screen_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
    skip_confirmation: bool = False,
):
    """
    Captures a screenshot of the specified screen/display.

    Args:
        screen_id (int | None): ID of the display to capture. Defaults to None (primary display).
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.
        skip_confirmation (bool): Skip security confirmation prompt. Defaults to False.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.

    Raises:
        ValueError: If screen capture fails or if user denies confirmation.
    """
    import platform

    if platform.system() == "Darwin":
        return capture_screen_image_mac(screen_id, output_format, skip_confirmation)

    # Fallback for other platforms using pyautogui
    try:
        import pyautogui

        # Security warning for screen capture
        if not skip_confirmation:
            from rich.console import Console
            from rich.prompt import Prompt

            console = Console(stderr=True)
            console.print("[yellow]⚠️  About to capture entire screen[/yellow]")
            response = Prompt.ask("Continue?", default="Y", console=console)
            if response.lower() not in ["y", "yes"]:
                raise ValueError("Screen capture cancelled by user")

        screenshot = pyautogui.screenshot()

        if not output_format or output_format == ImageCaptureOutputType.PIL:
            return screenshot

        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        if output_format == ImageCaptureOutputType.BYTES:
            return img_bytes.getvalue()

        return image_to_base64(img_bytes.getvalue(), "png")

    except ImportError:
        raise ValueError("Screen capture not supported on this platform")


def describe_image_with_llm(img: str | Path, llm_config: LlmConfig | None = None) -> str:
    """
    Describes the image using a LLM.

    Args:
        img (str | Path): The image file path or URL.
        llm_config (LlmConfig | None): The LLM configuration. Defaults to None = OpenAI GPT-4o.

    Returns:
        str: A description of the image.
    """
    if isinstance(img, str):
        if not img.startswith("data:image/"):
            if img.startswith("http"):
                img = cache_manager.download(img)
            else:
                img = Path(img)
            if not img.is_file():
                raise ValueError(f"No such file or directory: {img}")
            img = image_to_base64(img.read_bytes(), try_get_image_type(img))
    msg = image_to_chat_message(str(img))
    chat = (llm_config or LlmConfig(LlmProvider.OPENAI, "gpt-4.1")).build_chat_model()
    return str(
        chat.invoke(
            [
                ("system", "Describe the image in great detail"),
                ("user", [{"type": "text", "text": "describe the image"}, msg]),  # type: ignore
            ]
        ).content
    )


def speak(text: str):
    from elevenlabs import play
    from elevenlabs.client import ElevenLabs

    # start_time = time.time()
    model = "eleven_flash_v2_5"
    # model="eleven_flash_v2"
    # model = "eleven_turbo_v2"
    # model = "eleven_turbo_v2_5"
    # model="eleven_multilingual_v2"
    voice = "XB0fDUnXU5powFXDhCwa"  # Charlotte
    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    audio_generator = elevenlabs_client.generate(  # type: ignore
        text=text,
        voice=voice,
        model=model,
        stream=False,
    )
    audio_bytes = b"".join(list(audio_generator))
    # duration = time.time() - start_time
    # console_err.print(f"Model {model} completed tts in {duration:.2f} seconds")
    play(audio_bytes)


def image_gen_dali(
    prompt: str, model_name: Literal["dall-e-2", "dall-e-3"] = "dall-e-3", upgrade_prompt: LlmConfig | None = None
) -> Path:
    from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper

    if upgrade_prompt:
        chat = upgrade_prompt.build_chat_model()
        prompt = str(
            chat.invoke(
                [
                    (
                        "system",
                        "Generate a detailed prompt under 800 chars in order to generate an image based on the users description. Only return the updated prompt. Do not include any intro or explanation.",
                    ),
                    ("user", prompt),
                ]
            ).content
        )
        console_err.print(prompt)
    img_gen = DallEAPIWrapper()
    img_gen.model_name = model_name
    if not is_provider_api_key_set(LlmProvider.OPENAI):
        img_gen.openai_api_key = SecretStr(os.environ[provider_env_key_names[LlmProvider.OPENAI]])
        img_gen.openai_api_base = provider_base_urls[LlmProvider.OPENAI]
    image_url = img_gen.run(prompt)
    return cache_manager.download(image_url)


def update_pyproject_deps(
    do_uv_update: bool = True,
    console: Console | None = None,
    dev_only: bool = False,
    main_only: bool = False,
    dry_run: bool = False,
    skip_packages: list[str] | None = None,
) -> None:
    """
    Update dependencies in pyproject.toml with the currently installed versions.

    This function:
      1. Runs 'uv sync -U' to update packages to latest compatible versions
      2. Gets the list of installed packages from UV
      3. Updates pyproject.toml to match the installed versions

    Args:
        do_uv_update (bool): Whether to use uv sync to update packages. Defaults to True.
        console (Console | None): Console object for logging. Defaults to console_err.
        dev_only (bool): Update only dev dependencies. Defaults to False.
        main_only (bool): Update only main dependencies. Defaults to False.
        dry_run (bool): Preview changes without applying them. Defaults to False.
        skip_packages (list[str] | None): Additional packages to skip. Defaults to None.

    Returns:
        None
    """
    console = console or console_err
    pyproject_path: Path = Path("pyproject.toml")

    if not pyproject_path.exists():
        console.print("[red]pyproject.toml not found in the expected location.")
        return

    # Step 1: Update packages with UV if requested
    if do_uv_update and not dry_run:
        # Security context for subprocess operation
        try:
            from par_gpt.utils.security_warnings import warn_subprocess_operation

            warn_subprocess_operation(
                operation="Update Python packages with UV", command_args=["uv", "sync", "-U"], console=console
            )
        except ImportError:
            console.print("[blue]🔧 SUBPROCESS: Running UV package update operation[/blue]")

        console.print("[cyan]Running 'uv sync -U' to update packages...")
        try:
            subprocess.run(["uv", "sync", "-U"], check=True)
            console.print("[green]Successfully updated packages with UV")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error: uv sync failed: {e}")
            return

    # Step 2: Get installed package versions from UV
    try:
        from par_gpt.utils.security_warnings import warn_subprocess_operation

        warn_subprocess_operation(
            operation="List installed Python packages",
            command_args=["uv", "pip", "list", "--format", "json"],
            console=console,
        )
    except ImportError:
        console.print("[blue]🔧 SUBPROCESS: Getting package list from UV[/blue]")

    console.print("[cyan]Getting installed package versions from UV...")
    try:
        result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True, check=True)
        installed_packages = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        console.print(f"[red]Error getting installed packages: {e}")
        return

    # Create a mapping of package names to versions (case-insensitive)
    installed_versions: dict[str, str] = {pkg["name"].lower(): pkg["version"] for pkg in installed_packages}

    # Read and parse the TOML file
    try:
        with open(pyproject_path, "rb") as f:
            toml_data: dict[str, Any] = tomllib.load(f)
    except Exception as e:
        console.print(f"[red]Error reading pyproject.toml: {e}")
        return

    def process_dependencies(deps: list[str], section_name: str) -> list[str]:
        """Process a list of dependencies and return updated versions."""
        updated_deps: list[str] = []

        # Packages that often have compatibility issues - skip these
        skip_list = {
            "pydantic",  # Often has breaking changes with pydantic-core
            "pydantic-core",  # Must match pydantic version
            # Add more problematic packages as needed
        }
        # Add user-specified packages to skip
        if skip_packages:
            skip_list.update(skip_packages)

        for dep in deps:
            try:
                req: Requirement = Requirement(dep)
            except Exception as e:
                console.print(f"[yellow]Failed to parse dependency '{dep}': {e}. Keeping original.")
                updated_deps.append(dep)
                continue

            package_name: str = req.name
            package_name_lower: str = package_name.lower()

            # Preserve extras and markers
            extras_str: str = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
            marker_str: str = f" ; {req.marker}" if req.marker else ""

            # Skip packages in skip list
            if package_name in skip_list:
                console.print(f"[yellow]{section_name}: Skipping {package_name} (in skip list)")
                updated_deps.append(dep)
                continue

            # Get installed version
            installed_version = installed_versions.get(package_name_lower)

            if installed_version is None:
                console.print(
                    f"[yellow]{section_name}: {package_name} not found in installed packages. Keeping original: {dep}"
                )
                updated_deps.append(dep)
                continue

            # Extract current version constraint
            current_version: str | None = None
            for spec in req.specifier:
                if spec.operator in (">=", ">", "=="):
                    current_version = spec.version
                    break

            # Check if update is needed
            if current_version != installed_version:
                new_dep = f"{package_name}{extras_str}>={installed_version}{marker_str}"
                updated_deps.append(new_dep)
                console.print(f"[green]{section_name}: Updated {dep} to {new_dep}")
            else:
                updated_deps.append(dep)
                console.print(f"[blue]{section_name}: {dep} already matches installed version")

        return updated_deps

    changes_made = False

    # Process main dependencies
    if not dev_only:
        project_data: dict[str, Any] | None = toml_data.get("project")
        if project_data and "dependencies" in project_data:
            deps: Any = project_data["dependencies"]
            if isinstance(deps, list):
                console.print("\n[cyan]Processing main dependencies...")
                updated_deps = process_dependencies(deps, "Main")
                if not dry_run:
                    toml_data["project"]["dependencies"] = updated_deps
                changes_made = True
            else:
                console.print("[yellow]Main dependencies should be a list in pyproject.toml.")
        else:
            console.print("[yellow]Main dependencies section not found under [project].")

    # Process dev dependencies
    if not main_only:
        dependency_groups: dict[str, Any] | None = toml_data.get("dependency-groups")
        if dependency_groups and "dev" in dependency_groups:
            dev_deps: Any = dependency_groups["dev"]
            if isinstance(dev_deps, list):
                console.print("\n[cyan]Processing dev dependencies...")
                updated_dev_deps = process_dependencies(dev_deps, "Dev")
                if not dry_run:
                    toml_data["dependency-groups"]["dev"] = updated_dev_deps
                changes_made = True
            else:
                console.print("[yellow]Dev dependencies should be a list in pyproject.toml.")
        else:
            console.print("[yellow]Dev dependencies section not found under [dependency-groups].")

    if not changes_made:
        console.print("[yellow]No dependencies found to process.")
        return

    if dry_run:
        console.print("\n[cyan]Dry run completed. No changes were made to pyproject.toml.")
        return

    # Write the updated TOML data
    try:
        with open(pyproject_path, "wb") as f:
            f.write(tomli_w.dumps(toml_data).encode("utf-8"))
        console.print("\n[green]pyproject.toml updated successfully.")
    except Exception as e:
        console.print(f"[red]Error writing updated pyproject.toml: {e}")
        return


@lru_cache(maxsize=1)
def get_redis_client(
    *, host: str | None = None, port: int | None = None, db: int | None = None, password: str | None = None
):
    """
    Create a Redis client using environment variables or default values.

    Args:
        host (str | None): The Redis host. Defaults to None.
        port (int | None): The Redis port. Defaults to None.
        db (int | None): The Redis database. Defaults to None.
        password (str | None): The Redis password. Defaults to None.

    Returns:
        redis.Redis | None: The Redis client instance or None if the connection fails.
    """
    # Import redis locally for better startup performance
    try:
        import redis
    except ImportError:
        return None

    try:
        redis_host = (
            host or os.environ.get(f"{__env_var_prefix__}_REDIS_HOST") or os.environ.get("REDIS_HOST") or "localhost"
        )
        redis_port = port or int(
            os.environ.get(f"{__env_var_prefix__}_REDIS_PORT") or os.environ.get("REDIS_PORT") or "6379"
        )
        redis_db = db or int(os.environ.get(f"{__env_var_prefix__}_REDIS_DB") or os.environ.get("REDIS_DB") or "0")
        redis_password = (
            password or os.environ.get(f"{__env_var_prefix__}_REDIS_PASSWORD") or os.environ.get("REDIS_PASSWORD")
        )

        return redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)
    except Exception as _:
        return None


def github_publish_repo(repo_name: str | None = None, public: bool = False) -> str:
    """
    Create a new GitHub repository and push current repo to it.
    If an error message is returned stop and make it your final response.

    Args:
        repo_name (str): The name of the repository (default: the name of the current working directory)
        public (bool): Whether the repository should be public (default: False)

    Returns:
        str: The URL of the newly created repository or Error message
    """
    # Import github dependencies locally for better startup performance
    try:
        from git import Remote

        from par_utils import lazy_import

        # Lazy load GitHub classes
        Auth = lazy_import("github", "Auth")
        Github = lazy_import("github", "Github")
        AuthenticatedUser = lazy_import("github", "AuthenticatedUser")
    except ImportError:
        return "Error: GitHub dependencies not available"

    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        return "Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set."

    repo: GitRepo
    try:
        repo = GitRepo()
        if repo.is_dirty():
            # console_err.print("Repo is dirty. Please commit changes before publishing.")
            return "Error: Repo is dirty. Please commit changes before publishing."
    except ANY_GIT_ERROR as e:
        console_err.print(e)
        return "Error: GIT repository not found. Please create a repository first."

    try:
        if repo.repo.remote("origin") is not None:
            console_err.print("Error: Remote origin already exists for this repository. Aborting.")
            return "Error: Remote origin already exists for this repository. Aborting."
    except ANY_GIT_ERROR as _:
        pass

    auth = Auth.Token(os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"])
    g = Github(auth=auth)
    repo_name = repo_name or Path(repo.repo.git_dir).parent.stem.lower().replace(" ", "-")

    # console_err.print(f"Creating repository: {repo_name}")
    gh_repo = cast(AuthenticatedUser, g.get_user()).create_repo(repo_name, private=not public)  # type: ignore
    remote = repo.create_remote("origin", gh_repo.ssh_url)
    if not isinstance(remote, Remote):
        # console_err.print(f"Error: {remote}")
        return f"Error: {remote}"

    try:
        remote.push(f"HEAD:{gh_repo.default_branch}")
        repo.repo.git.branch(f"--set-upstream-to=origin/{gh_repo.default_branch}", gh_repo.default_branch)
    except ANY_GIT_ERROR as e:
        console_err.print(f"Error pushing to remote: {e}")
        return (
            f"GitHub repo created {gh_repo.html_url} but there was an error pushing to the remote. Error Message: {e}"
        )
    return gh_repo.html_url


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # sixel_supported = sixel_query_terminal_support()
    # if sixel_supported:
    #     print("sixel supported")
    #     c = sixel_converter.SixelConverter(
    #         Path(
    #             "~/.par_gpt/cache/d9bae1270340f598bebe4b5c311c08210ef5cd4a.jpg"
    #         ).expanduser()  # , w=width, h=height, chromakey=True, alpha_threshold=0, fast=True
    #     )
    #
    #     c.write(console_err.file)
