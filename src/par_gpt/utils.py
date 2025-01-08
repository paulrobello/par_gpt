"""Utils"""

from __future__ import annotations

import getpass
import hashlib
import os
import platform
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import orjson as json
import pyfiglet
import requests
from par_ai_core.par_logging import console_err
from par_ai_core.user_agents import get_random_user_agent
from rich.console import Console
from rich_pixels import Pixels

# from sixel import converter
# from textual_image.renderable.sixel import query_terminal_support
from . import __application_binary__


def get_url_file_suffix(url: str) -> str:
    """
    Get url file suffix

    Args:
        url (str): URL

    Returns:
        str: File suffix in lowercase with leading dot
    """
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    suffix = os.path.splitext(filename)[1].lower()
    return suffix or ".jpg"


class DownloadCache:
    """Download cache manager"""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if not cache_dir:
            cache_dir = Path(f"~/.{__application_binary__}/cache").expanduser()
        self.cache_dir = Path(cache_dir)

        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for_url(url: str) -> str:
        """
        Convert url to cache key

        Args:
            url (str): URL to compute cache key

        Returns:
            str: Cache key for url
        """
        return hashlib.sha1(url.encode()).hexdigest() + "." + get_url_file_suffix(url)

    def get_path(self, url: str) -> Path:
        """
        Get path in cache for url

        Args:
            url (str): URL to compute cache key

        Returns:
            Path: Path in cache for url
        """
        return self.cache_dir / self.key_for_url(url)

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
        """
        Delete from cache if exists

        Args:
            url (str): URL
        """
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
        timeout (int): Timeout in seconds

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
        timeout (int): Timeout in seconds

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


def show_image_in_terminal(image_path: str | Path, dimension: str = "auto", console: Console | None = None) -> str:
    """
    Show image in terminal.

    Args:
        image_path (str): Image path or URL
        dimension (str, optional): Image dimension in format of WIDTHxHEIGHT, small, medium, large or auto.
        console (Console, optional): Console. Defaults to None.

    Returns:
        str: Status of the operation
    """
    if not console:
        console = console_err
    if not image_path:
        return "Image not found"
    try:
        image_path = str(image_path)
        if image_path.startswith("//"):
            image_path = "https:" + image_path
        if image_path.startswith("http"):
            image_path = download_cache.download(image_path)

        if dimension in ["auto", "small", "medium", "large"]:
            width = console.width
            height = console.height
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

        # sixel_supported = query_terminal_support()
        # if sixel_supported:
        #     console.print(f"using image size {width} x {height}")
        #     if dimension == "auto":
        #         width = None
        #         height = None
        #     else:
        #         r = width / height
        #         width *= r
        #         height *= r * 2
        #         width = int(width)
        #         height = int(height)
        #     c = converter.SixelConverter(image_path, w=width, h=height, chromakey=True, alpha_threshold=0, fast=True)
        #     if console.stderr:
        #         c.write(sys.stderr)
        #     else:
        #         c.write(sys.stdout)
        # else:
        dim = width if width < height else height
        pixels = Pixels.from_image_path(image_path, resize=(dim, dim))
        console.print(pixels)
        return "Image shown in terminal"
    except Exception as e:
        console.print(e)
        return f"Error: {str(e)}"


def mk_env_context(extra_context: dict[str, Any] | str | Path | None = None, console: Console | None = None) -> str:
    """
    Create environment context with optional extra context.

    Args:
        extra_context: Optional extra context to add to the context
            Path will be read and parsed as JSON with fallback to plain text
            Dictionary will append / overwrite existing context
            String will be appended as-is
        console: Optional console to use

    Returns:
        str: The environment context as Markdown string
    """

    if not console:
        console = console_err

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


FigletFontName = Literal[
    "ansi_shadow",
    "3d-ascii",
    "alpha",
    "big_money-se",
    "blocks",
    "bulbhead",
    "doh",
    "impossible",
    "isometric1",
    "slant_relief",
    "caligraphy",
    "jerusalem",
    "pawp",
    "peaks",
    "tinker-toy",
    "big",
    "bloody",
]


def figlet_vertical(
    text: str, font: FigletFontName = "ansi_shadow", colors: list[str] | None = None, console: Console | None = None
) -> str:
    """
    Create a figlet text and output it to the terminal

    Args:
        text (str): The text to convert to figlet
        font (str): The font to use (default: ansi_shadow)
        colors (list[str] | None): The colors to use as a top to bottom gradient (default: ["#FFFF00", "#FFB000", "#FF7800", "#FF3200", "#FF0000"])
        console (Console | None): The console to use

    Returns:
        str: The figlet text

    Notes:
        Calling this tool will send its output directly to the terminal. You do not need to capture the output.
    """

    if not console:
        console = console_err

    text = pyfiglet.figlet_format(text, font=font, width=console.width)

    # Fire gradient colors
    colors = colors or [
        "#FFFF00",  # Bright yellow
        "#FFB000",  # Orange-yellow
        "#FF7800",  # Orange
        "#FF3200",  # Orange-red
        "#FF0000",  # Deep red
    ]

    # Split text into lines and compute lines per color
    lines = text.split("\n")
    num_lines = len(lines)
    lines_per_color = num_lines / len(colors)

    # Create gradient text
    styled_lines = []
    for i, line in enumerate(lines):
        color_index = int(i / lines_per_color)
        if color_index >= len(colors):
            color_index = len(colors) - 1
        styled_lines.append(f"[{colors[color_index]}]{line}")

    # Join print and capture output
    io_buffer = StringIO()
    with redirect_stdout(io_buffer):
        with redirect_stderr(io_buffer):
            console.print("\n".join(styled_lines))

    ret = io_buffer.getvalue()
    # the llm often messes up the colors so we output before we send to llm
    print(ret)

    return ret


def figlet_horizontal(
    text: str, font: FigletFontName = "ansi_shadow", colors: list[str] | None = None, console: Console | None = None
) -> str:
    """
    Create a figlet text and output it to the terminal

    Args:
        text (str): The text to convert to figlet
        font (str): The font to use (default: ansi_shadow)
        colors (list[str] | None): The colors to use as a gradient applied to each letter left to right (default: ["#FFFF00", "#FFB000", "#FF7800", "#FF3200", "#FF0000"])
        console (Console | None): The console to use

    Returns:
        str: The figlet text

    Notes:
        Calling this tool will send its output directly to the terminal. You do not need to capture the output.
    """

    if not console:
        console = console_err

    # Known issue that fonts that overlap letters will not be overlapped as we render each letter separately
    max_height: int = 0
    figlet_chars: list[str] = []
    # used to pad figlet chars to max height
    space_char_indexes: list[int] = []
    # used to not change colors for space characters

    # loop over each letter and generate figlet letter
    for i, letter in enumerate(text):
        if letter == " ":
            space_char_indexes.append(i)
        figlet_chars.append(pyfiglet.figlet_format(letter, font=font, width=console.width))
        # figlet wraps at 80 chars by default override with actual console width

        # break char into lines to get max height for padding
        char_lines = figlet_chars[i].split("\n")
        if len(char_lines) > max_height:
            max_height = len(char_lines) - 1

    letters = []
    # pad figlet chars to max height
    for letter in figlet_chars:
        char_lines = letter.split("\n")
        if len(char_lines) < max_height:
            char_lines += [""] * (max_height - len(char_lines))
        letters.append("\n".join(char_lines))

    # Fire gradient colors
    colors = colors or [
        "#FFFF00",  # Bright yellow
        "#FFB000",  # Orange-yellow
        "#FF7800",  # Orange
        "#FF3200",  # Orange-red
        "#FF0000",  # Deep red
    ]

    # Create gradient text
    styled_lines = []
    for y in range(max_height):
        color_index: int = 0
        line: str = ""
        # loop over each letter and apply color for current line
        for i, letter in enumerate(letters):
            # escape format char [
            char_line = letter.split("\n")[y].replace("[", "\\[")
            # if last char is \, escape it so it does not interfere with color change
            if char_line and char_line[-1] == "\\":
                char_line += "\\"
            # apply color to current strip of text
            line += f"[{colors[color_index]}]{char_line}[/{colors[color_index]}]"
            # move to next color if not a space
            if i not in space_char_indexes:
                color_index = (color_index + 1) % len(colors)
        styled_lines.append(line)

    # Join print and capture output
    io_buffer = StringIO()
    with redirect_stdout(io_buffer):
        with redirect_stderr(io_buffer):
            console.print("\n".join(styled_lines))
            # print("\n".join(styled_lines))

    ret = io_buffer.getvalue()

    # the llm often messes up the colors so we output before we send to llm
    print(ret)

    return ret
