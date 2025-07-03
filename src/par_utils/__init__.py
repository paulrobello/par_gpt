"""PAR Utils - Reusable utilities for Python projects.

This package provides a collection of general-purpose utilities that can be
used across different Python projects. It includes performance optimization,
security validation, error handling, caching, and console management utilities.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Paul Robello"
__email__ = "probello@gmail.com"

# Performance utilities
# Caching utilities
from par_utils.caching.disk_cache import CacheManager

# Console utilities
from par_utils.console.manager import ConsoleManager
from par_utils.errors.handlers import (
    ErrorHandler,
    log_error,
    suppress_error,
)

# Error handling utilities
from par_utils.errors.registry import ErrorCategory, ErrorRegistry, ErrorSeverity

# Lazy loading utilities
from par_utils.performance.lazy_loading import (
    LazyImportManager,
    LazyUtilsLoader,
    lazy_import,
)
from par_utils.performance.timing import (
    TimingRegistry,
    disable_timing,
    enable_timing,
    is_timing_enabled,
    show_timing_details,
    show_timing_summary,
    timed,
    timer,
    user_timer,
)

# Security utilities
from par_utils.security.path_validation import (
    PathSecurityError,
    SecurePathValidator,
    sanitize_filename,
    validate_relative_path,
    validate_within_base,
)

__all__ = [
    # Performance
    "TimingRegistry",
    "enable_timing",
    "disable_timing",
    "is_timing_enabled",
    "show_timing_details",
    "show_timing_summary",
    "timed",
    "timer",
    "user_timer",
    "LazyImportManager",
    "LazyUtilsLoader",
    "lazy_import",
    # Security
    "PathSecurityError",
    "SecurePathValidator",
    "sanitize_filename",
    "validate_relative_path",
    "validate_within_base",
    # Error handling
    "ErrorRegistry",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorHandler",
    "log_error",
    "suppress_error",
    # Caching
    "CacheManager",
    # Console
    "ConsoleManager",
]
