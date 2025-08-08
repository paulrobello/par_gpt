"""Par Gpt."""

from __future__ import annotations

import os
import warnings

# Defer global initializations to lazy loading for better startup performance
_clipman_initialized = False
_warnings_configured = False


def _init_clipman():
    """Initialize clipboard manager lazily."""
    global _clipman_initialized
    if not _clipman_initialized:
        try:
            import clipman

            clipman.init()
        except Exception as _:
            pass
        _clipman_initialized = True


def _configure_warnings():
    """Configure warnings lazily."""
    global _warnings_configured
    if not _warnings_configured:
        try:
            from langchain_core._api import LangChainBetaWarning, LangChainDeprecationWarning

            warnings.simplefilter("ignore", category=LangChainDeprecationWarning)
            warnings.simplefilter("ignore", category=LangChainBetaWarning)
        except ImportError:
            pass

        warnings.simplefilter("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain.*")
        _warnings_configured = True


def ensure_initialized():
    """Ensure all global initialization is done."""
    _configure_warnings()
    _init_clipman()


__author__ = "Paul Robello"
__credits__ = ["Paul Robello"]
__maintainer__ = "Paul Robello"
__email__ = "probello@gmail.com"
__version__ = "0.14.0"
__application_title__ = "Par Gpt"
__application_binary__ = "par_gpt"
__env_var_prefix__ = "PARGPT"

__licence__ = "MIT"


os.environ["USER_AGENT"] = f"{__application_title__} {__version__}"


__all__: list[str] = [
    "__author__",
    "__credits__",
    "__maintainer__",
    "__email__",
    "__version__",
    "__application_binary__",
    "__licence__",
    "__application_title__",
    "__env_var_prefix__",
]
