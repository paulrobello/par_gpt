"""AI tools"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
import pyperclip
import webbrowser

from ..lib.llm_config import LlmConfig, LlmMode
from ..lib.llm_providers import LlmProvider, provider_light_models
from ..lib.web_tools import fetch_url_and_convert_to_markdown, web_search, GoogleSearchResult
from ..repo.repo import GitRepo
from ..utils import get_weather_current, get_weather_forecast, show_image_in_terminal


@tool(parse_docstring=True)
def ai_fetch_url(
    urls: list[str],
) -> list[str]:
    """Fetches the content of one or more webpages and returns as markdown.

    Args:
        urls: 1 to 3 urls to download. No more than 3 urls will be downloaded.

    Returns:
        A list of markdown content for each url.
    """
    return fetch_url_and_convert_to_markdown(urls[:3], verbose=True)


@tool(parse_docstring=True)
def ai_web_search(query: str) -> list[GoogleSearchResult]:
    """Performs a Google web search.

    Args:
        query: The Google search query.

    Returns:
        A list of Google search results.
    """
    return web_search(query, num_results=5)


@tool(parse_docstring=True)
def ai_copy_to_clipboard(text: str) -> str:
    """Copies text to the clipboard.

    Args:
        text: The text to copy.

    Returns:
        The text that was copied.
    """

    pyperclip.copy(text)
    return "Text copied to clipboard"


@tool(parse_docstring=True)
def git_commit_tool(message_only: bool, files: list[str], context: str | None = None) -> str:
    """
    Create a git commit or return the commit message

    Args:
        message_only: If true, don't commit only return the commit message
        files: List of files to commit. Empty list will commit all tracked files
        context: Optional extra context to help generate the commit message

    Returns:
        str: The commit message and optional commit hash
    """
    ai_provider: LlmProvider = LlmProvider.OPENAI
    repo = GitRepo(
        llm_config=LlmConfig(
            provider=ai_provider,
            model_name=provider_light_models[ai_provider],
            temperature=0,
            mode=LlmMode.CHAT,
        )
    )
    if not repo.is_dirty():
        return "No changes to commit."
    if message_only:
        return "Commit Message: " + repo.get_commit_message(repo.get_diffs(files), context=context)
    else:
        ret = repo.commit(files, context=context)
        if not ret:
            return "Failed to commit."
        return f"Commit Message: {ret[1]}\nCommit Hash: {ret[0]}"


@tool(parse_docstring=True)
def ai_open_url(url: str) -> str:
    """Opens a URL in the default browser.

    Args:
        url: The URL to open.

    Returns:
        The URL that was opened.
    """

    webbrowser.open(url)
    return f"URL Opened: {url}"


@tool(parse_docstring=True)
def ai_get_weather_current(location: str) -> dict[str, Any]:
    """
    Get current weather for location.

    Args:
        location: Location ( can be Latitude / Longitude, City Name, ZIP Code, IATA, IP Address, or "auto" to autodetect location)

    Returns:
        dict: Weather data
    """

    return get_weather_current(location)


@tool(parse_docstring=True)
def ai_get_weather_forecast(location: str, num_days: int) -> dict[str, Any]:
    """
    Get current weather and forecast for next num_days.

    Args:
        location: Location ( can be Latitude / Longitude, City Name, ZIP Code, IATA, IP Address, or "auto" to autodetect location)
        num_days: Number of days to fetch. Must be between 1 and 7

    Returns:
        dict: Weather data
    """

    return get_weather_forecast(location, num_days)


@tool(parse_docstring=True)
def ai_display_image_in_terminal(image_path: str, dimension: str = "auto") -> str:
    """
    Show image in terminal.
    If an error is returned do not retry this call with same image.
    If the tool is successful there is no need to inform user

    Args:
        image_path: Image path or URL
        dimension: Image dimension in format of WIDTHxHEIGHT, small, medium, large or auto.

    Returns:
        str: Status of the operation
    """

    return show_image_in_terminal(image_path, dimension)
