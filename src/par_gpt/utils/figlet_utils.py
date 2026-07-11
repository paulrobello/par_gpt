"""Figlet ASCII-art text generation utilities."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Literal

from par_ai_core.par_logging import console_err
from rich.console import Console

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
    # Import pyfiglet locally for better startup performance
    try:
        import pyfiglet
    except ImportError:
        return "pyfiglet not available"

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
    # Import pyfiglet locally for better startup performance
    try:
        import pyfiglet
    except ImportError:
        return "pyfiglet not available"

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
