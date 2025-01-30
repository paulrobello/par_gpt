"""Par Gpt."""

from __future__ import annotations

import os
import warnings

import clipman
from langchain._api import LangChainDeprecationWarning
from langchain_core._api import LangChainBetaWarning

warnings.simplefilter("ignore", category=LangChainDeprecationWarning)
warnings.simplefilter("ignore", category=LangChainBetaWarning)

try:
    clipman.init()
except Exception as _:
    pass


__author__ = "Paul Robello"
__credits__ = ["Paul Robello"]
__maintainer__ = "Paul Robello"
__email__ = "probello@gmail.com"
__version__ = "0.6.0"
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
