"""macOS / cross-platform window enumeration and screen + window capture utilities."""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any

from par_ai_core.llm_image_utils import image_to_base64
from par_ai_core.par_logging import console_err
from pydantic import BaseModel, Field
from strenum import StrEnum

from ._macos_bindings import (
    copy_window_list_info,
    get_active_display_list,
    get_display_bounds,
    get_frontmost_app,
    get_main_display_id,
)

# Window-filtering constants for ``list_visible_windows_mac`` (QA-006).
_MENU_BAR_APPS: frozenset[str] = frozenset(
    {
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
)
_IGNORE_WINDOW_TITLES: frozenset[str] = frozenset(
    {
        "MenuBarRoundedCover",
        "MenuBarCover",
        "Item-0",
        "Menubar",
        "StatusBarApp",
        "Monitor Control Gamma Activity Enforcer",
    }
)
_MIN_WINDOW_DIMENSION = 100
_MENU_BAR_LAYER_THRESHOLD = 25
_MIN_WINDOW_ALPHA = 0.1

# Activity-scoring constants for ``_score_window`` (QA-006).
# Higher score = more likely to be the active window.
_FRONTMOST_APP_SCORE_BOOST = 10000
_LAYER_ZERO_SCORE_BOOST = 1000
_LAYER_PENALTY_MULTIPLIER = 10
_OPAQUE_WINDOW_SCORE_BOOST = 100
_SIZE_BONUS_DIVISOR = 100000
_MAX_SIZE_BONUS = 50


def _filter_eligible_windows(
    window_list: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    """Filter raw CGWindowList entries down to eligible application windows.

    Each raw entry is a dict-like Core Graphics window record. Returns
    ``(original_enumeration_index, window)`` pairs for windows that pass every
    filter: has an owner name; not a known menu-bar/system app; title not in the
    ignore list; at least ``_MIN_WINDOW_DIMENSION`` px on each side; below the
    menu-bar layer; sufficiently opaque; and not an empty-title Finder /
    System Preferences window.

    The original enumeration index is preserved because position in the window
    list (earlier = more recently active) feeds the activity score.
    """
    eligible: list[tuple[int, dict[str, Any]]] = []
    for idx, window in enumerate(window_list):
        app_name = window.get("kCGWindowOwnerName", "")
        app_title = window.get("kCGWindowName", "")
        window_layer = window.get("kCGWindowLayer", 0)
        window_bounds = window.get("kCGWindowBounds", {})
        window_alpha = window.get("kCGWindowAlpha", 0)

        if not app_name:
            continue
        if app_name in _MENU_BAR_APPS:
            continue
        if app_title in _IGNORE_WINDOW_TITLES:
            continue
        width = window_bounds.get("Width", 0)
        height = window_bounds.get("Height", 0)
        if width < _MIN_WINDOW_DIMENSION or height < _MIN_WINDOW_DIMENSION:
            continue
        if window_layer >= _MENU_BAR_LAYER_THRESHOLD:
            continue
        if window_alpha < _MIN_WINDOW_ALPHA:
            continue
        if not app_title and app_name in {"Finder", "System Preferences"}:
            continue

        eligible.append((idx, window))
    return eligible


def _score_window(
    idx: int,
    app_name: str,
    window_pid: int,
    frontmost_app_name: str | None,
    frontmost_pid: int | None,
    window_layer: int,
    window_alpha: float,
    window_size: int,
) -> float:
    """Score how likely a window is the active one (higher = more likely).

    Pure function: same inputs always yield the same score, so the sort order
    produced by ``list_visible_windows_mac`` is stable and deterministic.
    """
    score: float = 0
    # A window owned by the frontmost app gets a large boost.
    if frontmost_app_name and app_name == frontmost_app_name:
        score += _FRONTMOST_APP_SCORE_BOOST
    elif frontmost_pid and window_pid == frontmost_pid:
        score += _FRONTMOST_APP_SCORE_BOOST
    # Layer 0 is typical for ordinary app windows; higher layers are pushed back.
    if window_layer == 0:
        score += _LAYER_ZERO_SCORE_BOOST
    else:
        score -= window_layer * _LAYER_PENALTY_MULTIPLIER
    # Fully opaque windows are more likely to be active.
    if window_alpha >= 1.0:
        score += _OPAQUE_WINDOW_SCORE_BOOST
    # Position in window list: earlier = more recently active.
    score -= idx
    # Larger windows get a small, capped boost.
    if window_size > 0:
        score += min(window_size / _SIZE_BONUS_DIVISOR, _MAX_SIZE_BONUS)
    return score


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


class ImageCaptureOutputType(StrEnum):
    """
    Specifies the output format for captured images.
    """

    PIL = "PIL"
    BYTES = "BYTES"
    BASE64 = "BASE64"


def list_visible_windows_mac() -> list[VisibleWindow]:
    """
    Returns a list of visible windows on macOS, with the active/frontmost window first.

    Uses NSWorkspace to identify the frontmost application and prioritizes its windows.
    Filters out menu bar apps, system utilities, and other non-application windows.

    Returns:
        list[VisibleWindow]: A list of VisibleWindows objects, sorted with active window first.
    """
    # I/O: identify the frontmost app and snapshot the on-screen windows via the
    # typed macOS bindings (the Quartz/AppKit ``type: ignore`` lives there).
    frontmost_app_name, frontmost_pid = get_frontmost_app()
    window_list = copy_window_list_info()

    # Pure filter + score, separated from I/O (QA-006).
    scored: list[tuple[float, VisibleWindow]] = []
    for idx, window in _filter_eligible_windows(window_list):
        app_name = window.get("kCGWindowOwnerName", "")
        app_title = window.get("kCGWindowName", "")
        window_layer = window.get("kCGWindowLayer", 0)
        window_alpha = window.get("kCGWindowAlpha", 0)
        window_pid = window.get("kCGWindowOwnerPID", 0)
        bounds = window.get("kCGWindowBounds", {})
        width = bounds.get("Width", 0)
        height = bounds.get("Height", 0)
        window_size = width * height
        window_id = window["kCGWindowNumber"]

        score = _score_window(
            idx,
            app_name,
            window_pid,
            frontmost_app_name,
            frontmost_pid,
            window_layer,
            window_alpha,
            window_size,
        )
        scored.append((score, VisibleWindow(app_name=app_name, app_title=app_title, window_id=window_id)))

    # Sort by score (highest first); Python's sort is stable, so equal-score
    # windows keep their original list order.
    scored.sort(key=lambda item: item[0], reverse=True)

    return [window for _, window in scored]


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
    try:
        # Get all active displays
        max_displays = 32  # Reasonable upper limit for displays
        active_displays = get_active_display_list(max_displays)

        screens = []
        main_display_id = get_main_display_id()

        for display_id in active_displays:
            # Get display bounds
            width, height, origin_x, origin_y = get_display_bounds(display_id)

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
        console_err.print(f"[red]Error detecting displays: {type(e).__name__}: {e}[/red]")
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
    app_name = (app_name or "").strip().lower()
    app_title = (app_title or "").strip().lower()
    if not app_name and not app_title and not window_id:
        raise ValueError("Either app_name, app_title, or window_id must be specified")

    if not window_id:
        window_list = copy_window_list_info()

        for window in window_list:
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
