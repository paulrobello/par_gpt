"""Timing utilities for performance measurement and profiling.

This module provides utilities for measuring and reporting execution times of various
operations in PAR GPT. It includes context managers, decorators, and a global timing
registry for collecting performance metrics.
"""

import functools
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional, TypeVar

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class TimingData:
    """Data structure for storing timing information."""

    name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if timing measurement is complete."""
        return self.end_time is not None and self.duration is not None

    def complete(self) -> None:
        """Mark timing as complete and calculate duration."""
        if self.end_time is None:
            self.end_time = time.perf_counter()
        if self.duration is None and self.start_time is not None:
            self.duration = self.end_time - self.start_time


class TimingRegistry:
    """Global registry for collecting and managing timing data."""

    _instance: Optional["TimingRegistry"] = None
    _lock = Lock()

    def __new__(cls) -> "TimingRegistry":
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize the timing registry."""
        if getattr(self, "_initialized", False):
            return

        self._timings: dict[str, TimingData] = {}
        self._stack: list[str] = []
        self._enabled = False
        self._console = Console()
        self._initialized = True

    def enable(self) -> None:
        """Enable timing collection."""
        self._enabled = True

    def disable(self) -> None:
        """Disable timing collection."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if timing collection is enabled."""
        return self._enabled

    def clear(self) -> None:
        """Clear all timing data."""
        self._timings.clear()
        self._stack.clear()

    def start_timing(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Start timing an operation.

        Args:
            name: Name of the operation being timed
            metadata: Optional metadata to associate with the timing

        Returns:
            Unique identifier for the timing operation
        """
        if not self._enabled:
            return name

        # Create unique ID if name already exists
        unique_id = name
        counter = 1
        while unique_id in self._timings:
            unique_id = f"{name}_{counter}"
            counter += 1

        # Determine parent
        parent = self._stack[-1] if self._stack else None

        # Create timing data
        timing_data = TimingData(name=name, start_time=time.perf_counter(), parent=parent, metadata=metadata or {})

        self._timings[unique_id] = timing_data

        # Update parent's children
        if parent and parent in self._timings:
            self._timings[parent].children.append(unique_id)

        # Push to stack
        self._stack.append(unique_id)

        return unique_id

    def end_timing(self, timing_id: str) -> float | None:
        """End timing an operation.

        Args:
            timing_id: Unique identifier returned by start_timing

        Returns:
            Duration in seconds, or None if timing not found or disabled
        """
        if not self._enabled or timing_id not in self._timings:
            return None

        timing_data = self._timings[timing_id]
        timing_data.complete()

        # Remove from stack
        if self._stack and self._stack[-1] == timing_id:
            self._stack.pop()

        return timing_data.duration

    def get_timing(self, timing_id: str) -> TimingData | None:
        """Get timing data by ID."""
        return self._timings.get(timing_id)

    def get_all_timings(self) -> dict[str, TimingData]:
        """Get all timing data."""
        return self._timings.copy()

    def get_root_timings(self) -> list[TimingData]:
        """Get all root-level timing data (no parent)."""
        return [timing for timing in self._timings.values() if timing.parent is None]

    def get_summary(self) -> dict[str, float]:
        """Get summary of all completed timings.

        Returns:
            Dictionary mapping operation names to total durations
        """
        summary = {}
        for timing in self._timings.values():
            if timing.is_complete:
                name = timing.name
                duration = timing.duration or 0.0
                if name in summary:
                    summary[name] += duration
                else:
                    summary[name] = duration
        return summary

    def print_summary(self, detailed: bool = False) -> None:
        """Print timing summary to console.

        Args:
            detailed: If True, show detailed hierarchical view
        """
        if not self._enabled or not self._timings:
            return

        if detailed:
            self._print_detailed_summary()
        else:
            self._print_simple_summary()

    def _print_simple_summary(self) -> None:
        """Print simple timing summary table."""
        table = Table(title="Timing Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Total Time", style="green", justify="right")
        table.add_column("Count", style="yellow", justify="right")
        table.add_column("Average", style="blue", justify="right")

        # Aggregate by operation name
        aggregated = {}
        grand_total = 0.0
        total_operations = 0

        for timing in self._timings.values():
            if timing.is_complete:
                name = timing.name
                duration = timing.duration or 0.0
                grand_total += duration
                total_operations += 1

                if name not in aggregated:
                    aggregated[name] = {"total": 0.0, "count": 0}
                aggregated[name]["total"] += duration
                aggregated[name]["count"] += 1

        # Sort by total time
        sorted_ops = sorted(aggregated.items(), key=lambda x: x[1]["total"], reverse=True)

        for name, data in sorted_ops:
            total = data["total"]
            count = data["count"]
            average = total / count if count > 0 else 0.0

            table.add_row(name, f"{total:.3f}s", str(count), f"{average:.3f}s")

        # Add separator and grand total
        if sorted_ops:
            table.add_section()
            overall_average = grand_total / total_operations if total_operations > 0 else 0.0
            table.add_row(
                "[bold]Grand Total[/bold]",
                f"[bold]{grand_total:.3f}s[/bold]",
                f"[bold]{total_operations}[/bold]",
                f"[bold]{overall_average:.3f}s[/bold]",
            )

        self._console.print(table)

    def _print_detailed_summary(self) -> None:
        """Print detailed hierarchical timing summary."""
        # Calculate grand total
        grand_total = 0.0
        total_operations = 0

        for timing in self._timings.values():
            if timing.is_complete:
                grand_total += timing.duration or 0.0
                total_operations += 1

        tree = Tree(f"Timing Details (Grand Total: {grand_total:.3f}s, {total_operations} operations)")

        # Build tree from root timings
        root_timings = self.get_root_timings()
        for root_timing in sorted(root_timings, key=lambda t: t.start_time):
            self._add_timing_to_tree(tree, root_timing)

        self._console.print(tree)

    def _add_timing_to_tree(self, parent_node: Tree, timing: TimingData) -> None:
        """Recursively add timing data to tree."""
        duration_str = f"{timing.duration:.3f}s" if timing.duration else "incomplete"
        node_label = f"{timing.name}: {duration_str}"

        # Add metadata if present
        if timing.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in timing.metadata.items())
            node_label += f" ({metadata_str})"

        node = parent_node.add(node_label)

        # Add children
        for child_id in timing.children:
            if child_id in self._timings:
                child_timing = self._timings[child_id]
                self._add_timing_to_tree(node, child_timing)


# Global timing registry instance
_timing_registry = TimingRegistry()


def enable_timing() -> None:
    """Enable global timing collection."""
    _timing_registry.enable()


def disable_timing() -> None:
    """Disable global timing collection."""
    _timing_registry.disable()


def is_timing_enabled() -> bool:
    """Check if timing is enabled globally."""
    return _timing_registry.is_enabled()


def clear_timings() -> None:
    """Clear all collected timing data."""
    _timing_registry.clear()


def get_timing_summary() -> dict[str, float]:
    """Get summary of all timing data."""
    return _timing_registry.get_summary()


def print_timing_summary(detailed: bool = False) -> None:
    """Print timing summary to console."""
    _timing_registry.print_summary(detailed=detailed)


@contextmanager
def timer(name: str, metadata: dict[str, Any] | None = None) -> Generator[str, None, None]:
    """Context manager for timing operations.

    Args:
        name: Name of the operation being timed
        metadata: Optional metadata to associate with the timing

    Yields:
        Unique timing identifier

    Example:
        with timer("database_query", {"query": "SELECT * FROM users"}):
            # Your code here
            pass
    """
    timing_id = _timing_registry.start_timing(name, metadata)
    try:
        yield timing_id
    finally:
        _timing_registry.end_timing(timing_id)


def timed(name: str | None = None, metadata: dict[str, Any] | None = None) -> Callable[[F], F]:
    """Decorator for timing function execution.

    Args:
        name: Optional name for the timing (defaults to function name)
        metadata: Optional metadata to associate with the timing

    Returns:
        Decorated function

    Example:
        @timed("expensive_calculation")
        def my_function():
            # Your code here
            pass
    """

    def decorator(func: F) -> F:
        timing_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with timer(timing_name, metadata):
                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def time_operation(name: str, operation: Callable[[], Any], metadata: dict[str, Any] | None = None) -> Any:
    """Time a single operation.

    Args:
        name: Name of the operation
        operation: Callable to execute and time
        metadata: Optional metadata to associate with the timing

    Returns:
        Result of the operation

    Example:
        result = time_operation("file_read", lambda: open("file.txt").read())
    """
    with timer(name, metadata):
        return operation()
