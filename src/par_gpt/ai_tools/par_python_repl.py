"""Python REPL tool."""

import ast
import re
from contextlib import redirect_stdout
from io import StringIO
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.runnables.config import run_in_executor


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
        "When using this tool, sometimes output is abbreviated - "
        "make sure it does not look abbreviated before using it in your answer."
    )
    globals: dict | None = Field(default_factory=dict)
    locals: dict | None = Field(default_factory=dict)
    sanitize_input: bool = True
    args_schema: type[BaseModel] = PythonInputs

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """Use the tool."""
        try:
            if self.sanitize_input:
                query = sanitize_input(query)
            tree = ast.parse(query)
            module = ast.Module(tree.body[:-1], type_ignores=[])
            exec(ast.unparse(module), self.globals, self.locals)  # type: ignore
            module_end = ast.Module(tree.body[-1:], type_ignores=[])
            module_end_str = ast.unparse(module_end)  # type: ignore
            io_buffer = StringIO()
            try:
                with redirect_stdout(io_buffer):
                    ret = eval(module_end_str, self.globals, self.locals)
                    if ret is None:
                        return io_buffer.getvalue()
                    else:
                        return ret
            except Exception:
                with redirect_stdout(io_buffer):
                    exec(module_end_str, self.globals, self.locals)
                return io_buffer.getvalue()
        except Exception as e:
            return f"{type(e).__name__}: {str(e)}"

    async def _arun(
        self,
        query: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> Any:
        """Use the tool asynchronously."""

        return await run_in_executor(None, self._run, query)
