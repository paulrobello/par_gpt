"""AI tools"""

from __future__ import annotations

import os
import re
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

import clipman as clipboard
import feedparser
import requests
from github import Auth, AuthenticatedUser, Github
from langchain_core.tools import tool
from par_ai_core.llm_config import LlmConfig, LlmMode, llm_run_manager
from par_ai_core.llm_providers import LlmProvider, provider_light_models
from par_ai_core.par_logging import console_err
from par_ai_core.search_utils import brave_search, reddit_search, serper_search, youtube_get_transcript, youtube_search
from par_ai_core.web_tools import GoogleSearchResult, fetch_url_and_convert_to_markdown, web_search
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

# Memory utils imports moved inside ai_memory_db function to prevent Redis connection when disabled
from par_gpt.repo.repo import GitRepo
from par_gpt.utils import get_console

# Import functions directly from the original utils.py file to avoid circular imports
# We need to import them carefully to avoid the utils package vs utils.py conflict
try:
    # Direct import from the utils.py file
    import importlib.util

    utils_py_path = os.path.join(os.path.dirname(__file__), "..", "utils.py")
    spec = importlib.util.spec_from_file_location("utils_module", utils_py_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load utils.py spec")
    utils_module = importlib.util.module_from_spec(spec)

    # Set up minimal environment for utils.py to load
    import sys

    original_modules = sys.modules.copy()

    # Execute with minimal dependencies to avoid circular imports
    try:
        spec.loader.exec_module(utils_module)
        # Extract the functions we need
        capture_window_image = utils_module.capture_window_image
        describe_image_with_llm = utils_module.describe_image_with_llm
        get_weather_current = utils_module.get_weather_current
        get_weather_forecast = utils_module.get_weather_forecast
        show_image_in_terminal = utils_module.show_image_in_terminal
        github_publish_repo = utils_module.github_publish_repo
        figlet_horizontal = utils_module.figlet_horizontal
        figlet_vertical = utils_module.figlet_vertical
        list_visible_windows_mac = utils_module.list_visible_windows_mac
        image_gen_dali = utils_module.image_gen_dali
    except Exception:
        # Fallback if direct import fails - create stub functions
        def capture_window_image(*args, **kwargs):
            return "Function not available due to import restrictions"

        def describe_image_with_llm(*args, **kwargs):
            return "Function not available due to import restrictions"

        def get_weather_current(*args, **kwargs):
            return {"error": "Function not available due to import restrictions"}

        def get_weather_forecast(*args, **kwargs):
            return {"error": "Function not available due to import restrictions"}

        def show_image_in_terminal(*args, **kwargs):
            return "Function not available due to import restrictions"

        def github_publish_repo(*args, **kwargs):
            return "Function not available due to import restrictions"

        def figlet_horizontal(*args, **kwargs):
            return "Function not available due to import restrictions"

        def figlet_vertical(*args, **kwargs):
            return "Function not available due to import restrictions"

        def list_visible_windows_mac(*args, **kwargs):
            return []

        def image_gen_dali(*args, **kwargs):
            # Return a stub path that will work with hasattr check
            class StubPath:
                def as_posix(self):
                    return "Function not available due to import restrictions"

                def __str__(self):
                    return "Function not available due to import restrictions"

            return StubPath()

except Exception:
    # Final fallback - create stub functions if the first level import failed
    pass


from sandbox import ExecuteCommandResult


@tool(parse_docstring=True)
def ai_image_search(query: str, max_results: int = 10) -> list[str]:
    """
    Searches for images using Serper Google Images.

    Args:
        query: The search query.
        max_results: The maximum number of images to return (default: 10).

    Returns:
        A list of Markdown Image URLs.
    """
    all_links = []
    for result in serper_search(query, type="images", max_results=max_results, include_images=True, scrape=True):
        content = result["raw_content"].replace("\n", "")

        md_url_matcher = r"(!\[.*?\]\(https?://[^\s]+?\))"
        image_matcher = r".+\.(png|gif|jpe?g)"

        md_links = re.findall(md_url_matcher, content, re.IGNORECASE)
        md_links = [link for link in md_links if re.match(image_matcher, link, re.IGNORECASE)]
        all_links.extend(md_links)

    return all_links


@tool(parse_docstring=True)
def ai_fetch_url(
    urls: list[str],
) -> list[str]:
    """
    Fetches the content of one or more webpages and returns as markdown.

    Args:
        urls: 1 to 3 urls to download. No more than 3 urls will be downloaded.

    Returns:
        A list of markdown content for each url.
    """
    return fetch_url_and_convert_to_markdown(urls[:3], include_links=True, verbose=True)


@tool(parse_docstring=True)
def ai_web_search(query: str) -> list[GoogleSearchResult]:
    """
    Performs a Google web search.

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
    """
    Performs a Reddit search.

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
    """
    Copies text to the clipboard.

    Args:
        text: The text to copy to the clipboard.

    Returns:
        "Text copied to clipboard" or error message "Error accessing clipboard".
    """
    try:
        clipboard.copy(text)
        return "Text copied to clipboard"
    except Exception as e:
        get_console().print(f"Error copying to clipboard: {str(e)}")
        return "Error accessing clipboard"


@tool(parse_docstring=True)
def ai_copy_from_clipboard() -> str:
    """
    Copies text from the clipboard.

    Args:

    Returns:
        Any text that was copied from the clipboard or an error message "Error accessing clipboard".
    """
    try:
        return clipboard.paste() or ""
    except Exception as e:
        get_console().print(f"Error accessing clipboard: {str(e)}")
        return "Error accessing clipboard"


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
    """
    Opens a URL in the default browser.

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
    """
    Search the web using Brave.

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
def ai_serper_search(
    query: str,
    type: Literal["news", "search", "places", "images"] = "search",
    days: int = 0,
    max_results: int = 3,
    scrape: bool = False,
) -> list[dict[str, Any]]:
    """
    Search the web using Google Serper.

    Args:
        query (str): The search query to execute
        type: Literal["news", "search", "places", "images"] = "search",
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

    return serper_search(query, type=type, days=days, max_results=max_results, scrape=scrape)


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
def ai_github_publish_repo(repo_name: str | None = None, public: bool = False) -> str:
    """
    Create a new GitHub repository and push current repo to it.
    If an error message is returned stop and make it your final response.

    Args:
        repo_name (str): The name of the repository (default: the name of the current working directory)
        public (bool): Whether the repository should be public (default: False)

    Returns:
        str: The URL of the newly created repository or Error message
    """
    return github_publish_repo(repo_name, public)


@tool(parse_docstring=True)
def ai_figlet(
    text: str,
    font: str = "ansi_shadow",  # FigletFontName
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


@tool(parse_docstring=True)
def ai_fetch_rss(url: str, max_items: int = 5) -> str:
    """
    Fetches an RSS feed and formats its content as markdown. The Markdown should be returned to the user without modification unless otherwise requested by the user.

    Args:
        url (str): The URL of the RSS feed to fetch.
        max_items (int): The maximum number of items to include in the output (default: 5).

    Returns:
        str: The formatted markdown content of the RSS feed.
    """
    feed = feedparser.parse(url)

    if feed.bozo:
        return f"Error: Unable to parse the RSS feed. {feed.bozo_exception}"

    if "title" in feed.feed:
        markdown_content = f"# {feed.feed.title}\n\n"  # type: ignore
    else:
        markdown_content = "# No title found in the RSS feed\n\n"

    if "subtitle" in feed.feed:
        markdown_content += f"{feed.feed.subtitle}\n\n"  # type: ignore

    for i, entry in enumerate(feed.entries[:max_items]):
        # console_err.print(entry)
        markdown_content += f"## {entry.title}\n"

        if "published" in entry:
            pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")  # type: ignore
            markdown_content += f"*Published on: {pub_date.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

        if "summary" in entry:
            markdown_content += f"{entry.summary}\n\n"

        if "link" in entry:
            markdown_content += f"[Read more]({entry.link})\n\n"

        if i < len(feed.entries[:max_items]) - 1:
            markdown_content += "---\n\n"
    # console_err.print(Markdown(markdown_content))
    return markdown_content


@tool(parse_docstring=True)
def ai_fetch_hacker_news(max_items: int = 5) -> str:
    """
    Fetches top articles from Hacker News and formats them as markdown. The Markdown should be returned to the user without modification unless otherwise requested by the user.

    Args:
        max_items (int): The maximum number of items to include in the output (default: 5).

    Returns:
        str: The formatted markdown content of the Hacker News articles.
    """

    def fetch_item(item_id):
        response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10)
        return response.json()

    # Fetch top stories
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    top_stories = response.json()[:max_items]

    # Fetch details for each story
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_item = {executor.submit(fetch_item, item_id): item_id for item_id in top_stories}
        stories = []
        for future in as_completed(future_to_item):
            stories.append(future.result())

    # Sort stories by score
    stories.sort(key=lambda x: x.get("score", 0), reverse=True)

    markdown_content = "# Top Hacker News Articles\n\n"

    for story in stories:
        title = story.get("title", "No Title")
        url = story.get("url", "")
        score = story.get("score", 0)
        author = story.get("by", "Unknown")
        comments = story.get("descendants", 0)

        markdown_content += f"## {title}\n\n"
        markdown_content += f"**Score:** {score} | **Author:** {author} | **Comments:** {comments}\n\n"

        if url:
            markdown_content += f"[Read more]({url})\n\n"

        markdown_content += f"[View on Hacker News](https://news.ycombinator.com/item?id={story['id']})\n\n"
        markdown_content += "---\n\n"

    return markdown_content


@tool(parse_docstring=True)
def execute_code(code: str) -> ExecuteCommandResult:
    """
    Executes the given python code in a sandbox and returns the output.
    You must use print statements to get the output.
    Do not assume the output is shown to the user, you must use or show it to the user in the desired format.

    Args:
        code (str): The python code to execute. Should NOT be JSON encoded and newlines should not be escaped.

    Returns:
        ExecuteCommandResult which will contain the exit code, stdout, and stderr of the executed code.
    """
    from sandbox import SandboxRun

    try:
        console_err.print(Panel(code, title="Running code in sandbox..."))
        runner = SandboxRun(container_name="par_gpt_sandbox-python_runner-1", console=console_err, verbose=True)

        result = runner.execute_code_in_container(code)
        console_err.print(
            Panel(
                Text.assemble(
                    ("Return Code: ", "#9999FF"),
                    f"{result.exit_code}\n",
                    ("Out:\n", "#99FF99"),
                    f"{result.stdout}\n",
                    ("Err:\n", "#FF9999"),
                    result.stderr,
                ),
                title="Code execution result",
            )
        )
        return result
    except Exception as e:
        return ExecuteCommandResult(exit_code=1, stdout="", stderr=f"Error: {str(e)}")


@tool(parse_docstring=True)
def ai_list_visible_windows() -> list:
    """
    Get list all visible windows on the user's screen.
    Use this tool to help find and capture specific window screenshots.

    Returns:
        list: A list of visible windows on the user's screen.
    """
    return list_visible_windows_mac()


@tool(parse_docstring=True)
def ai_list_available_screens() -> list:
    """
    Get list of all available screens/displays on the user's system.
    Use this tool to help find and capture specific screen screenshots.

    Returns:
        list: A list of available screens/displays with their details.
    """
    try:
        import importlib.util

        # Direct import from utils.py to avoid circular imports
        utils_py_path = os.path.join(os.path.dirname(__file__), "..", "utils.py")
        spec = importlib.util.spec_from_file_location("utils_module", utils_py_path)
        if spec is None or spec.loader is None:
            return [{"error": "Could not load screen detection utilities"}]
        utils_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(utils_module)

        return utils_module.list_available_screens()
    except Exception as e:
        return [{"error": f"Screen detection not available: {str(e)}"}]


@tool(parse_docstring=True)
def ai_capture_screen_image(screen_id: int | None = None, describe_image: bool = True) -> str:
    """
    Captures a screenshot of the specified screen/display. If no screen_id is provided,
    it will list available screens and capture the primary display.

    Args:
        screen_id (int | None): ID of the screen/display to capture. Defaults to None (primary display).
        describe_image (bool): Whether to describe the captured image. Defaults to True.

    Returns:
        if describe_image is True then a description of the image will be returned otherwise thebase64-encoded image data.
    """
    # If no screen_id specified, get the list of screens and capture the primary one
    if screen_id is None:
        try:
            # Use the same import approach as above for consistency
            import importlib.util

            # Direct import from utils.py to avoid circular imports
            utils_py_path = os.path.join(os.path.dirname(__file__), "..", "utils.py")
            spec = importlib.util.spec_from_file_location("utils_module", utils_py_path)
            if spec is None or spec.loader is None:
                return "Error: Could not load screen detection utilities"
            utils_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(utils_module)

            screens = utils_module.list_available_screens()
            if not screens:
                return "No displays found to capture."

            # Use the first screen (should be the primary display after sorting) or show options
            from rich.console import Console

            console = Console()

            if len(screens) == 1:
                # Only one screen, use it
                selected_screen = screens[0]
                console.print(f"\n[green]Found one display:[/green] {selected_screen.name}")
            else:
                # Multiple screens, show list and use first one (primary display)
                console.print("\n[yellow]Available displays (primary display first):[/yellow]")
                for i, screen in enumerate(screens[:5], 1):  # Show first 5 screens
                    prefix = "🖥️" if i == 1 else "  "  # Mark the primary display
                    console.print(f"{prefix} {i}. {screen.name}")

                # Use the first screen (should be the primary display after sorting)
                selected_screen = screens[0]
                console.print(f"\n[green]Capturing primary display:[/green] {selected_screen.name}")

            # Use the screen information directly from AvailableScreen object
            screen_id = selected_screen.screen_id

        except Exception as e:
            return f"Error getting screen list: {str(e)}. Please specify screen_id manually."

    try:
        # Import capture_screen_image function using the same approach
        import importlib.util

        utils_py_path = os.path.join(os.path.dirname(__file__), "..", "utils.py")
        spec = importlib.util.spec_from_file_location("utils_module", utils_py_path)
        if spec is None or spec.loader is None:
            return "Error: Could not load screen capture utilities"
        utils_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(utils_module)

        img = utils_module.capture_screen_image(screen_id=screen_id, output_format="BASE64")
        if not describe_image:
            return img  # type: ignore

        return utils_module.describe_image_with_llm(img)  # type: ignore
    except Exception as e:
        return f"Error capturing screen image: {str(e)}"


@tool(parse_docstring=True)
def ai_capture_window_image(
    app_name: str | None = None, app_title: str | None = None, window_id: int | None = None, describe_image: bool = True
) -> str:
    """
    Captures a screenshot of the specified window. If no window parameters are provided,
    it will list available windows and capture the active/frontmost window.

    Args:
        app_name (str | None): Name of the application to find and capture. Defaults to None.
        app_title (str | None): Title of the application to find and capture. Defaults to None.
        window_id (int | None): Window ID of the application to find and capture. Defaults to None.
        describe_image (bool): Whether to describe the captured image. Defaults to True.

    Returns:
        if describe_image is True then a description of the image will be returned otherwise thebase64-encoded image data.
    """
    # If no window parameters are specified, get the list of windows and capture the active one
    if app_name is None and app_title is None and window_id is None:
        try:
            windows = list_visible_windows_mac()
            if not windows:
                return "No visible application windows found to capture. You may need to specify an app_name manually."

            # Use the first window (should be the frontmost/active after sorting) or show options
            from rich.console import Console

            console = Console()

            if len(windows) == 1:
                # Only one window, use it
                selected_window = windows[0]
                console.print(
                    f"\n[green]Found one window:[/green] {selected_window.app_name} - {selected_window.app_title}"
                )
            else:
                # Multiple windows, show list and use first one (should be the active window)
                console.print("\n[yellow]Available application windows (active window first):[/yellow]")
                for i, window in enumerate(windows[:5], 1):  # Show first 5 windows
                    prefix = "🔴" if i == 1 else "  "  # Mark the active window
                    console.print(f"{prefix} {i}. {window.app_name} - {window.app_title}")

                # Use the first window (should be the active window after intelligent sorting)
                selected_window = windows[0]
                console.print(
                    f"\n[green]Capturing active window:[/green] {selected_window.app_name} - {selected_window.app_title}"
                )

            # Use the window information directly from VisibleWindow object
            app_name = selected_window.app_name
            app_title = selected_window.app_title
            window_id = selected_window.window_id

        except Exception as e:
            return f"Error getting window list: {str(e)}. Please specify app_name, app_title, or window_id manually."

    try:
        img = capture_window_image(app_name=app_name, app_title=app_title, window_id=window_id, output_format="BASE64")
        if not describe_image:
            return img  # type: ignore

        return describe_image_with_llm(img)  # type: ignore
    except Exception as e:
        return f"Error capturing window image: {str(e)}"


@tool(parse_docstring=True)
def user_prompt(prompt: str, default_value: str | None = None, choices: list[str] | None = None) -> str:
    """
    Prompt the user for input with a customizable prompt message, and optional default value choices.

    Args:
        prompt (str): The prompt message to display to the user.
        default_value (str | None): The default value to use if the user enters nothing.
        choices (list[str] | None): A list of choices to present to the user. If provided, the user will be asked to select one of the choices.

    Returns:
        str: The user's input.
    """
    return Prompt.ask(prompt, console=console_err, default=default_value, choices=choices) or ""


@tool(parse_docstring=True)
def ai_image_gen_dali(prompt: str, display: bool = True) -> str:
    """
    Generate an image using DALI-3 based on the given prompt.
    You MUST return the path to the generated image to the user.

    Args:
        prompt (str): The prompt to use for generating the image (max 1000 chars).
        display (bool): Whether to display the generated image in the terminal (default: True).

    Returns:
        str: The path to the generated image. This MUST be shown to the user.
    """
    image_path = image_gen_dali(
        prompt,
        # upgrade_prompt=LlmConfig(LlmProvider.OPENAI, model_name="gpt-4o-mini", temperature=0.9),
    )
    if display:
        show_image_in_terminal(image_path, transparent=False)

    # Handle both Path objects and string returns from image_gen_dali
    if hasattr(image_path, "as_posix"):
        return image_path.as_posix()
    else:
        return str(image_path)


@tool(parse_docstring=True)
def ai_memory_db(op: Literal["list", "add", "remove"], memory: str | None) -> str:
    """
    Use this tool to help keep track of user-specific memories.

    Args:
        op (Literal["list", "add", "remove"]): The operation to perform on the memory (list, add, remove).
        memory (str | None): The memory to add or remove (if applicable).

    Returns:
        str: The result of the operation.
    """
    # Import memory utils here to avoid Redis connection when Redis is disabled
    from par_gpt.memory_utils import add_memory_redis, get_memory_user, list_memories_redis, remove_memory_redis

    if op == "list":
        return "\n".join(list_memories_redis(get_memory_user()))
    elif op == "add":
        if not memory:
            return "Please provide a memory to add."
        add_memory_redis(get_memory_user(), memory)
        return "Memory added successfully."
    elif op == "remove":
        if not memory:
            return "Please provide a memory to remove."
        remove_memory_redis(get_memory_user(), memory)
        return "Memory removed successfully."
    else:
        return "Invalid operation. Supported operations: list, add, remove"


if __name__ == "__main__":
    figlet_horizontal("PAR GPT", font="3d-ascii")
    # figlet_vertical("PAR GPT", font="3d-ascii")
