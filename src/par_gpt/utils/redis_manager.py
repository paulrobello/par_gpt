"""Redis operation management utilities for consistent error handling."""

from __future__ import annotations

import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any, TypeVar

import redis
from par_ai_core.par_logging import console_err
from rich.console import Console

from par_gpt import __env_var_prefix__

F = TypeVar("F", bound=Callable[..., Any])


class RedisOperationManager:
    """Manages Redis operations with consistent error handling."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db: int | None = None,
        password: str | None = None,
        console: Console | None = None,
    ):
        """
        Initialize Redis operation manager.

        Args:
            host: Redis host. Defaults to environment variable or localhost.
            port: Redis port. Defaults to environment variable or 6379.
            db: Redis database number. Defaults to environment variable or 0.
            password: Redis password. Defaults to environment variable.
            console: Console for output. Defaults to console_err.
        """
        self.host = host or os.getenv(f"{__env_var_prefix__}_REDIS_HOST", "localhost")
        self.port = int(port or os.getenv(f"{__env_var_prefix__}_REDIS_PORT", "6379"))
        self.db = int(db or os.getenv(f"{__env_var_prefix__}_REDIS_DB", "0"))
        self.password = password or os.getenv(f"{__env_var_prefix__}_REDIS_PASSWORD")
        self.console = console or console_err
        self._client: redis.Redis | None = None

    def get_client(self) -> redis.Redis | None:
        """
        Get Redis client instance.

        Returns:
            Redis client or None if connection fails.
        """
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                self._client.ping()
            except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
                if self.console:
                    self.console.print(f"[red]Redis connection failed: {e}[/red]")
                self._client = None
        return self._client

    @contextmanager
    def redis_operation(self, operation_name: str = "Redis operation") -> Generator[redis.Redis | None]:
        """
        Context manager for Redis operations with error handling.

        Args:
            operation_name: Name of the operation for error messages.

        Yields:
            Redis client or None if connection fails.
        """
        client = self.get_client()
        if not client:
            yield None
            return

        try:
            yield client
        except redis.RedisError as e:
            if self.console:
                self.console.print(f"[red]{operation_name} failed: {e}[/red]")
            yield None
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Unexpected error in {operation_name}: {e}[/red]")
            yield None

    def safe_execute(self, func: Callable[..., Any], default: Any = None, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a Redis operation safely with error handling.

        Args:
            func: Function to execute with Redis client.
            default: Default value to return on error.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Result of the function or default value on error.
        """
        with self.redis_operation(f"Redis {func.__name__}") as client:
            if client:
                try:
                    return func(client, *args, **kwargs)
                except Exception:
                    return default
        return default

    def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            self._client.close()
            self._client = None


def with_redis_fallback(default: Any = None) -> Callable[[F], F]:
    """
    Decorator for functions that use Redis with automatic fallback.

    Args:
        default: Default value to return if Redis operation fails.

    Returns:
        Decorator function.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract Redis manager from kwargs or create new one
            manager = kwargs.pop("redis_manager", None)
            if manager is None:
                manager = RedisOperationManager()

            try:
                # Inject Redis client into function
                with manager.redis_operation(f"{func.__name__}") as client:
                    if client:
                        kwargs["redis_client"] = client
                        return func(*args, **kwargs)
                    return default
            except Exception:
                return default

        return wrapper  # type: ignore

    return decorator


# Global Redis manager instance and enable flag
_redis_manager: RedisOperationManager | None = None
_redis_enabled: bool = True


def set_redis_enabled(enabled: bool) -> None:
    """Set whether Redis is globally enabled."""
    global _redis_enabled
    _redis_enabled = enabled


def is_redis_enabled() -> bool:
    """Check if Redis is globally enabled."""
    return _redis_enabled


def get_redis_manager() -> RedisOperationManager:
    """Get the global Redis manager instance."""
    global _redis_manager
    if not _redis_enabled:
        # Return a dummy manager that never connects when Redis is disabled
        class DisabledRedisManager:
            def get_client(self):
                return None

            def redis_operation(self, operation_name="Redis operation"):
                from contextlib import nullcontext

                return nullcontext(None)

            def safe_execute(self, func, default=None, *args, **kwargs):
                return default

            def close(self):
                pass

        return DisabledRedisManager()  # type: ignore

    if _redis_manager is None:
        _redis_manager = RedisOperationManager()
    return _redis_manager


def reset_redis_manager() -> None:
    """Reset the global Redis manager instance."""
    global _redis_manager
    if _redis_manager:
        _redis_manager.close()
    _redis_manager = None
