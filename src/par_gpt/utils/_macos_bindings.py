"""Typed wrappers around the macOS Quartz / AppKit bindings.

``Quartz`` and ``AppKit`` are macOS-only pyobjc packages that ship without type
stubs. Centralizing their imports here isolates the unavoidable
``# type: ignore[reportMissingImports]`` annotations into a single module
instead of scattering them across the screen-capture call sites (see AUDIT.md
QA-012).

The wrappers import the bindings lazily (inside each function) so that merely
importing this module on a non-macOS platform never triggers the pyobjc import;
the public callers in :mod:`par_gpt.utils.screen_capture` only invoke these
helpers after a ``platform.system() == "Darwin"`` guard.
"""

from __future__ import annotations

from typing import Any


def _quartz() -> Any:
    """Return the Quartz module (lazy; macOS-only)."""
    import Quartz  # type: ignore[reportMissingImports]

    return Quartz


def _appkit() -> Any:
    """Return the AppKit module (lazy; macOS-only)."""
    import AppKit  # type: ignore[reportMissingImports]

    return AppKit


def get_frontmost_app() -> tuple[str | None, int | None]:
    """Return ``(localized_name, process_id)`` of the frontmost app.

    Returns ``(None, None)`` if AppKit is unavailable or no frontmost app is
    reported. Mirrors the original ``try/except (ImportError, AttributeError)``
    fallback in ``list_visible_windows_mac``.
    """
    try:
        appkit = _appkit()
        workspace = appkit.NSWorkspace.sharedWorkspace()
        frontmost_app = workspace.frontmostApplication()
    except (ImportError, AttributeError):
        return None, None
    if not frontmost_app:
        return None, None
    name: str | None = frontmost_app.localizedName()
    pid: int | None = frontmost_app.processIdentifier()
    return name, pid


def copy_window_list_info() -> list[dict[str, Any]]:
    """Return on-screen, non-desktop Core Graphics window info dicts."""
    quartz = _quartz()
    window_list = quartz.CGWindowListCopyWindowInfo(
        quartz.kCGWindowListExcludeDesktopElements | quartz.kCGWindowListOptionOnScreenOnly,
        quartz.kCGNullWindowID,
    )
    return list(window_list)


def get_active_display_list(max_count: int) -> list[int]:
    """Return the active display IDs (up to ``max_count``)."""
    quartz = _quartz()
    return list(quartz.CGGetActiveDisplayList(max_count, None, None)[1])


def get_main_display_id() -> int:
    """Return the main display ID."""
    quartz = _quartz()
    return int(quartz.CGMainDisplayID())


def get_display_bounds(display_id: int) -> tuple[int, int, int, int]:
    """Return ``(width, height, origin_x, origin_y)`` for ``display_id``."""
    quartz = _quartz()
    bounds = quartz.CGDisplayBounds(display_id)
    return (
        int(bounds.size.width),
        int(bounds.size.height),
        int(bounds.origin.x),
        int(bounds.origin.y),
    )
