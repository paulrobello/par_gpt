"""Secure path validation utilities to prevent path traversal attacks."""

from __future__ import annotations

import os
import re
from pathlib import Path

from par_ai_core.par_logging import console_err
from rich.console import Console


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""

    def __init__(self, message: str, path: str | Path | None = None):
        super().__init__(message)
        self.path = str(path) if path else None


class SecurePathValidator:
    """Validates paths to prevent directory traversal and other security issues."""

    # Regex patterns for detecting path traversal attempts
    TRAVERSAL_PATTERNS = [
        r"\.\.[\\/]",  # ../ or ..\
        r"[\\/]\.\.[\\/]",  # /../ or \..\
        r"[\\/]\.\.$",  # Ending with /.. or \..
        r"^\.\.[\\/]",  # Starting with ../ or ..\
        r"^\.\.?$",  # Just .. or .
    ]

    # Dangerous characters that should be restricted
    DANGEROUS_CHARS = ["<", ">", '"', "|", "?", "*", "\x00"]

    # Reserved Windows filenames (also dangerous on other systems)
    WINDOWS_RESERVED = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    def __init__(self, console: Console | None = None):
        """Initialize the path validator."""
        self.console = console or console_err
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.TRAVERSAL_PATTERNS]

    def validate_path_component(self, component: str) -> str:
        """
        Validate a single path component for security issues.

        Args:
            component: Single path component (filename or directory name).

        Returns:
            Sanitized component.

        Raises:
            PathSecurityError: If the component contains security issues.
        """
        if not component or component.isspace():
            raise PathSecurityError("Empty or whitespace-only path component")

        # Check for path traversal patterns
        for pattern in self._compiled_patterns:
            if pattern.search(component):
                raise PathSecurityError(f"Path traversal detected in component: {component}")

        # Check for dangerous characters
        for char in self.DANGEROUS_CHARS:
            if char in component:
                raise PathSecurityError(f"Dangerous character '{char}' in path component: {component}")

        # Check for Windows reserved names
        name_without_ext = component.split(".")[0].upper()
        if name_without_ext in self.WINDOWS_RESERVED:
            raise PathSecurityError(f"Reserved filename: {component}")

        # Check for names that are too long
        if len(component) > 255:
            raise PathSecurityError(f"Path component too long: {len(component)} characters")

        return component

    def validate_relative_path(self, path: str | Path, max_depth: int = 10) -> Path:
        """
        Validate a relative path for security issues.

        Args:
            path: Path to validate.
            max_depth: Maximum allowed directory depth.

        Returns:
            Validated Path object.

        Raises:
            PathSecurityError: If the path contains security issues.
        """
        path_str = str(path)

        # Check for null bytes
        if "\x00" in path_str:
            raise PathSecurityError("Null byte in path", path)

        # Normalize path separators for cross-platform compatibility
        normalized_path = path_str.replace("\\", "/")

        # Check for path traversal patterns in the full path
        for pattern in self._compiled_patterns:
            if pattern.search(normalized_path):
                raise PathSecurityError(f"Path traversal detected: {path}", path)

        # Convert to Path object and check each component
        path_obj = Path(normalized_path)
        components = path_obj.parts

        if len(components) > max_depth:
            raise PathSecurityError(f"Path too deep: {len(components)} levels (max: {max_depth})", path)

        # Validate each component
        for component in components:
            self.validate_path_component(component)

        return path_obj

    def validate_within_base(self, path: str | Path, base_dir: str | Path) -> Path:
        """
        Validate that a path stays within a base directory.

        Args:
            path: Path to validate.
            base_dir: Base directory that path must stay within.

        Returns:
            Resolved path that's guaranteed to be within base_dir.

        Raises:
            PathSecurityError: If the path escapes the base directory.
        """
        base_path = Path(base_dir).resolve()

        # First validate the relative path for basic security issues
        validated_relative = self.validate_relative_path(path)

        # Resolve the full path
        try:
            full_path = (base_path / validated_relative).resolve()
        except (OSError, ValueError) as e:
            raise PathSecurityError(f"Invalid path resolution: {e}", path) from e

        # Check that the resolved path is within the base directory
        try:
            full_path.relative_to(base_path)
        except ValueError as e:
            raise PathSecurityError(f"Path escapes base directory: {path}", path) from e

        return full_path

    def sanitize_filename(self, filename: str, replacement: str = "_") -> str:
        """
        Sanitize a filename by replacing dangerous characters.

        Args:
            filename: Filename to sanitize.
            replacement: Character to replace dangerous characters with.

        Returns:
            Sanitized filename.
        """
        if not filename or filename.isspace():
            return "unnamed_file"

        # Replace dangerous characters
        sanitized = filename
        for char in self.DANGEROUS_CHARS:
            sanitized = sanitized.replace(char, replacement)

        # Replace path separators
        sanitized = sanitized.replace("/", replacement).replace("\\", replacement)

        # Check for Windows reserved names
        name_without_ext = sanitized.split(".")[0].upper()
        if name_without_ext in self.WINDOWS_RESERVED:
            sanitized = f"safe_{sanitized}"

        # Trim to reasonable length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            max_name_len = 255 - len(ext)
            sanitized = name[:max_name_len] + ext

        # Ensure it doesn't start/end with dots or spaces
        sanitized = sanitized.strip(". ")

        if not sanitized:
            return "unnamed_file"

        return sanitized

    def validate_url_path(self, url_path: str) -> str:
        """
        Validate a URL path component for security issues.

        Args:
            url_path: URL path to validate.

        Returns:
            Validated URL path.

        Raises:
            PathSecurityError: If the URL path contains security issues.
        """
        if not url_path:
            raise PathSecurityError("Empty URL path")

        # Check for null bytes and control characters
        if any(ord(c) < 32 for c in url_path):
            raise PathSecurityError("Control characters in URL path", url_path)

        # Check for path traversal in URL context
        if "../" in url_path or "..\\" in url_path:
            raise PathSecurityError("Path traversal in URL path", url_path)

        # Validate length
        if len(url_path) > 2048:  # Common URL length limit
            raise PathSecurityError("URL path too long", url_path)

        return url_path


# Global validator instance
_validator = SecurePathValidator()


def validate_path_component(component: str) -> str:
    """Validate a single path component. Convenience function."""
    return _validator.validate_path_component(component)


def validate_relative_path(path: str | Path, max_depth: int = 10) -> Path:
    """Validate a relative path. Convenience function."""
    return _validator.validate_relative_path(path, max_depth)


def validate_within_base(path: str | Path, base_dir: str | Path) -> Path:
    """Validate path stays within base directory. Convenience function."""
    return _validator.validate_within_base(path, base_dir)


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitize a filename. Convenience function."""
    return _validator.sanitize_filename(filename, replacement)


def validate_url_path(url_path: str) -> str:
    """Validate a URL path. Convenience function."""
    return _validator.validate_url_path(url_path)


def secure_path_join(base: str | Path, *components: str) -> Path:
    """
    Securely join path components, ensuring no traversal.

    Args:
        base: Base directory path.
        *components: Path components to join.

    Returns:
        Secure joined path.

    Raises:
        PathSecurityError: If any component is unsafe.
    """
    if not components:
        return Path(base)

    # Validate each component individually
    for component in components:
        validate_path_component(str(component))

    # Join the components
    joined_path = "/".join(str(c) for c in components)

    # Validate the final path within the base
    return validate_within_base(joined_path, base)


def is_safe_download_path(url: str, destination: str | Path, allowed_base: str | Path) -> bool:
    """
    Check if a download destination path is safe.

    Args:
        url: Source URL (for logging/error context).
        destination: Destination file path.
        allowed_base: Base directory that destination must be within.

    Returns:
        True if the path is safe, False otherwise.
    """
    try:
        validate_within_base(destination, allowed_base)
        return True
    except PathSecurityError as e:
        console_err.print(f"[red]Unsafe download path for {url}: {e}[/red]")
        return False
