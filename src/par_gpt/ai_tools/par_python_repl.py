"""Python REPL tool. Adapted from Langchain PythonAstREPLTool."""

import ast
import re
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.runnables.config import run_in_executor
from langchain_core.tools import BaseTool
from par_ai_core.par_logging import console_err
from pydantic import BaseModel, Field
from rich.console import Console
from rich.prompt import Prompt


class AbortedByUserError(Exception):
    """Raised when user aborts."""


def sanitize_input(query: str) -> str:
    """Sanitize input to the python REPL.

    Remove whitespace, backtick & python (if llm mistakes python console as terminal)

    Args:
        query: The query to sanitize

    Returns:
        str: The sanitized query
    """

    # Removes `, whitespace & python from start
    query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
    # Removes whitespace & ` from end
    query = re.sub(r"(\s|`)*$", "", query)
    return query


class PythonInputs(BaseModel):
    """Python inputs."""

    query: str = Field(description="code snippet to run")


class ParPythonAstREPLTool(BaseTool):
    """Tool for running python code in a REPL."""

    name: str = "par_python_repl_ast"
    description: str = (
        "A Python shell. Use this to execute python commands. "
        "Input should be a valid python command. "
        "Can be used to handle complicated mathematical operations. "
        "When using this tool, sometimes output is abbreviated - "
        "make sure it does not look abbreviated before using it in your answer."
    )
    globals: dict | None = Field(default_factory=dict)  # type: ignore
    locals: dict | None = Field(default_factory=dict)  # type: ignore
    args_schema: type[BaseModel] = PythonInputs

    sanitize_input: bool = True
    """Sanitize input to the python REPL.
        Remove whitespace, backtick & python (if llm mistakes python console as terminal)
    """
    prompt_before_exec: bool = True
    """Prompt before executing."""
    show_exec_code: bool = False
    """Show code before executing."""
    console: Console | None = None
    """Rich console to use for output defaults to stderr."""

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """Execute Python code in a controlled environment.

        Args:
            query: The Python code to execute
            run_manager: Optional callback manager for tool run

        Returns:
            str: The result of the code execution or error message
        """
        if not self.console:
            self.console = console_err
        if not self.locals:
            self.locals = {}
        if "console" not in self.locals:
            self.locals["console"] = self.console
        try:
            if self.sanitize_input:
                query = sanitize_input(query)
            if self.prompt_before_exec:
                ans = Prompt.ask(
                    f"Execute>>>\n[yellow]{query}[/yellow]\n<<<[[green]Y[/green]/[red]n[/red]] ? ",
                    default="y",
                    console=self.console,
                )
                if ans.lower() not in ["y", "yes", ""]:
                    raise (AbortedByUserError("Tool aborted by user."))
            elif self.show_exec_code:
                self.console.print(f"Executing>>>\n[yellow]{query}[/yellow]\n")

            tree = ast.parse(query)
            module = ast.Module(tree.body[:-1], type_ignores=[])
            exec(ast.unparse(module), self.globals, self.locals)  # type: ignore
            module_end = ast.Module(tree.body[-1:], type_ignores=[])
            module_end_str = ast.unparse(module_end)  # type: ignore
            io_buffer = StringIO()
            try:
                with redirect_stdout(io_buffer):
                    with redirect_stderr(io_buffer):
                        ret = eval(module_end_str, self.globals, self.locals)
                if ret is None:
                    ret = io_buffer.getvalue()
            except Exception as _:
                with redirect_stdout(io_buffer):
                    with redirect_stderr(io_buffer):
                        exec(module_end_str, self.globals, self.locals)
                ret = io_buffer.getvalue()
            if self.show_exec_code and self.console:
                self.console.print("[blue]Result>>>")
                print(ret)
            return ret
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)}"
            if self.console:
                self.console.print("[bold red]Error:")
                self.console.print(msg, markup=False)
            return msg

    async def _arun(
        self,
        query: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> Any:
        """Use the tool asynchronously."""

        return await run_in_executor(None, self._run, query)


class ParPythonREPLTool(BaseTool):
    """Tool for running python code in a REPL."""

    name: str = "par_python_repl"
    description: str = (
        "A Python shell. Use this to execute python commands. "
        "Input should be a valid python command. "
        "Can be used to handle complicated mathematical operations. "
        "If you want to see the output of a value, you should print it out "
        "with `print(...)`."
    )
    globals: dict | None = Field(default_factory=dict)  # type: ignore
    locals: dict | None = Field(default_factory=dict)  # type: ignore
    args_schema: type[BaseModel] = PythonInputs

    sanitize_input: bool = True
    """Sanitize input to the python REPL.
        Remove whitespace, backtick & python (if llm mistakes python console as terminal)
    """
    prompt_before_exec: bool = True
    """Prompt before executing."""
    show_exec_code: bool = False
    """Show code before executing."""
    console: Console | None = None
    """Rich console to use for output defaults to stderr."""

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """Execute Python code in a controlled environment.

        Args:
            query: The Python code to execute
            run_manager: Optional callback manager for tool run

        Returns:
            str: The result of the code execution or detailed error message
        """
        if not self.console:
            self.console = console_err
        try:
            if self.sanitize_input:
                query = sanitize_input(query)

            tree = ast.parse(query)
            query = ast.unparse(ast.Module(tree.body, type_ignores=[]))

            if self.prompt_before_exec:
                ans = Prompt.ask(
                    f"Execute>>>\n[yellow]{query}[/yellow]\n<<<[[green]Y[/green]/[red]n[/red]] ? ",
                    default="y",
                    console=self.console,
                )
                if ans.lower() not in ["y", "yes", ""]:
                    raise AbortedByUserError("Tool aborted by user.")
            elif self.show_exec_code:
                self.console.print(f"Executing>>>\n[yellow]{query}[/yellow]\n")

            io_buffer = StringIO()
            with redirect_stdout(io_buffer), redirect_stderr(io_buffer):
                self.console.print("Running...")
                ret = eval(query, self.globals, self.locals)
                if ret is None:
                    ret = io_buffer.getvalue()
                if self.show_exec_code:
                    self.console.print(f"Result>>>\n[cyan]{query}[/cyan]\n")
                return str(ret)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.console.print("[bold red]Error:", error_msg, markup=False)
            return error_msg

    async def _arun(
        self,
        query: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> Any:
        """Use the tool asynchronously."""

        return await run_in_executor(None, self._run, query)
