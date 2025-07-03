"""Lazy loading utilities for performance optimization.

This module provides utilities for lazy importing and loading of modules and components
to reduce startup time and memory usage. It includes a general-purpose lazy import manager
and utilities for command-specific import loading.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any


class LazyImportManager:
    """Manages lazy imports for different command categories."""

    def __init__(self) -> None:
        """Initialize the lazy import manager."""
        self._import_cache: dict[str, Any] = {}

    def get_cached_import(self, module_path: str, item_name: str | None = None) -> Any:
        """Get a cached import or import and cache it.

        Args:
            module_path: Python module path (e.g., 'package.module')
            item_name: Optional specific item to import from module

        Returns:
            The imported module or item

        Example:
            # Import entire module
            json_module = manager.get_cached_import("json")

            # Import specific item from module
            JSONEncoder = manager.get_cached_import("json", "JSONEncoder")
        """
        cache_key = f"{module_path}.{item_name}" if item_name else module_path

        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        # Import the module
        module = importlib.import_module(module_path)

        if item_name:
            # Get specific item from module
            item = getattr(module, item_name)
            self._import_cache[cache_key] = item
            return item
        else:
            # Cache entire module
            self._import_cache[cache_key] = module
            return module

    def clear_cache(self) -> None:
        """Clear the import cache."""
        self._import_cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached imports."""
        return len(self._import_cache)

    def get_cached_modules(self) -> list[str]:
        """Get list of cached module paths."""
        return list(self._import_cache.keys())


class LazyUtilsLoader:
    """Lazy loader for utils modules to reduce startup time."""

    def __init__(self, utils_package: str = "par_gpt.utils") -> None:
        """Initialize the lazy utils loader.

        Args:
            utils_package: Base package path for utils modules
        """
        self._utils_cache: dict[str, Any] = {}
        self._utils_package = utils_package

    def get_utils_item(self, module_name: str, item_name: str) -> Any:
        """Get a specific item from a utils module.

        Args:
            module_name: Name of the utils module (e.g., 'timing')
            item_name: Name of the item to import (e.g., 'TimingRegistry')

        Returns:
            The imported item

        Example:
            timing_registry = loader.get_utils_item("timing", "TimingRegistry")
        """
        cache_key = f"{module_name}.{item_name}"

        if cache_key in self._utils_cache:
            return self._utils_cache[cache_key]

        # Import the utils module
        module = importlib.import_module(f"{self._utils_package}.{module_name}")
        item = getattr(module, item_name)

        self._utils_cache[cache_key] = item
        return item

    def clear_cache(self) -> None:
        """Clear the utils cache."""
        self._utils_cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached utils items."""
        return len(self._utils_cache)


def lazy_import(module_path: str, item_name: str | None = None) -> Any:
    """Convenience function for lazy importing.

    Args:
        module_path: Python module path
        item_name: Optional specific item to import

    Returns:
        The imported module or item

    Example:
        # Import module
        os_module = lazy_import("os")

        # Import specific function
        join_func = lazy_import("os.path", "join")
    """
    manager = LazyImportManager()
    return manager.get_cached_import(module_path, item_name)


def create_lazy_loader(utils_package: str) -> LazyUtilsLoader:
    """Create a lazy utils loader for a specific package.

    Args:
        utils_package: Base package path for utils modules

    Returns:
        Configured LazyUtilsLoader instance

    Example:
        loader = create_lazy_loader("myproject.utils")
        config_class = loader.get_utils_item("config", "ConfigManager")
    """
    return LazyUtilsLoader(utils_package)


def lazy_import_with_fallback(primary_module: str, fallback_module: str, item_name: str | None = None) -> Any:
    """Lazy import with fallback option.

    Args:
        primary_module: Primary module to try importing
        fallback_module: Fallback module if primary fails
        item_name: Optional specific item to import

    Returns:
        The imported module or item

    Raises:
        ImportError: If both primary and fallback modules fail to import

    Example:
        # Try orjson first, fallback to json
        json_module = lazy_import_with_fallback("orjson", "json")
    """
    manager = LazyImportManager()

    try:
        return manager.get_cached_import(primary_module, item_name)
    except ImportError:
        try:
            return manager.get_cached_import(fallback_module, item_name)
        except ImportError as e:
            raise ImportError(f"Failed to import from both {primary_module} and {fallback_module}") from e


class LazyAttribute:
    """Descriptor for lazy attribute loading.

    This descriptor allows for lazy loading of expensive attributes,
    computing them only when first accessed.

    Example:
        class MyClass:
            expensive_data = LazyAttribute(lambda self: compute_expensive_data())

            def compute_expensive_data(self):
                # Expensive computation here
                return "computed data"
    """

    def __init__(self, factory: Callable[[Any], Any]) -> None:
        """Initialize lazy attribute.

        Args:
            factory: Function that computes the attribute value
        """
        self.factory = factory
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the attribute name when attached to a class."""
        self.name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        """Get the attribute value, computing it if necessary."""
        if instance is None:
            return self

        if self.name is None:
            raise RuntimeError("LazyAttribute name not set")

        # Check if value is already cached on the instance
        cache_attr = f"_lazy_{self.name}"
        if hasattr(instance, cache_attr):
            return getattr(instance, cache_attr)

        # Compute and cache the value
        value = self.factory(instance)
        setattr(instance, cache_attr, value)
        return value
