"""Focused unit tests for the pure helpers extracted during the QA-006 / QA-010
refactor in ``src/par_gpt/utils/screen_capture.py`` and ``terminal_image.py``.

These helpers were inlined inside long I/O-bound functions before the refactor;
they are now module-level and pure (no macOS bindings, no filesystem, no
console), so they can be exercised directly and deterministically.
"""

from __future__ import annotations

import pytest

from par_gpt.utils.screen_capture import _filter_eligible_windows, _score_window
from par_gpt.utils.terminal_image import _parse_dimension


# ---------------------------------------------------------------------------
# _score_window (QA-006) — activity-likelihood scoring
# ---------------------------------------------------------------------------


def test_score_window_frontmost_name_match_gets_big_boost() -> None:
    score = _score_window(
        idx=0,
        app_name="Code",
        window_pid=11,
        frontmost_app_name="Code",
        frontmost_pid=99,
        window_layer=0,
        window_alpha=1.0,
        window_size=1_000_000,
    )
    # 10000 (frontmost) + 1000 (layer 0) + 100 (opaque) - 0 (idx) + 10 (size bonus)
    assert score == 11_110


def test_score_window_frontmost_pid_match_when_name_differs() -> None:
    score = _score_window(
        idx=0,
        app_name="X",
        window_pid=42,
        frontmost_app_name="Y",
        frontmost_pid=42,
        window_layer=0,
        window_alpha=1.0,
        window_size=0,
    )
    # elif branch: pid match -> 10000; layer 0 -> 1000; opaque -> 100
    assert score == 11_100


def test_score_window_non_frontmost_high_layer_transparent() -> None:
    score = _score_window(
        idx=2,
        app_name="X",
        window_pid=1,
        frontmost_app_name="Y",
        frontmost_pid=99,
        window_layer=5,
        window_alpha=0.5,
        window_size=100_000,
    )
    # no frontmost; layer penalty -50; no opaque; -idx 2; size bonus +1
    assert score == -51


def test_score_window_size_bonus_capped() -> None:
    huge = _score_window(0, "A", 1, None, None, 0, 1.0, 10_000_000)
    tiny = _score_window(0, "A", 1, None, None, 0, 1.0, 200_000)
    # size bonus capped at 50; tiny gets 2. Both get the layer/opaque boosts.
    assert huge - tiny == 48


def test_score_window_orders_active_window_first() -> None:
    """A frontmost, layer-0, opaque, large window must out-score a background one."""
    active = _score_window(0, "Code", 11, "Code", 99, 0, 1.0, 1_000_000)
    background = _score_window(1, "Slack", 22, "Code", 99, 3, 0.3, 50_000)
    assert active > background


# ---------------------------------------------------------------------------
# _filter_eligible_windows (QA-006) — eligibility filtering
# ---------------------------------------------------------------------------


def _win(
    owner: str = "App",
    title: str = "Doc",
    layer: int = 0,
    alpha: float = 1.0,
    width: int = 800,
    height: int = 600,
    number: int = 1,
    pid: int = 100,
) -> dict[str, object]:
    return {
        "kCGWindowOwnerName": owner,
        "kCGWindowName": title,
        "kCGWindowLayer": layer,
        "kCGWindowAlpha": alpha,
        "kCGWindowBounds": {"Width": width, "Height": height},
        "kCGWindowNumber": number,
        "kCGWindowOwnerPID": pid,
    }


def test_filter_eligible_drops_menu_bar_and_system_apps() -> None:
    windows = [
        _win(owner="Activity Monitor", number=1),
        _win(owner="Stats", number=2),
        _win(owner="Editor", number=3),
    ]
    kept = [num for _, w in _filter_eligible_windows(windows) for num in [w["kCGWindowNumber"]]]
    assert kept == [3]


def test_filter_eligible_drops_small_and_layered_and_transparent() -> None:
    windows = [
        _win(width=50, height=50, number=1),  # too small
        _win(layer=25, number=2),  # menu-bar layer
        _win(alpha=0.05, number=3),  # too transparent
        _win(number=4),  # eligible
    ]
    eligible = _filter_eligible_windows(windows)
    assert [w["kCGWindowNumber"] for _, w in eligible] == [4]


def test_filter_eligible_preserves_original_index() -> None:
    windows = [_win(number=10), _win(number=20), _win(number=30)]
    eligible = _filter_eligible_windows(windows)
    # All eligible; indices must be 0, 1, 2 in order.
    assert [idx for idx, _ in eligible] == [0, 1, 2]


def test_filter_eligible_drops_empty_title_finder_window() -> None:
    windows = [
        _win(owner="Finder", title="", number=1),
        _win(owner="Finder", title="Downloads", number=2),
    ]
    eligible = _filter_eligible_windows(windows)
    assert [w["kCGWindowNumber"] for _, w in eligible] == [2]


# ---------------------------------------------------------------------------
# _parse_dimension (QA-010) — dimension spec parsing
# ---------------------------------------------------------------------------


def test_parse_dimension_auto_sixel_uses_sixel_multipliers() -> None:
    assert _parse_dimension("auto", 80, 24, sixel_supported=True) == (640, 384)


def test_parse_dimension_auto_pixels_uses_pixel_multipliers() -> None:
    assert _parse_dimension("auto", 80, 24, sixel_supported=False) == (160, 48)


@pytest.mark.parametrize(
    ("name", "factor"),
    [("small", 0.25), ("medium", 0.5), ("large", 0.75)],
)
def test_parse_dimension_named_presets_scale_sixel_base(name: str, factor: float) -> None:
    expected = (round(640 * factor), round(384 * factor))
    assert _parse_dimension(name, 80, 24, sixel_supported=True) == expected


def test_parse_dimension_explicit_width_x_height() -> None:
    assert _parse_dimension("320x240", 80, 24, sixel_supported=True) == (320, 240)


def test_parse_dimension_single_integer_sets_square() -> None:
    assert _parse_dimension("200", 80, 24, sixel_supported=True) == (200, 200)


def test_parse_dimension_malformed_width_x_height_x_extra_raises() -> None:
    """A spec with other than exactly two ``x``-separated parts must raise (parity)."""
    with pytest.raises(ValueError):
        _parse_dimension("1x2x3", 80, 24, sixel_supported=True)
