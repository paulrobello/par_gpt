from __future__ import annotations

import os
from pathlib import Path

from par_ai_core.par_logging import console_err

from par_gpt import __env_var_prefix__
from par_gpt.utils import get_redis_manager, with_redis_fallback


def get_memory_user() -> str:
    """
    Return the key used to access memories for the current user.
    """
    return os.environ.get(f"{__env_var_prefix__}_USER") or os.environ.get("USER") or "user"


@with_redis_fallback(default=False)
def add_memory_redis(key: str, memory: str | list[str], *, redis_client=None) -> bool:
    """
    Save a memory string or a list of memory strings to Redis.

    Args:
        key (str): The key under which to save the memory in Redis.
        memory (str | list[str]): The memory string or list of memory strings to save.

    Returns:
        bool: True if the memory was saved successfully, False otherwise.
    """
    if not redis_client:
        return False

    if isinstance(memory, str):
        memory = [memory]
    memory = [m.strip() for m in memory]
    redis_client.rpush(key, *memory)
    return True


@with_redis_fallback(default=[])
def list_memories_redis(key: str, *, redis_client=None) -> list[str]:
    """
    Retrieve all memories associated with a given key from Redis.

    Args:
        key (str): The key under which the memories are stored.

    Returns:
        list[str]: A list of memory strings associated with the given key. If no memories are found, an empty list is returned.
    """
    if not redis_client:
        return []

    memories = redis_client.lrange(key, 0, -1)
    return [str(memory) for memory in memories]


def remove_memory_redis(key: str, memory: str) -> bool:
    """
    Remove a specific memory from Redis based on its value.

    Args:
        key (str): The key under which the memories are stored.
        memory (str): The memory string to remove.

    Returns:
        bool: True if the memory was removed successfully, False otherwise.
    """
    try:
        memories = list_memories_redis(key)
        if memory in memories:
            manager = get_redis_manager()
            with manager.redis_operation("remove memory") as client:
                if client:
                    return client.lrem(key, 1, memory) == 1
                return False
        return False
    except Exception as _:
        # console_err.print(f"Error removing memory from Redis: {e}")
        return False


def clear_memories_redis(key: str) -> bool:
    """
    Clear all memories associated with a given key from Redis.

    Args:
        key (str): The key under which the memories are stored.

    Returns:
        bool: True if all memories were removed successfully, False otherwise.
    """
    try:
        manager = get_redis_manager()
        with manager.redis_operation("clear memories") as client:
            if client:
                client.delete(key)
                return True
            return False
    except Exception as _:
        # console_err.print(f"Error removing memory from Redis: {e}")
        return False


def get_memory_prompt() -> str:
    """
    Retrieve all memories associated with the current user and format them as a prompt.

    Returns:
        str: A formatted prompt containing the memories.
    """
    # Check if Redis is enabled before attempting to get memories
    from par_gpt.utils.redis_manager import is_redis_enabled

    if not is_redis_enabled():
        return ""

    memories = ("\n".join(list_memories_redis(get_memory_user()))).strip()
    if not memories:
        return ""
    return f"""
<user_info>
The following are memories you have collected from previous interactions with the user. They may be useful in fulfilling or personalizing responses.
<memories>
{memories}
</memories>
</user_info>
"""


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path("~/.par_gpt.env").expanduser())
    console_err.print(list_memories_redis("user"))
