"""Disk based cache manager"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import requests
from par_ai_core.user_agents import get_random_user_agent
from par_ai_core.utils import get_file_suffix, is_url

from par_gpt import __application_binary__


class CacheManager:
    """Thread-safe cache manager with url download support"""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if not cache_dir:
            cache_dir = Path(f"~/.{__application_binary__}/cache")
        self.cache_dir = Path(cache_dir).expanduser()
        self.lock = threading.Lock()

        with self.lock:
            if not self.cache_dir.exists():
                self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for_item(item: str) -> str:
        """
        Convert item path to cache key

        Args:
            item (str): item to compute cache key for

        Returns:
            str: Cache key for item
        """
        key = hashlib.sha1(item.encode()).hexdigest()
        return key + get_file_suffix(item)

    def get_path(self, item: str) -> Path:
        """
        Get path in cache for item

        Args:
            item (str): item to compute cache key for

        Returns:
            Path: Path in cache for item
        """
        return self.cache_dir / self.key_for_item(item)

    def download(self, url: str, force: bool = False, timeout: int = 10) -> Path:
        """
        Return file from cache or download

        Args:
            url (str): URL
            force (bool): Force download
            timeout (int): Timeout in seconds for download

        Returns:
            Path: Path in cache for url

        Raises:
            requests.exceptions.RequestException: If download fails
        """
        path = self.get_path(url)

        # Check cache first with lock
        if not force:
            with self.lock:
                if path.exists():
                    return path

        # Download if needed
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": get_random_user_agent()},
        )
        response.raise_for_status()

        # Write to cache with lock
        with self.lock:
            path.write_bytes(response.content)
            return path

    def get_item(self, item: str, force: bool = False, timeout: int = 10) -> Path:
        """
        Get file path for key if it exists

        Args:
            item (str): key or item to used to compute cache key
            force (bool): Force download if item is URL
            timeout (int): Timeout in seconds for downloads

        Returns:
            Path: Path in cache for item

        Raises:
            FileNotFoundError: If key not found in cache
        """

        # if key is a URL, use download method to fetch if needed
        if is_url(item):
            return self.download(item, force, timeout)

        with self.lock:
            # check if item is a key in cache
            path = self.cache_dir / item
            if path.exists():
                return path
            # compute cache key for item
            path = self.get_path(item)
            if path.exists():
                return path
        raise FileNotFoundError(f"Key '{item}' not found in cache")

    def set_item(self, item: str, value: bytes | str) -> Path:
        """
        Write value to cache for key

        Args:
            item (str): Item or Key
            value (bytes | str): Value to cache

        Returns:
            Path: Path in cache for item
        """
        with self.lock:
            path = self.cache_dir / item
            if not path.exists():
                path = self.get_path(item)

            if isinstance(value, str):
                value = value.encode()
            path.write_bytes(value)
            return path

    def delete_item(self, item: str) -> bool:
        """
        Delete key from cache if exists

        Args:
            item (str): item / key to delete from cache

        Returns:
            bool: True if item / key exists, False otherwise
        """
        with self.lock:
            path = self.cache_dir / item
            if not path.exists():
                path = self.get_path(item)
            exists = path.exists()
            path.unlink(missing_ok=True)
            return exists

    def item_exists(self, item: str) -> bool:
        """
        Check if item / key exists in cache

        Args:
            item (str): Item or key to check in cache

        Returns:
            bool: True if item / key exists, False otherwise
        """
        with self.lock:
            path = self.cache_dir / item
            if path.exists():
                return True

            return self.get_path(item).exists()


cache_manager = CacheManager()
