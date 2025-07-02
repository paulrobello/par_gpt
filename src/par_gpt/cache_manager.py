"""Disk based cache manager"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import requests
from par_ai_core.user_agents import get_random_user_agent
from par_ai_core.utils import get_file_suffix, is_url

from par_gpt import __application_binary__
from par_gpt.utils.path_security import PathSecurityError, validate_within_base


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

    def _get_secure_cache_path(self, item: str) -> Path:
        """
        Securely get a cache path for an item, preventing directory traversal.

        Args:
            item (str): Item to get cache path for

        Returns:
            Path: Secure cache path

        Raises:
            PathSecurityError: If item contains path traversal attempts
        """
        try:
            # Validate that the item path stays within the cache directory
            return validate_within_base(item, self.cache_dir)
        except PathSecurityError:
            # If direct path fails validation, fall back to the hashed key method
            # This ensures backward compatibility while maintaining security
            return self.get_path(item)

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
            # First try secure direct path (validates against path traversal)
            try:
                path = self._get_secure_cache_path(item)
                if path.exists():
                    return path
            except PathSecurityError:
                # If direct path is unsafe, skip it and only use hashed key
                pass

            # Always try the hashed key path as fallback
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
            # Use secure path resolution to prevent directory traversal
            try:
                path = self._get_secure_cache_path(item)
            except PathSecurityError:
                # If item contains unsafe path, use hashed key method only
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
            # Try secure path first, then fallback to hashed key
            exists = False
            try:
                path = self._get_secure_cache_path(item)
                if path.exists():
                    exists = True
                    path.unlink()
            except PathSecurityError:
                # Skip unsafe direct path
                pass

            # Also try hashed key path
            path = self.get_path(item)
            if path.exists():
                exists = True
                path.unlink()

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
            # Check secure direct path first
            try:
                path = self._get_secure_cache_path(item)
                if path.exists():
                    return True
            except PathSecurityError:
                # Skip unsafe direct path
                pass

            # Always check hashed key path
            return self.get_path(item).exists()


cache_manager = CacheManager()
