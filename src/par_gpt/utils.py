"""Utils"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from rich_pixels import Pixels
from rich.console import Console

from .lib.user_agents import get_random_user_agent
from . import __application_binary__


def get_url_file_suffix(url):
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    suffix = os.path.splitext(filename)[1]
    return suffix or ".jpg"


class DownloadCache:
    """Download cache"""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if not cache_dir:
            cache_dir = Path(f"~/.{__application_binary__}/cache").expanduser()
        self.cache_dir = Path(cache_dir)

        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for_url(url: str) -> str:
        """Key for url"""
        return hashlib.sha1(url.encode()).hexdigest() + "." + get_url_file_suffix(url)

    def get_path(self, url: str) -> Path:
        """Get path"""
        return self.cache_dir / self.key_for_url(url)

    def download(self, url: str, force: bool = False) -> Path:
        """Return from cache or download"""
        path = self.get_path(url)
        if not force and path.exists():
            return path
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": get_random_user_agent()},
        )
        response.raise_for_status()

        path.write_bytes(response.content)
        return path

    def delete(self, url: str) -> None:
        """Delete from cache if exists"""
        self.get_path(url).unlink(missing_ok=True)


download_cache = DownloadCache()


def safe_abs_path(res):
    """Gives an abs path, which safely returns a full (not 8.3) windows path"""
    res = Path(res).resolve()
    return str(res)


def get_weather_current(location: str) -> dict[str, Any]:
    """
    Get current weather

    Args:
        location (str): Location

    Returns:
        str: Weather
    """
    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/current.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&aqi=no",
        timeout=10,
    )
    return response.json()


def get_weather_forecast(location: str, num_days: int) -> dict[str, Any]:
    """
    Get weather forecast for next days

    Args:
        location (str): Location
        num_days (int): Number of days

    Returns:
        str: Weather
    """
    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/forecast.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&days={num_days}&aqi=no&alerts=no",
        timeout=10,
    )
    return response.json()


def show_image_in_terminal(image_path: str | Path, dimension: str = "auto", io: Console | None = None) -> str:
    """
    Show image in terminal.

    Args:
        image_path (str): Image path or URL
        dimension (str, optional): Image dimension in format of WIDTHxHEIGHT, small, medium, large or auto.
        io (Console, optional): Console. Defaults to None.

    Returns:
        str: Status of the operation
    """
    if not io:
        io = Console(stderr=True)
    if not image_path:
        return "Image not found"
    try:
        if str(image_path).startswith("http"):
            image_path = download_cache.download(str(image_path))

        if dimension in ["auto", "small", "medium", "large"]:
            width = io.width
            height = io.height
            if dimension == "small":
                width = width // 3
                height = height // 3
            elif dimension == "medium":
                width = width // 2
                height = height // 2
            elif dimension == "large":
                width = width * 2 - 2
                height = height * 2 - 2
        else:
            if "x" in dimension:
                width, height = (int(x) for x in dimension.split("x"))
            else:
                width = height = int(dimension)

        dim = width if width < height else height
        pixels = Pixels.from_image_path(image_path, resize=(dim, dim))
        io.print(pixels)
        return "Image shown in terminal"
    except Exception as e:
        return f"Error: {str(e)}"
