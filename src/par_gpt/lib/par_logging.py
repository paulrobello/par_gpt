"""Logging handler using rich."""

from __future__ import annotations

import logging
import os

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

console_out = Console()
console_err = Console(stderr=True)

install(max_frames=10, show_locals=True, console=console_err)

log_level = os.environ.get("PARAI_LOG_LEVEL", "ERROR")

logging.basicConfig(
    level=log_level,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console_err, markup=True, tracebacks_max_frames=10)],
)

log = logging.getLogger("par_ai")
