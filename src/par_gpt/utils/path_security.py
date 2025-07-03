"""Backward compatibility module for path security utilities.

This module provides backward compatibility by importing the new path security
utilities from par_utils and exposing the same interface as before.
"""

from __future__ import annotations

# Import the new path security utilities from par_utils
from par_utils import (
    PathSecurityError,
    SecurePathValidator,
    sanitize_filename,
    validate_relative_path,
    validate_within_base,
)

# Export all the functions and classes for backward compatibility
__all__ = [
    "PathSecurityError",
    "SecurePathValidator",
    "sanitize_filename",
    "validate_relative_path",
    "validate_within_base",
]
