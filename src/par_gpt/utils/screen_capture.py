"""macOS / cross-platform window enumeration and screen + window capture utilities."""

from __future__ import annotations

import io
import os
import tempfile

from par_ai_core.llm_image_utils import image_to_base64
from par_ai_core.par_logging import console_err
from pydantic import BaseModel, Field
from strenum import StrEnum


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
