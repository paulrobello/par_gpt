"""Backward compatibility module for error handling utilities.

This module provides backward compatibility by importing the new error handling
utilities from par_utils and exposing the same interface as before.
"""

from __future__ import annotations

# Import the new error handling utilities from par_utils
from par_utils import (
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    log_error,
    suppress_error,
)

# Export all the functions and classes for backward compatibility
__all__ = [
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorHandler",
    "log_error",
    "suppress_error",
]
