"""Low-level Redis client construction.

This is distinct from ``redis_manager`` which provides the
``RedisOperationManager`` / ``with_redis_fallback`` higher-level helpers.
"""

from __future__ import annotations

import os
from functools import lru_cache

from par_gpt import __env_var_prefix__


@lru_cache(maxsize=1)
def get_redis_client(
    *, host: str | None = None, port: int | None = None, db: int | None = None, password: str | None = None
):
    """
    Create a Redis client using environment variables or default values.

    Args:
        host (str | None): The Redis host. Defaults to None.
        port (int | None): The Redis port. Defaults to None.
        db (int | None): The Redis database. Defaults to None.
        password (str | None): The Redis password. Defaults to None.

    Returns:
        redis.Redis | None: The Redis client instance or None if the connection fails.
    """
    # Import redis locally for better startup performance
    try:
        import redis
    except ImportError:
        return None

    try:
        redis_host = (
            host or os.environ.get(f"{__env_var_prefix__}_REDIS_HOST") or os.environ.get("REDIS_HOST") or "localhost"
        )
        redis_port = port or int(
            os.environ.get(f"{__env_var_prefix__}_REDIS_PORT") or os.environ.get("REDIS_PORT") or "6379"
        )
        redis_db = db or int(os.environ.get(f"{__env_var_prefix__}_REDIS_DB") or os.environ.get("REDIS_DB") or "0")
        redis_password = (
            password or os.environ.get(f"{__env_var_prefix__}_REDIS_PASSWORD") or os.environ.get("REDIS_PASSWORD")
        )

        return redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)
    except Exception as _:
        return None
