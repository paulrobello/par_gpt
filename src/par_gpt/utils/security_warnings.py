"""Security warning utilities for dangerous operations.

This module provides reusable functions for displaying prominent security warnings
when PAR GPT performs potentially dangerous operations that could affect system security.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def warn_command_execution(
    command: str,
    operation_description: str,
    *,
    console: Console | None = None,
    skip_confirmation: bool = False,
) -> bool:
    """Display a prominent warning for command execution and get user confirmation.

    Args:
        command: The command that will be executed
        operation_description: Human-readable description of what the operation does
        console: Rich console instance (defaults to stderr)
        skip_confirmation: If True, display warning but skip confirmation prompt

    Returns:
        bool: True if user confirmed or skip_confirmation=True, False if denied

    Raises:
        KeyboardInterrupt: If user presses Ctrl+C during confirmation
    """
    if console is None:
        console = Console(stderr=True)

    warning_text = f"""[bold red]⚠️  SECURITY WARNING ⚠️[/bold red]

[yellow]Operation:[/yellow] {operation_description}
[yellow]Command:[/yellow] [cyan]{command}[/cyan]

[bold red]This operation will execute a system command that could:
• Access or modify files on your system
• Interact with system resources
• Potentially be exploited if inputs are malicious[/bold red]

[yellow]Only proceed if you trust the operation and understand the risks.[/yellow]"""

    console.print(Panel(warning_text, border_style="red", title="[bold red]DANGER[/bold red]"))

    if skip_confirmation:
        return True

    try:
        response = Prompt.ask(
            "[bold]Do you want to proceed?[/bold] [green][[Y]es[/green]/[red][N]o[/red]]",
            default="N",
            console=console,
        )
        return response.lower() in ["y", "yes"]
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user.[/red]")
        return False


def warn_environment_modification(
    var_name: str,
    var_value: str,
    *,
    console: Console | None = None,
    skip_confirmation: bool = False,
) -> bool:
    """Display a warning for environment variable modification.

    Args:
        var_name: Name of the environment variable being set
        var_value: Value being assigned (will be truncated for security)
        console: Rich console instance (defaults to stderr)
        skip_confirmation: If True, display warning but skip confirmation prompt

    Returns:
        bool: True if user confirmed or skip_confirmation=True, False if denied
    """
    # Disable output until user turns it back on.ß
    if skip_confirmation:
        return True
    if console is None:
        console = Console(stderr=True)

    # Truncate value for security (don't show full API keys, etc.)
    display_value = var_value[:20] + "..." if len(var_value) > 20 else var_value

    warning_text = f"""[bold yellow]⚠️  ENVIRONMENT MODIFICATION ⚠️[/bold yellow]

[yellow]Setting environment variable:[/yellow] [cyan]{var_name}[/cyan]
[yellow]Value:[/yellow] [cyan]{display_value}[/cyan]

[yellow]This will modify your process environment and may affect:
• Application configuration
• Security settings
• Other running processes (if inherited)[/yellow]"""

    console.print(Panel(warning_text, border_style="yellow", title="[bold yellow]ENVIRONMENT CHANGE[/bold yellow]"))

    if skip_confirmation:
        return True

    try:
        response = Prompt.ask(
            "[bold]Continue with environment modification?[/bold] [green][[Y]es[/green]/[red][N]o[/red]]",
            default="Y",
            console=console,
        )
        return response.lower() in ["y", "yes"]
    except KeyboardInterrupt:
        console.print("\n[red]Environment modification cancelled.[/red]")
        return False


def warn_code_execution(
    code: str,
    execution_context: str = "Python REPL",
    *,
    console: Console | None = None,
    skip_confirmation: bool = False,
) -> bool:
    """Display a prominent warning for code execution and get user confirmation.

    Args:
        code: The code that will be executed (will be truncated for display)
        execution_context: Description of where code will run (e.g., "Python REPL", "Docker sandbox")
        console: Rich console instance (defaults to stderr)
        skip_confirmation: If True, display warning but skip confirmation prompt

    Returns:
        bool: True if user confirmed or skip_confirmation=True, False if denied
    """
    if console is None:
        console = Console(stderr=True)

    # Truncate code for display while preserving readability
    display_code = code[:200] + "\n..." if len(code) > 200 else code

    warning_text = f"""[bold red]🔥 CODE EXECUTION WARNING 🔥[/bold red]

[yellow]Execution Context:[/yellow] {execution_context}
[yellow]Code to execute:[/yellow]
[cyan]{display_code}[/cyan]

[bold red]This will execute arbitrary code that could:
• Access your files and system resources
• Make network requests
• Install packages or modify your environment
• Potentially cause system damage or data loss[/bold red]

[bold yellow]⚠️  ONLY PROCEED IF YOU TRUST THIS CODE ⚠️[/bold yellow]"""

    console.print(Panel(warning_text, border_style="red", title="[bold red]⚠️  DANGER: CODE EXECUTION ⚠️[/bold red]"))

    if skip_confirmation:
        return True

    try:
        response = Prompt.ask(
            "[bold red]Execute this code?[/bold red] [green][[Y]es[/green]/[red][N]o[/red]]",
            default="N",
            console=console,
        )
        return response.lower() in ["y", "yes"]
    except KeyboardInterrupt:
        console.print("\n[red]Code execution cancelled by user.[/red]")
        return False


def warn_subprocess_operation(
    operation: str,
    command_args: list[str] | None = None,
    *,
    console: Console | None = None,
) -> None:
    """Display an informational warning for subprocess operations.

    This provides security context for operations that use subprocess
    but are generally considered safer than direct shell execution.

    Args:
        operation: Description of the operation being performed
        command_args: Command arguments being executed (optional)
        console: Rich console instance (defaults to stderr)
    """
    if console is None:
        console = Console(stderr=True)

    command_display = ""
    if command_args:
        command_display = f"\n[yellow]Command:[/yellow] [cyan]{' '.join(command_args)}[/cyan]"

    info_text = f"""[bold blue]🔧 SUBPROCESS OPERATION[/bold blue]

[yellow]Operation:[/yellow] {operation}{command_display}

[blue]This operation uses subprocess execution with controlled arguments.
While safer than shell commands, it still interacts with external programs.[/blue]"""

    console.print(Panel(info_text, border_style="blue", title="[bold blue]SUBPROCESS INFO[/bold blue]"))
