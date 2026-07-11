"""Process-wide singletons shared across par_gpt.utils submodules.

These live in a dedicated leaf module so that domain submodules can import a
single shared instance without creating an import cycle with the package
``__init__`` and without re-creating the instance per import.
"""

from __future__ import annotations

from par_utils import CacheManager

# Single shared cache manager instance (constructed exactly once via normal
# Python module caching in sys.modules). Previously this lived at the top of
# the legacy ``utils.py`` which was re-executed off-disk on every facade fetch,
# fragmenting the singleton.
cache_manager = CacheManager()
