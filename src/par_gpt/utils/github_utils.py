"""GitHub repository publishing utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from par_ai_core.par_logging import console_err

from par_gpt.repo.repo import ANY_GIT_ERROR, GitRepo


def github_publish_repo(repo_name: str | None = None, public: bool = False) -> str:
    """
    Create a new GitHub repository and push current repo to it.
    If an error message is returned stop and make it your final response.

    Args:
        repo_name (str): The name of the repository (default: the name of the current working directory)
        public (bool): Whether the repository should be public (default: False)

    Returns:
        str: The URL of the newly created repository or Error message
    """
    # Import github dependencies locally for better startup performance
    try:
        from git import Remote

        from par_utils import lazy_import

        # Lazy load GitHub classes
        Auth = lazy_import("github", "Auth")
        Github = lazy_import("github", "Github")
        AuthenticatedUser = lazy_import("github", "AuthenticatedUser")
    except ImportError:
        return "Error: GitHub dependencies not available"

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
    gh_repo = cast(AuthenticatedUser, g.get_user()).create_repo(repo_name, private=not public)  # type: ignore
    remote = repo.create_remote("origin", gh_repo.ssh_url)
    if not isinstance(remote, Remote):
        # console_err.print(f"Error: {remote}")
        return f"Error: {remote}"

    try:
        remote.push(f"HEAD:{gh_repo.default_branch}")
        repo.repo.git.branch(f"--set-upstream-to=origin/{gh_repo.default_branch}", gh_repo.default_branch)
    except ANY_GIT_ERROR as e:
        console_err.print(f"Error pushing to remote: {e}")
        return (
            f"GitHub repo created {gh_repo.html_url} but there was an error pushing to the remote. Error Message: {e}"
        )
    return gh_repo.html_url
