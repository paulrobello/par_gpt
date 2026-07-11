"""Main application entry point for PAR GPT."""

# ruff: noqa: E402
# E402 is intentionally ignored because we must configure warning filters
# before importing LangChain modules that trigger Python 3.14 compatibility warnings

from __future__ import annotations

# Suppress Pydantic v1 compatibility warning on Python 3.14+
# This is a known issue with LangChain's pydantic.v1 imports
# Will be resolved when Pydantic 2.13 is released with Python 3.14 support
# See: https://github.com/langchain-ai/langchain/issues/33926
import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater",
    category=UserWarning,
)

from collections.abc import Callable
from typing import Any

from par_gpt.cli.app import app
from par_gpt.commands.agent import create_agent_command
from par_gpt.commands.code_review import create_code_review_command
from par_gpt.commands.generate_prompt import create_generate_prompt_command
from par_gpt.commands.git import create_git_command
from par_gpt.commands.llm import create_llm_command
from par_gpt.commands.sandbox import create_sandbox_command
from par_gpt.commands.simple import create_show_env_command
from par_gpt.commands.stardew import create_stardew_command
from par_gpt.commands.utils import (
    create_pi_profile_command,
    create_publish_repo_command,
    create_tinify_command,
    create_update_deps_command,
)

# Context settings for commands that accept arbitrary extra args / unknown options.
_EXTRA_ARGS_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}

# (command name, factory, accepts_extra_args) — registration order is preserved.
_COMMANDS: list[tuple[str, Callable[[], Any], bool]] = [
    ("show-env", create_show_env_command, False),
    ("llm", create_llm_command, True),
    ("agent", create_agent_command, True),
    ("git", create_git_command, True),
    ("code-review", create_code_review_command, True),
    ("generate-prompt", create_generate_prompt_command, True),
    ("sandbox", create_sandbox_command, False),
    ("update-deps", create_update_deps_command, False),
    ("pub-repo-gh", create_publish_repo_command, False),
    ("tinify", create_tinify_command, False),
    ("pi-profile", create_pi_profile_command, False),
    ("stardew", create_stardew_command, False),
]

# Register all commands with the app
for _name, _factory, _accepts_extra_args in _COMMANDS:
    _kwargs: dict[str, Any] = {"name": _name}
    if _accepts_extra_args:
        _kwargs["context_settings"] = _EXTRA_ARGS_SETTINGS
    app.command(**_kwargs)(_factory())


if __name__ == "__main__":
    app()
