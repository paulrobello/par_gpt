"""Utils"""

from __future__ import annotations

import getpass
import importlib
import io
import os
import platform
import subprocess
import sys
import tomllib
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Literal

import orjson as json
import PIL.Image
import pyfiglet
import requests
import tomli_w
from packaging.requirements import Requirement
from packaging.version import parse
from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_image_utils import image_to_base64, image_to_chat_message, try_get_image_type
from par_ai_core.llm_providers import LlmProvider
from par_ai_core.par_logging import console_err
from PIL import Image
from pydantic import BaseModel, Field
from rich.console import Console
from rich_pixels import Pixels
from sixel import converter as sixel_converter
from strenum import StrEnum
from textual_image.renderable.sixel import query_terminal_support as sixel_query_terminal_support

from par_gpt.cache_manger import cache_manager

try:
    sixel_supported = sixel_query_terminal_support()
except Exception:
    sixel_supported = False


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


def show_image_in_terminal(
    image_path: str | Path, dimension: str = "auto", no_sixel: bool = False, console: Console | None = None
) -> str:
    """
    Show image in terminal.

    Args:
        image_path (str): Image path or URL
        dimension (str, optional): Image dimension in format of WIDTHxHEIGHT, small, medium, large or auto.
        no_sixel (bool, optional): Disable use of sixel even if its supported. Defaults to False.
        console (Console, optional): Console. Defaults to stderr.

    Returns:
        str: Status of the operation

    Raises:
        ValueError: If image_path not specified or invalid.
    """
    if not console:
        console = console_err
    if not image_path:
        raise ValueError("Image path or URL is required")

    try:
        if not isinstance(image_path, str):
            image_path = str(image_path)
        if image_path.startswith("//"):
            image_path = "https:" + image_path
        if image_path.startswith("http"):
            image_path = cache_manager.download(image_path)

        image_path = Path(image_path).expanduser()
        if not image_path.exists():
            return "Image not found"

        if dimension in ["auto", "small", "medium", "large"]:
            if sixel_supported:
                width = console.width * 8
                height = console.height * 16
            else:
                width = console.width * 2
                height = console.height * 2
            if dimension == "small":
                width = round(width * 0.25)
                height = round(height * 0.25)
            elif dimension == "medium":
                width = round(width * 0.5)
                height = round(height * 0.5)
            elif dimension == "large":
                width = round(width * 0.75)
                height = round(height * 0.75)
        else:
            if "x" in dimension:
                width, height = (int(x) for x in dimension.split("x"))
            else:
                width = height = int(dimension)
        if not width or not height:
            return "Invalid dimension"

        image = Image.open(image_path)
        w, h = image.size

        width_scale = width / w
        height_scale = height / h
        scale = min(width_scale, height_scale)
        new_image_width = round(w * scale)
        new_image_height = round(h * scale)
        # console.print(f"Image size {w} x {h} : Console {dimension}: {width} x {height} : {scale}")

        if sixel_supported and not no_sixel:
            c = sixel_converter.SixelConverter(
                image_path, w=new_image_width, h=new_image_height, chromakey=True, alpha_threshold=0, fast=True
            )
            if console.stderr:
                c.write(sys.__stderr__)
            else:
                c.write(sys.__stdout__)

            return "Image shown in terminal"
        pixels = Pixels.from_image(image, resize=(new_image_width, new_image_height - 2))
        console.print(pixels)
        return "Image shown in terminal"
    except Exception as e:
        console.print(e)
        console.print_exception()

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


class VisibleWindow(BaseModel):
    """Info about Visible Windows"""

    app_name: str = Field(..., description="Name of the application")
    app_title: str = Field(..., description="Current content of the application's title bar")
    window_id: int = Field(..., description="Window ID of the application. Required by some other tools")


def list_visible_windows_mac() -> list[VisibleWindow]:
    """
    Returns a list of visible windows on macOS.

    Returns:
        list[VisibleWindow]: A list of VisibleWindows objects representing the visible windows.
    """
    import Quartz

    windowList = Quartz.CGWindowListCopyWindowInfo(  # type: ignore
        Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
        Quartz.kCGNullWindowID,  # type: ignore
    )  # type: ignore
    result: list[VisibleWindow] = []
    for window in windowList:
        app_name = window.get("kCGWindowOwnerName", "")
        app_title = window.get("kCGWindowName", "")
        if not app_name and not app_title:
            continue

        window_id = window["kCGWindowNumber"]
        result.append(VisibleWindow(app_name=app_name, app_title=app_title, window_id=window_id))
    return result


def list_visible_windows() -> list[VisibleWindow]:
    """
    Returns a list of visible windows.

    Returns:
        list[VisibleWindow]: A list of VisibleWindows objects representing the visible windows.
    """
    import platform

    if platform.system() == "Darwin":
        return list_visible_windows_mac()
    return []


class ImageCaptureOutputType(StrEnum):
    """
    Specifies the output format for captured images.
    """

    PIL = "PIL"
    BYTES = "BYTES"
    BASE64 = "BASE64"


def capture_window_image_mac(
    app_name: str | None = None,
    app_title: str | None = None,
    window_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
) -> PIL.Image.Image | bytes | str:
    """
    Captures a screenshot of the specified window on macOS and saves it as a PNG image.
    You must specify at least one of app_name, app_title or window_id.
    Image will be PNG format in the specified output format.

    Args:
        app_name (str | None): Name of the application to find and capture. Defaults to None = Any.
        app_title (str | None): Title of the application to find and capture. Defaults to None = Any.
        window_id (int | None): Window ID of the application to find and capture. Defaults to None = Any.
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.
    """
    import tempfile

    import Quartz

    app_name = (app_name or "").strip().lower()
    app_title = (app_title or "").strip().lower()
    if not app_name and not app_title and not window_id:
        raise ValueError("Either app_name, app_title, or window_id must be specified")

    if not window_id:
        windowList = Quartz.CGWindowListCopyWindowInfo(  # type: ignore
            Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
            Quartz.kCGNullWindowID,  # type: ignore
        )  # type: ignore

        for window in windowList:
            app = window.get("kCGWindowOwnerName", "").lower()
            title = window.get("kCGWindowName", "").lower()

            if app_name and (not app or app_name not in app):
                continue
            if app_title and (not title or app_title not in title):
                continue

            window_id = window["kCGWindowNumber"]

    with tempfile.NamedTemporaryFile(suffix=".png") as temp_image:
        # -x mutes sound and -l specifies windowId
        cmd = f"screencapture -x -t png -l {window_id} {temp_image.name}"
        # console_err.print(cmd)
        ret = os.system(cmd)
        if ret != 0:
            raise ValueError(
                f"Failed to capture screenshot of app '{app_name}' / title '{app_title}' / window ID '{window_id}'"
            )

        screenshot = PIL.Image.open(temp_image.name)
        if not output_format or output_format == ImageCaptureOutputType.PIL:
            return screenshot

        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        if output_format == ImageCaptureOutputType.BYTES:
            return img_bytes.getvalue()

        return image_to_base64(img_bytes.getvalue(), "png")

    raise ValueError(f"No app '{app_name}' / title '{app_title}' / window ID {window_id} found")


def capture_window_image(
    app_name: str | None = None,
    app_title: str | None = None,
    window_id: int | None = None,
    output_format: ImageCaptureOutputType | None = None,
) -> PIL.Image.Image | bytes | str:
    """
    Captures a screenshot of the specified window and saves it as a PNG image.
    You must specify at least one of app_name, app_title or window_id.
    Image will be PNG format in the specified output format.

    Args:
        app_name (str | None): Name of the application to find and capture. Defaults to None = Any.
        app_title (str | None): Title of the application to find and capture. Defaults to None = Any.
        window_id (int | None): Window ID of the application to find and capture. Defaults to None = Any.
        output_format (ImageCaptureOutputType | None): The format to return the image in. Defaults to None = PIL.

    Returns:
        Image | bytes | str: The captured image, image bytes or the base64-encoded image data.
    """
    import platform

    if platform.system() == "Darwin":
        return capture_window_image_mac(app_name, app_title, window_id, output_format)

    app_name = (app_name or "").strip().lower()
    app_title = (app_title or "").strip().lower()
    if not app_name and not app_title:
        raise ValueError("Either app_name or app_title must be specified")

    import pyautogui
    import pywinctl as gw

    window_info = gw.getAllWindows()
    # console_err.print(window_info)
    if app_name and not app_title:
        windows = [t for t in window_info if app_name in t.getAppName().lower()]
    elif app_title and not app_name:
        windows = [t for t in window_info if app_title in t.title.lower()]
    else:
        windows = [t for t in window_info if app_name in t.getAppName().lower() and app_title in t.title.lower()]
    if not windows:
        raise ValueError(f"No app '{app_name}' / title '{app_title}' found")

    if len(windows) > 1:
        print(f"Multiple windows found with title '{app_title}':")
        for i, title in enumerate(windows, start=1):
            console_err.print(f"{i}. {title}")
        raise ValueError(f"Multiple app '{app_name}' windows found with title '{app_title}'")
    window = windows[0]
    window.activate()

    left, top, right, bottom = window.left, window.top, window.right, window.bottom
    screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
    if not output_format or output_format == ImageCaptureOutputType.PIL:
        return screenshot

    img_bytes = io.BytesIO()
    screenshot.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    if output_format == ImageCaptureOutputType.BYTES:
        return img_bytes.getvalue()

    return image_to_base64(img_bytes.getvalue(), "png")


def describe_image_with_llm(img: str | Path, llm_config: LlmConfig | None = None) -> str:
    """
    Describes the image using a LLM.

    Args:
        img (str | Path): The image file path or URL.
        llm_config (LlmConfig | None): The LLM configuration. Defaults to None = OpenAI GPT-4o.

    Returns:
        str: A description of the image.
    """
    if isinstance(img, str):
        if not img.startswith("data:image/"):
            if img.startswith("http"):
                img = cache_manager.download(img)
            else:
                img = Path(img)
            if not img.is_file():
                raise ValueError(f"No such file or directory: {img}")
            img = image_to_base64(img.read_bytes(), try_get_image_type(img))
    msg = image_to_chat_message(str(img))
    chat = (llm_config or LlmConfig(LlmProvider.OPENAI, "gpt-4o")).build_chat_model()
    return str(
        chat.invoke(
            [
                ("system", "Describe the image in great detail"),
                ("user", [{"type": "text", "text": "describe the image"}, msg]),  # type: ignore
            ]
        ).content
    )


def speak(text: str):
    from elevenlabs import play
    from elevenlabs.client import ElevenLabs

    # start_time = time.time()
    model = "eleven_flash_v2_5"
    # model="eleven_flash_v2"
    # model = "eleven_turbo_v2"
    # model = "eleven_turbo_v2_5"
    # model="eleven_multilingual_v2"
    voice = "XB0fDUnXU5powFXDhCwa"  # Charlotte
    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    audio_generator = elevenlabs_client.generate(
        text=text,
        voice=voice,
        model=model,
        stream=False,
    )
    audio_bytes = b"".join(list(audio_generator))
    # duration = time.time() - start_time
    # console_err.print(f"Model {model} completed tts in {duration:.2f} seconds")
    play(audio_bytes)


def image_gen_dali(
    prompt: str, model_name: Literal["dall-e-2", "dall-e-3"] = "dall-e-3", upgrade_prompt: LlmConfig | None = None
) -> Path:
    from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper

    if upgrade_prompt:
        chat = upgrade_prompt.build_chat_model()
        prompt = str(
            chat.invoke(
                [
                    (
                        "system",
                        "Generate a detailed prompt under 800 chars in order to generate an image based on the users description. Only return the updated prompt. Do not include any intro or explanation.",
                    ),
                    ("user", prompt),
                ]
            ).content
        )
        console_err.print(prompt)
    img_gen = DallEAPIWrapper()
    img_gen.model_name = model_name
    image_url = img_gen.run(prompt)
    return cache_manager.download(image_url)


def update_pyproject_deps(do_uv_update: bool = True, console: Console | None = None) -> None:
    """
    Update dependencies in pyproject.toml with the latest available versions.

    This function reads the pyproject.toml file (expected to follow PEP 621 with
    dependencies listed under the [project] table), and for each dependency:

      - Parses the dependency string (e.g. "package[extra]>=1.2.3") using packaging's
        Requirement class.
      - Retrieves the latest version from the installed package metadata.
      - If no version is specified or if the latest version is newer than the specified
        version, it updates the dependency to use a specifier of the form ">=latest_version".

    The updated TOML data is then written to a new file named "pyproject_new.toml"
    in the same directory as the original file.

    Args:
        do_uv_update (bool): Whether to use uv sync to update the packages. Defaults to True.
        console (Console | None): The console object to use for logging. Defaults to console_err.

    Returns:
        None
    """
    console = console or console_err
    # Define the path to the pyproject.toml file
    pyproject_path: Path = Path("pyproject.toml")
    if not pyproject_path.exists():
        console_err.print("[red]pyproject.toml not found in the expected location.")
        return

    if do_uv_update:
        subprocess.run(["uv", "sync", "-U"], check=True)

    # Read and parse the TOML file using tomllib
    try:
        with open(pyproject_path, "rb") as f:
            toml_data: dict[str, Any] = tomllib.load(f)
    except Exception as e:
        console.print(f"[red]Error reading pyproject.toml: {e}")
        return

    # Locate the dependencies section.
    # This example assumes dependencies are under the [project] table per PEP 621.
    project_data: dict[str, Any] | None = toml_data.get("project")
    if not project_data or "dependencies" not in project_data:
        console.print("[red]Dependencies section not found under [project] in pyproject.toml.")
        return

    deps: Any = project_data["dependencies"]
    if not isinstance(deps, list):
        console.print("[red]Dependencies should be a list in pyproject.toml.")
        return

    updated_deps: list[str] = []
    for dep in deps:
        try:
            # Parse the dependency string (which may include extras)
            req: Requirement = Requirement(dep)
        except Exception as e:
            console.print(f"[yellow]Failed to parse dependency '{dep}': {e}. Keeping original.")
            updated_deps.append(dep)
            continue

        package_name: str = req.name
        # Reconstruct the extras string (if any) in a normalized way.
        extras_str: str = f"[{','.join(sorted(req.extras))}]" if req.extras else ""

        # Try to extract the current version from the specifiers (if provided)
        current_version: str | None = None
        for spec in req.specifier:
            if spec.operator in (">=", ">"):
                current_version = spec.version
                break

        # Attempt to get the latest version from package metadata
        try:
            metadata = importlib.metadata.metadata(package_name)  # type: ignore
            latest_version: str = metadata["Version"]
        except importlib.metadata.PackageNotFoundError:  # type: ignore
            console.print(f"[yellow]Package {package_name} not found. Keeping original: {dep}")
            updated_deps.append(dep)
            continue

        # Determine if an update is needed:
        # - If there was no version specifier, or
        # - If the latest version is newer than the current version,
        # then update the dependency string.
        if current_version is None or parse(latest_version) > parse(current_version):
            new_dep: str = f"{package_name}{extras_str}>={latest_version}"
            updated_deps.append(new_dep)
            console.print(f"[green]Updated {dep} to {new_dep}")
        else:
            updated_deps.append(dep)

    # Update the dependencies list in the TOML data
    toml_data["project"]["dependencies"] = updated_deps

    # Write the updated TOML data to a new file using tomli_w
    new_pyproject_path: Path = pyproject_path  # pyproject_path.parent / "pyproject_new.toml"
    try:
        with open(new_pyproject_path, "wb") as f:
            f.write(tomli_w.dumps(toml_data).encode("utf-8"))
    except Exception as e:
        console.print(f"[red]Error writing updated {new_pyproject_path.name}: {e}")
        return

    console.print(f"[green]{new_pyproject_path.name} updated.")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path("~/.par_gpt.env").expanduser())

    # sixel_supported = sixel_query_terminal_support()
    # if sixel_supported:
    #     print("sixel supported")
    #     c = sixel_converter.SixelConverter(
    #         Path(
    #             "~/.par_gpt/cache/d9bae1270340f598bebe4b5c311c08210ef5cd4a.jpg"
    #         ).expanduser()  # , w=width, h=height, chromakey=True, alpha_threshold=0, fast=True
    #     )
    #
    #     c.write(console_err.file)
