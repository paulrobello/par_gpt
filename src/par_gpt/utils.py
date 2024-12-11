"""Utils"""

from __future__ import annotations

import getpass
import hashlib
import os
import platform
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import orjson as json
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

    def download(self, url: str, force: bool = False, timeout: int = 10) -> Path:
        """Return from cache or download"""
        path = self.get_path(url)
        if not force and path.exists():
            return path
        response = requests.get(
            url,
            timeout=timeout,
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
    return str(Path(res).resolve())


def get_weather_current(location: str, timeout: int = 10) -> dict[str, Any]:
    """
    Get current weather

    Args:
        location (str): Location
        timeout (int): Timeout

    Returns:
        str: Weather
    """
    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/current.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&aqi=no",
        timeout=timeout,
    )
    return response.json()


def get_weather_forecast(location: str, num_days: int, timeout: int = 10) -> dict[str, Any]:
    """
    Get weather forecast for next days

    Args:
        location (str): Location
        num_days (int): Number of days
        timeout (int): Timeout

    Returns:
        str: Weather
    """
    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/forecast.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&days={num_days}&aqi=no&alerts=no",
        timeout=timeout,
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
        image_path = str(image_path)
        if image_path.startswith("//"):
            image_path = "https:" + image_path
        if image_path.startswith("http"):
            image_path = download_cache.download(image_path)

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


def mk_env_context(extra_context: dict[str, Any] | str | Path | None = None, console: Console | None = None) -> str:
    """
    Create environment context with optional extra context.

    Args:
        extra_context: Optional extra context to add to the context
            Path will be read and parsed as JSON with fallback to plain text
            Dictionary will append / overwrite existing context
            String will be appended as-is

    Returns:
        str: The environment context as Markdown string
    """
    if extra_context is None:
        extra_context = {}

    extra_context_text = ""

    if isinstance(extra_context, Path):
        if not extra_context.is_file():
            raise ValueError(f"Extra context file not found or is not a file: {extra_context}")
        try:
            extra_context = json.loads(extra_context.read_text(encoding="utf-8"))
        except Exception as _:
            extra_context = extra_context.read_text(encoding="utf-8").strip()

    if isinstance(extra_context, dict):
        for k, v in extra_context.items():
            extra_context[k] = str(v)
    elif isinstance(extra_context, (str | list)):
        extra_context_text = str(extra_context)
        extra_context = {}

    extra_context_text = "\n" + extra_context_text.strip()

    if not console:
        console = Console(stderr=True)

    return (
        (
            "<extra_context>\n"
            + "\n".join(
                [
                    f"<{k}>{v}</{k}>"
                    for k, v in (
                        {
                            "username": getpass.getuser(),
                            "home_directory": Path("~").expanduser().as_posix(),
                            "current_directory": Path(os.getcwd()).expanduser().as_posix(),
                            "current_date_and_time": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "platform": platform.platform(aliased=True, terse=True),
                            "shell": Path(os.environ.get("SHELL", "bash")).stem,
                            "term": os.environ.get("TERM", "xterm-256color"),
                            "terminal_dimensions": f"{console.width}x{console.height}",
                        }
                        | extra_context
                    ).items()  # type: ignore
                ]
            )
            + "\n"
        )
        + extra_context_text
        + "\n</extra_context>\n"
    )
