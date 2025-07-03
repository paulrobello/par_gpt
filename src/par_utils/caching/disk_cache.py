"""Disk based cache manager with security features."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import requests

from par_utils.security.path_validation import PathSecurityError, validate_within_base


def get_file_suffix(filename: str) -> str:
    """Get file suffix/extension from filename or URL.

    Args:
        filename: Filename or URL to extract suffix from

    Returns:
        File suffix including the dot (e.g., '.txt', '.json')
    """
    path = Path(filename)
    return path.suffix


def is_url(text: str) -> bool:
    """Check if text is a URL.

    Args:
        text: Text to check

    Returns:
        True if text appears to be a URL
    """
    return text.startswith(("http://", "https://", "ftp://", "ftps://"))


def get_random_user_agent() -> str:
    """Get a random user agent string.

    Returns:
        User agent string
    """
    return "Mozilla/5.0 (compatible; par_utils/1.0)"


class CacheManager:
    """Thread-safe cache manager with URL download support and security features."""

    def __init__(self, cache_dir: str | Path | None = None, app_name: str = "par_utils") -> None:
        """Initialize cache manager.

        Args:
            cache_dir: Cache directory path (defaults to ~/.{app_name}/cache)
            app_name: Application name for default cache directory
        """
        if not cache_dir:
            cache_dir = Path(f"~/.{app_name}/cache")
        self.cache_dir = Path(cache_dir).expanduser()
        self.lock = threading.Lock()

        with self.lock:
            if not self.cache_dir.exists():
                self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for_item(item: str) -> str:
        """Convert item path to cache key.

        Args:
            item: Item to compute cache key for

        Returns:
            Cache key for item
        """
        key = hashlib.sha1(item.encode()).hexdigest()
        return key + get_file_suffix(item)

    def get_path(self, item: str) -> Path:
        """Get path in cache for item.

        Args:
            item: Item to compute cache key for

        Returns:
            Path in cache for item
        """
        return self.cache_dir / self.key_for_item(item)

    def _get_secure_cache_path(self, item: str) -> Path:
        """Securely get a cache path for an item, preventing directory traversal.

        Args:
            item: Item to get cache path for

        Returns:
            Secure cache path

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

    def download(self, url: str, force: bool = False, timeout: int = 10, headers: dict[str, str] | None = None) -> Path:
        """Return file from cache or download.

        Args:
            url: URL to download
            force: Force download even if cached
            timeout: Timeout in seconds for download
            headers: Additional headers for the request

        Returns:
            Path in cache for URL

        Raises:
            requests.exceptions.RequestException: If download fails
        """
        path = self.get_path(url)

        # Check cache first with lock
        if not force:
            with self.lock:
                if path.exists():
                    return path

        # Prepare headers
        request_headers = {"User-Agent": get_random_user_agent()}
        if headers:
            request_headers.update(headers)

        # Download if needed
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=request_headers,
        )
        response.raise_for_status()

        # Write to cache with lock
        with self.lock:
            path.write_bytes(response.content)
            return path

    def get_item(self, item: str, force: bool = False, timeout: int = 10) -> Path:
        """Get file path for key if it exists.

        Args:
            item: Key or item to used to compute cache key
            force: Force download if item is URL
            timeout: Timeout in seconds for downloads

        Returns:
            Path in cache for item

        Raises:
            FileNotFoundError: If key not found in cache
        """
        # If key is a URL, use download method to fetch if needed
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
        """Write value to cache for key.

        Args:
            item: Item or Key
            value: Value to cache

        Returns:
            Path in cache for item
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
        """Delete key from cache if exists.

        Args:
            item: Item/key to delete from cache

        Returns:
            True if item/key exists, False otherwise
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
        """Check if item/key exists in cache.

        Args:
            item: Item or key to check in cache

        Returns:
            True if item/key exists, False otherwise
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

    def clear_cache(self) -> int:
        """Clear all items from cache.

        Returns:
            Number of items removed
        """
        with self.lock:
            count = 0
            if self.cache_dir.exists():
                for item in self.cache_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                        count += 1
            return count

    def get_cache_size(self) -> int:
        """Get number of items in cache.

        Returns:
            Number of cached items
        """
        with self.lock:
            if not self.cache_dir.exists():
                return 0
            return sum(1 for item in self.cache_dir.iterdir() if item.is_file())

    def get_cache_size_bytes(self) -> int:
        """Get total size of cache in bytes.

        Returns:
            Total cache size in bytes
        """
        with self.lock:
            if not self.cache_dir.exists():
                return 0
            return sum(item.stat().st_size for item in self.cache_dir.iterdir() if item.is_file())


def create_cache_manager(cache_dir: str | Path | None = None, app_name: str = "par_utils") -> CacheManager:
    """Create a cache manager instance.

    Args:
        cache_dir: Cache directory path
        app_name: Application name for default cache directory

    Returns:
        CacheManager instance
    """
    return CacheManager(cache_dir, app_name)
