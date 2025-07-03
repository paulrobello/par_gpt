"""Error handling utilities for centralized error management."""

from __future__ import annotations

from par_utils.errors.handlers import (
    ErrorHandler,
    log_error,
    suppress_error,
)
from par_utils.errors.registry import ErrorCategory, ErrorRegistry, ErrorSeverity

__all__ = [
    "ErrorRegistry",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorHandler",
    "log_error",
    "suppress_error",
]
