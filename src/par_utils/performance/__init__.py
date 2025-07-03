"""Performance utilities for optimization and measurement."""

from __future__ import annotations

from par_utils.performance.lazy_loading import LazyImportManager, LazyUtilsLoader
from par_utils.performance.timing import (
    TimingRegistry,
    disable_timing,
    enable_timing,
    is_timing_enabled,
    show_timing_details,
    show_timing_summary,
    timed,
    timer,
)

__all__ = [
    "TimingRegistry",
    "enable_timing",
    "disable_timing",
    "is_timing_enabled",
    "show_timing_details",
    "show_timing_summary",
    "timed",
    "timer",
    "LazyImportManager",
    "LazyUtilsLoader",
]
