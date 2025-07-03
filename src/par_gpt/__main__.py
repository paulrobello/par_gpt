"""Main application entry point for PAR GPT."""

from __future__ import annotations

# Import the main Typer app from CLI infrastructure
from par_gpt.cli.app import app

# Import all command creators
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

# Register all commands with the app
app.command(name="show-env")(create_show_env_command())
app.command(name="llm", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
    create_llm_command()
)
app.command(name="agent", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
    create_agent_command()
)
app.command(name="git", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
    create_git_command()
)
app.command(name="code-review", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
    create_code_review_command()
)
app.command(name="generate-prompt", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
    create_generate_prompt_command()
)
app.command(name="sandbox")(create_sandbox_command())
app.command(name="update-deps")(create_update_deps_command())
app.command(name="pub-repo-gh")(create_publish_repo_command())
app.command(name="tinify")(create_tinify_command())
app.command(name="pi-profile")(create_pi_profile_command())
app.command(name="stardew")(create_stardew_command())


if __name__ == "__main__":
    app()
