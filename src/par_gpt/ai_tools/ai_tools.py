"""AI tools"""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Any, Literal, cast

import clipman as clipboard
from git import Remote
from github import Auth, AuthenticatedUser, Github
from langchain_core.tools import tool
from par_ai_core.llm_config import LlmConfig, LlmMode, llm_run_manager
from par_ai_core.llm_providers import LlmProvider, provider_light_models
from par_ai_core.par_logging import console_err
from par_ai_core.search_utils import brave_search, reddit_search, serper_search, youtube_get_transcript, youtube_search
from par_ai_core.web_tools import GoogleSearchResult, fetch_url_and_convert_to_markdown, web_search

from par_gpt.repo.repo import ANY_GIT_ERROR, GitRepo
from par_gpt.utils import (
    FigletFontName,
    figlet_horizontal,
    figlet_vertical,
    get_weather_current,
    get_weather_forecast,
    show_image_in_terminal,
)


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
    return fetch_url_and_convert_to_markdown(urls[:3], include_links=True, verbose=True)


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
def ai_reddit_search(
    query: str, subreddit: str = "all", max_comments: int = 0, max_results: int = 3
) -> list[dict[str, Any]]:
    """Performs a Reddit search.

    Args:
        query: The Google search query. The following list of single word queries can be used to fetch posts [hot, new, controversial]
        subreddit: The sub-reddit to search (default: 'all')
        max_comments (int): Maximum number of comments to return (default: 0 do not return comments)
        max_results: Maximum number of results to return (default: 3)

    Returns:
        A list of Reddit search results.
    """
    return reddit_search(query, subreddit=subreddit, max_comments=max_comments, max_results=max_results)


@tool(parse_docstring=True)
def ai_copy_to_clipboard(text: str) -> str:
    """Copies text to the clipboard.

    Args:
        text: The text to copy to the clipboard.

    Returns:
        "Text copied to clipboard"
    """

    clipboard.copy(text)
    return "Text copied to clipboard"


@tool(parse_docstring=True)
def ai_copy_from_clipboard() -> str:
    """Copies text from the clipboard.

    Args:

    Returns:
        Any text that was copied from the clipboard.
    """

    return clipboard.paste() or ""


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


@tool(parse_docstring=True)
def ai_youtube_get_transcript(video_id: str) -> str:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_id (str): YouTube video ID

    Returns:
        str: Transcript text
    """
    return youtube_get_transcript(video_id)


@tool(parse_docstring=True)
def ai_youtube_search(
    query: str, days: int = 0, max_results: int = 3, fetch_transcript: bool = False
) -> list[dict[str, Any]]:
    """
    Search YouTube for videos and optionally fetch transcripts.

    Args:
        query (str): The search query.
        days (int, optional): The number of days to search. Defaults to 0 meaning all time.
        max_results (int, optional): The maximum number of results to return. Defaults to 3.
        fetch_transcript (bool, optional): Whether to fetch the transcript for each video. Defaults to False.

    Returns:
        - results (list): List of search result dictionaries, each containing:
            - title (str): Title of the search result
            - url (str): URL of the search result
            - description (str): Snippet/summary of the content
            - raw_content (str): Full content of the page if available
    """
    return youtube_search(query, days=days, max_results=max_results, fetch_transcript=fetch_transcript)


@tool(parse_docstring=True)
def ai_brave_search(query: str, days: int = 0, max_results: int = 3, scrape: bool = False) -> list[dict[str, Any]]:
    """Search the web using Brave.

    Args:
        query (str): The search query to execute
        days (int): Number of days to search (default is 0 meaning all time)
        max_results (int): Maximum number of results to return
        scrape (bool): Whether to scrape the content of the search result urls

    Returns:
        - results (list): List of search result dictionaries, each containing:
            - title (str): Title of the search result
            - url (str): URL of the search result
            - description (str): Snippet/summary of the content
            - raw_content (str): Full content of the page if available
    """
    return brave_search(query, days=days, max_results=max_results, scrape=scrape)


@tool(parse_docstring=True)
def ai_serper_search(query: str, days: int = 0, max_results: int = 3, scrape: bool = False) -> list[dict[str, Any]]:
    """Search the web using Google Serper.

    Args:
        query (str): The search query to execute
        days (int): Number of days to search (default is 0 meaning all time)
        max_results (int): Maximum number of results to return
        scrape (bool): Whether to scrape the search result urls (default is False)

    Returns:
        - results (list): List of search result dictionaries, each containing:
            - title (str): Title of the search result
            - url (str): URL of the search result
            - description (str): Snippet/summary of the content
            - raw_content (str): Full content of the page if available
    """

    return serper_search(query, days=days, max_results=max_results, scrape=scrape)


# this tool is only used to test nested llm calls
@tool()
def ai_joke(subject: str | None = None) -> str:
    """
    Tell a joke.

    Args:
        subject (str | None): The subject of the joke (default: None for any subject)

    Returns:
        str: The joke
    """
    llm_config = LlmConfig(
        provider=LlmProvider.OPENAI,
        model_name=provider_light_models[LlmProvider.OPENAI],
    )
    chat_model = llm_config.build_chat_model()

    prompt = f"Tell me a {subject} joke"
    messages = [
        {
            "role": "system",
            "content": "You are a comedian that specializes in jokes that really make you think. Tell a joke dealing with the subject provided by the user. If the subject is not provided, tell a joke about anything.",
        },
        {"role": "user", "content": prompt or "anything"},
    ]
    return str(chat_model.invoke(messages, config=llm_run_manager.get_runnable_config(chat_model.name)).content)


REPO_ORDER_BY = Literal["created", "updated", "pushed", "full_name"]
REPO_ORDER_DIRECTION = Literal["asc", "desc"]


@tool(parse_docstring=True)
def ai_github_list_repos(
    order_by: REPO_ORDER_BY = "updated", order_direction: REPO_ORDER_DIRECTION = "asc", max_results: int = 0
) -> list[dict[str, Any]]:
    """
    List all the GitHub repositories for the current authenticated user.

    Args:
        order_by (str): The field to order the repositories by. Valid values are "created", "updated", "pushed", and "full_name".
        order_direction (str): The direction to order the repositories. Valid values are "asc" (ascending) and "desc" (descending).
        max_results (int): The maximum number of results to return. If 0, returns all results.

    Returns:
        - results (list): List of repository dictionaries, each containing:
            - name (str): Name of the repository
            - full_name (str): Full name of the repository
            - description (str): Description of the repository
            - url (str): URL of the repository
            - default_branch (str): Default branch of the repository
            - private (bool): Whether the repository is private
            - stars (int): Number of stars the repository has
            - forks_count (int): Number of forks the repository has
            - created_at (str): ISO format date and time the repository was created
            - updated_at (str): ISO format date and time the repository was last updated
            - pushed_at (str): ISO format date and time the repository was last pushed
            - open_issues (int): Number of open issues in the repository
    """
    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set.")
    auth = Auth.Token(os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"])
    g = Github(auth=auth)
    repos = g.get_user().get_repos(sort=order_by, direction=order_direction)
    res = [
        {
            "name": r.name,
            "full_name": r.full_name,
            "description": r.description,
            "url": r.html_url,
            "default_branch": r.default_branch,
            "private": r.private,
            "stars": r.stargazers_count,
            "forks_count": r.forks_count,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
            "pushed_at": r.pushed_at.isoformat(),
            "open_issues": r.open_issues,
        }
        for r in repos
    ]
    # console_err.print(res)
    if max_results:
        return res[:max_results]
    return res


@tool(parse_docstring=True)
def ai_github_create_repo(repo_name: str | None = None, private: bool = True) -> str:
    """
    Create a new GitHub repository

    Args:
        repo_name (str): The name of the repository (default: the name of the current working directory)
        private (bool): Whether the repository should be private (default: True)

    Returns:
        str: The URL of the newly created repository
    """
    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set.")
    auth = Auth.Token(os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"])
    g = Github(auth=auth)
    repo_name = repo_name or Path(os.getcwd()).stem.lower().replace(" ", "-")
    # console_err.print(f"Creating repository: {repo_name}")
    repo = cast(AuthenticatedUser, g.get_user()).create_repo(repo_name, private=private)  # type: ignore
    return repo.html_url


@tool(parse_docstring=True)
def ai_github_publish_repo(repo_name: str | None = None, private: bool = True) -> str:
    """
    Create a new GitHub repository and push current repo to it.
    If an error message is returned stop and make it your final response.

    Args:
        repo_name (str): The name of the repository (default: the name of the current working directory)
        private (bool): Whether the repository should be private (default: True)

    Returns:
        str: The URL of the newly created repository or Error message
    """
    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        return "Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set."

    repo: GitRepo
    try:
        repo = GitRepo()
        if repo.is_dirty():
            # console_err.print("Repo is dirty. Please commit changes before publishing.")
            return "Error: Repo is dirty. Please commit changes before publishing."
    except ANY_GIT_ERROR as e:
        console_err.print(e)
        return "Error: GIT repository not found. Please create a repository first."

    try:
        if repo.repo.remote("origin") is not None:
            console_err.print("Error: Remote origin already exists for this repository. Aborting.")
            return "Error: Remote origin already exists for this repository. Aborting."
    except ANY_GIT_ERROR as _:
        pass

    auth = Auth.Token(os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"])
    g = Github(auth=auth)
    repo_name = repo_name or Path(repo.repo.git_dir).parent.stem.lower().replace(" ", "-")

    # console_err.print(f"Creating repository: {repo_name}")
    gh_repo = cast(AuthenticatedUser, g.get_user()).create_repo(repo_name, private=private)  # type: ignore
    remote = repo.create_remote("origin", gh_repo.ssh_url)
    if not isinstance(remote, Remote):
        # console_err.print(f"Error: {remote}")
        return f"Error: {remote}"

    try:
        remote.push(f"HEAD:{gh_repo.default_branch}")
    except ANY_GIT_ERROR as e:
        # console_err.print(f"Error pushing to remote: {e}")
        return (
            f"GitHub repo created {gh_repo.html_url} but there was an error pushing to the remote. Error Message: {e}"
        )

    return gh_repo.html_url


@tool(parse_docstring=True)
def ai_figlet(
    text: str,
    font: FigletFontName = "ansi_shadow",
    colors: list[str] | None = None,
    color_direction: Literal["horizontal", "vertical"] = "vertical",
) -> str:
    """
    Create a figlet text and output it to the terminal

    Args:
        text (str): The text to convert to figlet
        font (str): The font to use (default: ansi_shadow)
        colors (list[str] | None): The colors to use as a gradient (default: ["#FFFF00", "#FFB000", "#FF7800", "#FF3200", "#FF0000"])
        color_direction (str): The direction to use for the gradient (default: "vertical")

    Returns:
        str: The figlet text

    Notes:
        Calling this tool will send its output directly to the terminal. You do not need to capture the output.
    """
    if color_direction == "horizontal":
        return figlet_horizontal(text, font, colors)
    return figlet_vertical(text, font, colors)


if __name__ == "__main__":
    figlet_horizontal("PAR GPT", font="3d-ascii")
    figlet_vertical("PAR GPT", font="3d-ascii")
