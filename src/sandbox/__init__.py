"""Run Python code in an isolated Docker container.

This package provides functionality to execute Python code safely in Docker
containers. The implementation lives in :mod:`sandbox.runner`; ``docker`` is
imported lazily so ``import sandbox`` does not eagerly pull the Docker SDK
(ARC-013).

Public API is re-exported here for backward compatibility —
``from sandbox import SandboxRun`` continues to work unchanged.
"""

from __future__ import annotations

from .runner import (
    ExecuteCommandResult,
    PathSecurityError,
    SandboxAction,
    SandboxCopyFromResult,
    SandboxRun,
    SandboxRunResult,
    install_sandbox,
    sanitize_filename,
    start_sandbox,
    stop_sandbox,
)

__all__ = [
    "ExecuteCommandResult",
    "PathSecurityError",
    "SandboxAction",
    "SandboxCopyFromResult",
    "SandboxRun",
    "SandboxRunResult",
    "install_sandbox",
    "sanitize_filename",
    "start_sandbox",
    "stop_sandbox",
]
