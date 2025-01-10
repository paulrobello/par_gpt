"""Run Python code in an isolated Docker container.

This module provides functionality to execute Python code safely in Docker containers.
"""

import ast
import os
import sys
import tarfile
import tempfile
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

import docker
import docker.errors
from docker import DockerClient
from RestrictedPython import compile_restricted
from rich.console import Console


@dataclass
class SandboxRunResult:
    """Result of a sandbox operation."""

    status: bool
    message: str


@dataclass
class SandboxCopyFromResult(SandboxRunResult):
    """Result of a copy operation from the container with optional data."""

    data: BytesIO | None = None


class SandboxRun:
    """Execute Python code in an isolated Docker container.

    This class provides functionality to safely execute Python code within Docker containers
    with resource limits and dependency management.

    Example:
        >>> from sandbox import SandboxRun
        >>> runner = SandboxRun(container_name="my_container")
        >>> result = runner.execute_code_in_container("print('Hello, world!')")
        >>> print(result)

    Args:
        container_name (str): Name of the Docker container to use.
        dependencies_whitelist (list[str], optional): List of whitelisted dependencies to install.
            Defaults to ["*"] which allows all dependencies.
        cached_dependencies (list, optional): List of dependencies to cache in the container.
            Defaults to empty list.
        cpu_quota (int, optional): CPU quota in microseconds. Defaults to 50,000.
        default_timeout (int, optional): Default timeout in seconds. Defaults to 20.
        memory_limit (str, optional): Memory limit for the container. Defaults to "100m".
        memswap_limit (str, optional): Memory + swap limit for the container. Defaults to "512m".
        client (DockerClient | None, optional): Docker client object. Defaults to None.
        start_if_needed (bool, optional): Whether to start the container if stopped.
            Defaults to True.
        console (Console | None, optional): Console object for logging. Defaults to None.
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Raises:
        RuntimeError: If unable to connect to Docker daemon.
        ValueError: If container is not found or not running, or if dependencies validation fails.
    """

    def __init__(
        self,
        container_name: str,
        *,
        dependencies_whitelist: list[str] = ["*"],
        cached_dependencies=[],
        cpu_quota: int = 50000,
        default_timeout: int = 20,
        memory_limit: str = "100m",
        memswap_limit: str = "512m",
        client: DockerClient | None = None,
        start_if_needed: bool = True,
        console: Console | None = None,
        verbose: bool = False,
    ) -> None:
        self.cpu_quota = cpu_quota
        self.default_timeout = default_timeout
        self.memory_limit = memory_limit
        self.memswap_limit = memswap_limit
        self.container_name = container_name
        self.dependencies_whitelist = dependencies_whitelist
        self.cached_dependencies = cached_dependencies
        self.console = console or Console(stderr=True)
        self.verbose = verbose

        try:
            self.client = client or docker.from_env()
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker daemon. Please make sure Docker is running. {e}")

        try:
            container = self.client.containers.get(self.container_name)
            if container.status != "running":
                if start_if_needed:
                    container.start()
                else:
                    raise ValueError(f"Container {self.container_name} is not running.")
        except docker.errors.NotFound:
            raise ValueError(f"Container {self.container_name} not found.")

        if not self.is_everything_whitelisted() and not self.validate_cached_dependencies():
            raise ValueError("Some cached dependencies are not in the whitelist.")
        if self.cached_dependencies:
            self.install_cached_dependencies()

        exec_log = container.exec_run(cmd="uv pip list", workdir="/code")
        exit_code, output = exec_log.exit_code, exec_log.output.decode("utf-8")
        if not exit_code:
            installed_packages = output.splitlines()
            self.cached_dependencies = [
                line.split()[0].lower()
                for line in installed_packages
                if (" " in line and not line.startswith("Package ") and not line.startswith("-"))
            ]

    class CommandTimeout(Exception):
        """Exception raised when a command execution times out.

        This exception is raised when a command running in the Docker container
        exceeds its specified timeout duration.
        """

        pass

    def is_everything_whitelisted(self) -> bool:
        """Check if all dependencies are whitelisted.

        Determines if the wildcard "*" is present in the dependencies whitelist,
        indicating that all dependencies are allowed.

        Returns:
            bool: True if all dependencies are whitelisted ("*" is in whitelist),
                False otherwise.
        """
        return "*" in self.dependencies_whitelist

    def validate_cached_dependencies(self) -> bool:
        """Validate cached dependencies against the whitelist.

        Checks if all cached dependencies are either explicitly whitelisted
        or if everything is whitelisted via "*".

        Returns:
            bool: True if all cached dependencies are allowed by the whitelist,
                False otherwise.
        """
        if self.is_everything_whitelisted():
            return True
        return all(dep in self.dependencies_whitelist for dep in self.cached_dependencies)

    def install_cached_dependencies(self) -> None:
        """Install cached dependencies into the Docker container.

        Attempts to install all dependencies listed in self.cached_dependencies
        into the container using the package manager.

        Raises:
            ValueError: If any dependency fails to install or if installation
                process encounters an error.
        """
        output = self.install_dependencies(self.cached_dependencies)
        if not output.status:
            raise ValueError(output.message)

    def execute_command_in_container(self, cmd: str, timeout: int) -> tuple[Any | None, Any | str]:
        """Execute a command in a Docker container with a timeout.

        This function runs the command in a separate thread and waits for the specified timeout.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds
        Returns:
            Tuple of exit code and output

        """
        container = self.client.containers.get(self.container_name)

        exit_code, output = None, None

        def target():
            nonlocal exit_code, output
            exec_log = container.exec_run(cmd=cmd, workdir="/code")
            exit_code, output = exec_log.exit_code, exec_log.output

        thread = Thread(target=target)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            thread.join(1)
            raise self.CommandTimeout("Command timed out")
        output = output if output is not None else b""
        return exit_code, output.decode("utf-8")

    @staticmethod
    def safety_check(python_code: str) -> SandboxRunResult:
        """Check if Python code is safe to execute.
        This function uses common patterns and RestrictedPython to check for unsafe patterns in the code.

        Args:
            python_code: Python code to check
        Returns:
           SandboxRunResult
        """

        # Crude check for problematic code (os, sys, subprocess, exec, eval, etc.)
        # unsafe_modules = {"os", "sys", "subprocess", "builtins"}
        unsafe_modules = {"sys", "subprocess", "builtins"}
        unsafe_functions = {
            "exec",
            "eval",
            "compile",
            "open",
            "input",
            "__import__",
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
        }
        dangerous_builtins = {
            "globals",
            "locals",
            "vars",
            "dir",
            "eval",
            "exec",
            "compile",
        }
        # this a crude check first - no need to compile the code if it's obviously unsafe. Performance boost.
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return SandboxRunResult(status=False, message=f"Syntax error: {str(e)}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in dangerous_builtins:
                return SandboxRunResult(status=False, message=f"Use of dangerous built-in function: {node.func.id}")

            # Check for unsafe imports
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                module_name = node.module if isinstance(node, ast.ImportFrom) else None
                for alias in node.names:
                    if module_name and module_name.split(".")[0] in unsafe_modules:
                        SandboxRunResult(status=False, message=f"Unsafe module import: {module_name}")

                    if alias.name.split(".")[0] in unsafe_modules:
                        return SandboxRunResult(status=False, message=f"Unsafe module import: {alias.name}")

            # Check for unsafe function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in unsafe_functions:
                    return SandboxRunResult(status=False, message=f"Unsafe function call: {node.func.id}")

                elif isinstance(node.func, ast.Attribute) and node.func.attr in unsafe_functions:
                    return SandboxRunResult(status=False, message=f"Unsafe function call: {node.func.attr}")

        try:
            # Compile the code using RestrictedPython with a filename indicating its dynamic nature
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                compile_restricted(python_code, filename="<dynamic>", mode="exec")

            # Note: Execution step is omitted to only check the code without running it
            # This is not perfect, but should catch most unsafe patterns
        except Exception as e:
            return SandboxRunResult(status=False, message=f"RestrictedPython detected an unsafe pattern: {str(e)}")

        return SandboxRunResult(status=True, message="The code is safe to execute.")

    @staticmethod
    def parse_dependencies(python_code: str) -> list[str]:
        """Parse Python code to find import statements and filter out standard library modules.
        This function returns a list of unique dependencies found in the code.

        Args:
            python_code: Python code to parse
        Returns:
            List of unique dependencies
        """
        tree = ast.parse(python_code)
        dependencies = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get the base module name. E.g. for "import foo.bar", it's "foo"
                    module_name = alias.name.split(".")[0]
                    if module_name not in sys.stdlib_module_names and module_name not in sys.builtin_module_names:
                        dependencies.append(module_name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module.split(".")[0] if node.module else ""
                if (
                    module_name
                    and module_name not in sys.stdlib_module_names
                    and module_name not in sys.builtin_module_names
                ):
                    dependencies.append(module_name)
        return list(set(dependencies))  # Return unique dependencies

    def install_dependencies(self, dependencies: list[str]) -> SandboxRunResult:
        """Install dependencies in the container.
        Args:
            dependencies: List of dependencies to install
        Returns:
            SandboxRunResult
        """
        container = self.client.containers.get(self.container_name)

        everything_whitelisted = self.is_everything_whitelisted()

        # Perform a pre-check to ensure all dependencies are in the whitelist (or everything is whitelisted)
        if not everything_whitelisted:
            for dep in dependencies:
                if dep not in self.dependencies_whitelist:
                    return SandboxRunResult(status=False, message=f"Dependency: {dep} is not in the whitelist.")

        lines = []
        file_name = ""
        for dep in [d for d in dependencies if d.lower() not in self.cached_dependencies]:
            lines.append(dep)
        if lines:
            result = self.copy_requirements_container("\n".join(lines))
            if not result.status:
                return result
            command = f"uv pip install -r {result.message}"
            if self.verbose:
                self.console.print(command)
            exec_log = container.exec_run(cmd=command, workdir="/code")
            exit_code, output = exec_log.exit_code, exec_log.output.decode("utf-8")
            if exit_code != 0:
                self.console.print(output)
                return SandboxRunResult(status=False, message="Failed to install dependencies")
            file_name = result.message

        return SandboxRunResult(status=True, message=file_name)

    def uninstall_dependencies(self, dependencies: list, timeout: int = 120) -> str:
        """Uninstall dependencies in the container.
        Args:
            dependencies: List of dependencies to uninstall
            timeout: Timeout in seconds
        Returns:
            Success message or error message
        """
        for dep in dependencies:
            # do not uninstall dependencies that are cached_dependencies
            if dep in self.cached_dependencies:
                continue
            command = f"uv pip uninstall -y {dep}"
            exit_code, output = self.execute_command_in_container(command, timeout=timeout)

        return "Dependencies uninstalled successfully."

    def copy_file_from_container(self, src_file_name: str, dest_file_name: str | None = None) -> SandboxCopyFromResult:
        """Copy file from the container.

        Args:
            src_file_name: File name to copy from the container.
            dest_file_name: Destination file name in the system's temp folder. If None copy to data attribute.

        Returns:
            SandboxCopyFromResult
        Raises:
            Exception: If there's an error during the file copying process.
        """
        container = self.client.containers.get(self.container_name)

        tar_stream = BytesIO()
        bits, stat_info = container.get_archive(f"/code/{src_file_name}")
        for chunk in bits:
            tar_stream.write(chunk)
        tar_stream.seek(0)

        try:
            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                file_info = tar.getmember(src_file_name)
                extracted_file = tar.extractfile(file_info)
                if extracted_file:
                    if dest_file_name:
                        # Write the content to a file in the system's temp folder
                        temp_dir = tempfile.gettempdir()
                        dest_path = os.path.join(temp_dir, dest_file_name)

                        with open(dest_path, "wb") as f:
                            f.write(extracted_file.read())

                        return SandboxCopyFromResult(status=True, message=dest_path)
                    else:
                        data = BytesIO(extracted_file.read())
                        data.seek(0)
                        return SandboxCopyFromResult(status=True, message="File copy successful.", data=data)
                else:
                    return SandboxCopyFromResult(
                        status=False, message=f"Failed to extract {src_file_name} from tar archive."
                    )
        except Exception as e:
            return SandboxCopyFromResult(
                status=False, message=f"Failed to copy {src_file_name} from container: {str(e)}"
            )

    def copy_file_to_container(self, file_name: str, content: str) -> SandboxRunResult:
        """Copy file to the container.
        Args:
            file_name: File name to copy
            content: Content of the file
        Returns:
            SandboxRunResult
        """
        container = self.client.containers.get(self.container_name)

        temp_script_path = os.path.join("/tmp", file_name)

        with open(temp_script_path, "w") as file:
            file.write(content)

        tar_stream = BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.add(temp_script_path, arcname=file_name)
        tar_stream.seek(0)

        exec_result = container.put_archive(path="/code/", data=tar_stream)
        if exec_result:
            return SandboxRunResult(status=True, message=file_name)

        return SandboxRunResult(status=False, message=f"Failed to copy {file_name} to container.")

    def copy_requirements_container(self, requirements: str) -> SandboxRunResult:
        """Copy Python requirements file to container.
        Args:
            requirements: file contents
        Returns:
           SandboxRunResult
        """
        if self.verbose:
            self.console.print("Copying requirements to container...")
            self.console.print(requirements)
        file_name = f"requirements_{uuid4().hex}.txt"
        return self.copy_file_to_container(file_name, requirements)

    def copy_code_to_container(self, python_code: str) -> SandboxRunResult:
        """Copy Python code to the container.
        Args:
            python_code: Python code to copy
        Returns:
            SandboxRunResult
        """
        if self.verbose:
            self.console.print("Copying script to container...")

        script_name = f"script_{uuid4().hex}.py"
        return self.copy_file_to_container(script_name, python_code)

    def remove_files(self, files: list[str]) -> None:
        """Clean up the container after execution.
        Args:
            files: List of files to clean up
        """
        container = self.client.containers.get(self.container_name)

        for script_name in files:
            if not script_name:
                continue
            (Path("/tmp") / script_name).unlink(missing_ok=True)
            container.exec_run(cmd=f"rm /code/{script_name}", workdir="/code")
        return None

    def execute_code_in_container(self, python_code: str) -> str:
        """Executes Python code in an isolated Docker container.
        This is the main function to execute Python code in a Docker container. It performs the following steps:
        1. Check if the code is safe to execute
        2. Update the container with the memory limits
        3. Copy the code to the container
        4. Install dependencies in the container
        5. Execute the code in the container
        5. Uninstall dependencies in the container & clean up

        Args:
            python_code: Python code to execute
        Returns:
            Output of the code execution or an error message
        """

        container = None
        script_name = ""
        requirements_name = ""
        try:
            client = self.client
            timeout_seconds = self.default_timeout

            # check  if the code is safe to execute
            safety_result = self.safety_check(python_code)
            safety_message = safety_result.message
            safe = safety_result.status
            if not safe:
                return safety_message

            container = client.containers.get(self.container_name)

            # update the container with the new limits
            container.update(
                cpu_quota=self.cpu_quota,
                mem_limit=self.memory_limit,
                memswap_limit=self.memswap_limit,
            )

            # Copy the code to the container
            exec_result = self.copy_code_to_container(python_code)
            successful_copy = exec_result.status
            message = exec_result.message
            if not successful_copy:
                return message

            script_name = message

            # Install dependencies in the container
            dependencies = self.parse_dependencies(python_code)
            dep_install_result = self.install_dependencies(dependencies)
            if not dep_install_result.status:
                return dep_install_result.message
            requirements_name = dep_install_result.message

            try:
                _, output = self.execute_command_in_container(f"uv run /code/{script_name}", timeout_seconds)
            except self.CommandTimeout:
                return "Execution timed out."

        except Exception as e:
            return str(e)

        finally:
            if container:
                # run clean up in a separate thread to avoid blocking the main thread
                thread = Thread(target=self.remove_files, args=(container, [script_name, requirements_name]))
                thread.start()

        return output
