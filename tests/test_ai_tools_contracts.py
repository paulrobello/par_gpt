"""Contract tests for AI tool return values.

These tests pin down the error-signaling convention established for QA-004 /
QA-009 in ``src/par_gpt/ai_tools/ai_tools.py``:

    * a tool that cannot complete its intended operation returns content whose
      text begins with the literal prefix ``"Error: "`` (for ``str`` returns),
      or carries ``"Error: ..."`` in the element (``list``) / ``stderr`` field;
    * a success return never begins with ``"Error: "``;
    * the exception type is preserved in the message as ``{type(e).__name__}:``.

All paths are exercised without making real LLM/network/host calls: external
entry points are monkeypatched at the module level. This mirrors the style of
``test_context_manager.py`` / ``test_error_registry.py``.
"""

from unittest.mock import MagicMock

import pytest

from par_gpt.ai_tools import ai_tools


# ---------------------------------------------------------------------------
# URL-fetch / open tools: security rejection path
# ---------------------------------------------------------------------------


def test_fetch_url_security_rejection_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """ai_fetch_url must return a list whose single element is error-prefixed."""
    monkeypatch.setattr(ai_tools, "validate_url", lambda url: (_ for _ in ()).throw(ValueError("disallowed scheme")))
    result = ai_tools.ai_fetch_url.invoke({"urls": ["file:///etc/passwd"]})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].startswith("Error: ")
    assert "URL rejected" in result[0]
    assert "ValueError" in result[0]


def test_open_url_security_rejection_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """ai_open_url must return an error-prefixed string when validate_url rejects."""
    monkeypatch.setattr(ai_tools, "validate_url", lambda url: (_ for _ in ()).throw(ValueError("disallowed scheme")))
    monkeypatch.setattr(ai_tools, "webbrowser", MagicMock())  # ensure no real browser open on a leaky guard

    result = ai_tools.ai_open_url.invoke({"url": "file:///etc/passwd"})

    assert isinstance(result, str)
    assert result.startswith("Error: ")
    assert "ValueError" in result


# ---------------------------------------------------------------------------
# Clipboard tools: success vs. failure
# ---------------------------------------------------------------------------


def test_clipboard_copy_success_is_not_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful copy must return the plain success message (no prefix)."""
    fake_clipboard = MagicMock()
    monkeypatch.setattr(ai_tools, "lazy_import", lambda *args, **kwargs: fake_clipboard)

    result = ai_tools.ai_copy_to_clipboard.invoke({"text": "hello"})

    assert result == "Text copied to clipboard"
    assert not result.startswith("Error: ")
    fake_clipboard.copy.assert_called_once_with("hello")


def test_clipboard_copy_failure_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clipboard failure must surface as a prefixed error preserving the type."""
    fake_clipboard = MagicMock()
    fake_clipboard.copy.side_effect = RuntimeError("clipboard locked")
    monkeypatch.setattr(ai_tools, "lazy_import", lambda *args, **kwargs: fake_clipboard)

    result = ai_tools.ai_copy_to_clipboard.invoke({"text": "hello"})

    assert result.startswith("Error: ")
    assert "RuntimeError" in result
    assert "clipboard" in result.lower()


def test_clipboard_paste_failure_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A paste failure must surface as a prefixed error preserving the type."""
    fake_clipboard = MagicMock()
    fake_clipboard.paste.side_effect = OSError("no clipboard")
    monkeypatch.setattr(ai_tools, "lazy_import", lambda *args, **kwargs: fake_clipboard)

    result = ai_tools.ai_copy_from_clipboard.invoke({})

    assert result.startswith("Error: ")
    assert "OSError" in result


# ---------------------------------------------------------------------------
# Capture tools: empty-list, list-error, and capture-error paths
# ---------------------------------------------------------------------------


def test_capture_screen_no_displays_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No displays means the tool cannot fulfil its purpose -> error-prefixed."""
    monkeypatch.setattr(ai_tools._utils, "list_available_screens", lambda: [])

    result = ai_tools.ai_capture_screen_image.invoke({"screen_id": None, "describe_image": True})

    assert isinstance(result, str)
    assert result.startswith("Error: ")
    assert "no displays" in result.lower()


def test_capture_screen_list_failure_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure enumerating screens must surface as a prefixed error with type."""

    def boom() -> None:
        raise OSError("quartz unavailable")

    monkeypatch.setattr(ai_tools._utils, "list_available_screens", boom)

    result = ai_tools.ai_capture_screen_image.invoke({"screen_id": None, "describe_image": True})

    assert result.startswith("Error: ")
    assert "OSError" in result
    assert "screen list" in result.lower()


def test_capture_screen_capture_failure_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure inside the capture/describe step must surface a prefixed error."""
    screen = MagicMock()
    screen.name = "Display"
    screen.screen_id = 1
    monkeypatch.setattr(ai_tools._utils, "list_available_screens", lambda: [screen])
    monkeypatch.setattr(ai_tools._utils, "capture_screen_image", lambda **kwargs: (_ for _ in ()).throw(OSError("capture failed")))
    monkeypatch.setattr(ai_tools, "_resolve_skip_confirmation", lambda: False)

    result = ai_tools.ai_capture_screen_image.invoke({"screen_id": None, "describe_image": False})

    assert result.startswith("Error: ")
    assert "OSError" in result
    assert "screen image" in result.lower()


def test_capture_window_no_windows_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No visible windows means the tool cannot fulfil its purpose -> error-prefixed."""
    monkeypatch.setattr(ai_tools._utils, "list_visible_windows_mac", lambda: [])

    result = ai_tools.ai_capture_window_image.invoke(
        {"app_name": None, "app_title": None, "window_id": None, "describe_image": True}
    )

    assert isinstance(result, str)
    assert result.startswith("Error: ")
    assert "no visible" in result.lower()


def test_capture_window_explicit_id_avoids_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    """With an explicit window_id the list path is skipped; a capture failure is prefixed."""
    monkeypatch.setattr(ai_tools._utils, "capture_window_image", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("denied")))
    monkeypatch.setattr(ai_tools, "_resolve_skip_confirmation", lambda: False)
    # Sentinel: if the list path were entered, this would blow up the test.
    monkeypatch.setattr(ai_tools._utils, "list_visible_windows_mac", lambda: (_ for _ in ()).throw(AssertionError("should not list")))

    result = ai_tools.ai_capture_window_image.invoke(
        {"app_name": None, "app_title": None, "window_id": 42, "describe_image": False}
    )

    assert result.startswith("Error: ")
    assert "RuntimeError" in result


# ---------------------------------------------------------------------------
# execute_code: sandbox failure lands in stderr with the prefix
# ---------------------------------------------------------------------------


def test_execute_code_failure_stderr_is_error_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sandbox runner failure must populate stderr with a prefixed, typed error."""

    class _BoomRunner:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("docker unavailable")

        def execute_code_in_container(self, code: str) -> object:  # pragma: no cover - never reached
            raise AssertionError("init should have failed")

    import sandbox as sandbox_mod

    monkeypatch.setattr(sandbox_mod, "SandboxRun", _BoomRunner)

    result = ai_tools.execute_code.invoke({"code": "print('hi')"})

    assert result.exit_code == 1
    assert result.stderr.startswith("Error: ")
    assert "RuntimeError" in result.stderr


# ---------------------------------------------------------------------------
# Shared helper behavior (QA-002 extraction)
# ---------------------------------------------------------------------------


def test_resolve_skip_confirmation_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without yes-to-all set, the helper resolves to False (no skip)."""
    # Ensure the tool context reports disabled.
    from par_gpt.utils.context_manager import clear_tool_context, set_tool_context

    clear_tool_context()
    set_tool_context(yes_to_all=False)
    try:
        assert ai_tools._resolve_skip_confirmation() is False
    finally:
        clear_tool_context()


def test_list_and_select_returns_none_for_empty() -> None:
    """The shared selection helper signals 'empty' by returning None."""
    assert ai_tools._list_and_select([], singular_label="x", list_header="y", primary_marker="*", heading_label=str, list_label=str, select_label="z") is None


def test_list_and_select_returns_first_for_non_empty() -> None:
    """The shared selection helper always selects the first item."""
    item = MagicMock(name="first")
    selected = ai_tools._list_and_select(
        [item, MagicMock(name="second")],
        singular_label="Found one",
        list_header="Available",
        primary_marker="*",
        heading_label=lambda i: "label",
        list_label=lambda i: "label",
        select_label="Selecting",
    )
    assert selected is item
