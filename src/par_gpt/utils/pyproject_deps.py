"""Pyproject dependency syncing utilities."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any

import orjson
import tomli_w
from packaging.requirements import Requirement
from par_ai_core.par_logging import console_err
from rich.console import Console


def update_pyproject_deps(
    do_uv_update: bool = True,
    console: Console | None = None,
    dev_only: bool = False,
    main_only: bool = False,
    dry_run: bool = False,
    skip_packages: list[str] | None = None,
) -> None:
    """
    Update dependencies in pyproject.toml with the currently installed versions.

    This function:
      1. Runs 'uv sync -U --all-extras' to update packages to latest compatible versions
      2. Gets the list of installed packages from UV
      3. Updates pyproject.toml to match the installed versions

    Args:
        do_uv_update (bool): Whether to use uv sync to update packages. Defaults to True.
        console (Console | None): Console object for logging. Defaults to console_err.
        dev_only (bool): Update only dev dependencies. Defaults to False.
        main_only (bool): Update only main dependencies. Defaults to False.
        dry_run (bool): Preview changes without applying them. Defaults to False.
        skip_packages (list[str] | None): Additional packages to skip. Defaults to None.

    Returns:
        None
    """
    console = console or console_err
    pyproject_path: Path = Path("pyproject.toml")

    if not pyproject_path.exists():
        console.print("[red]pyproject.toml not found in the expected location.")
        return

    # Step 1: Update packages with UV if requested
    if do_uv_update and not dry_run:
        # Security context for subprocess operation
        try:
            from par_gpt.utils.security_warnings import warn_subprocess_operation

            warn_subprocess_operation(
                operation="Update Python packages with UV", command_args=["uv", "sync", "-U"], console=console
            )
        except ImportError:
            console.print("[blue]🔧 SUBPROCESS: Running UV package update operation[/blue]")

        console.print("[cyan]Running 'uv sync -U --all-extras' to update packages...")
        try:
            subprocess.run(["uv", "sync", "-U", "--all-extras"], check=True)
            console.print("[green]Successfully updated packages with UV")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error: uv sync failed: {e}")
            return

    # Step 2: Get installed package versions from UV
    try:
        from par_gpt.utils.security_warnings import warn_subprocess_operation

        warn_subprocess_operation(
            operation="List installed Python packages",
            command_args=["uv", "pip", "list", "--format", "json"],
            console=console,
        )
    except ImportError:
        console.print("[blue]🔧 SUBPROCESS: Getting package list from UV[/blue]")

    console.print("[cyan]Getting installed package versions from UV...")
    try:
        result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True, check=True)
        installed_packages = orjson.loads(result.stdout)
    except (subprocess.CalledProcessError, orjson.JSONDecodeError) as e:
        console.print(f"[red]Error getting installed packages: {e}")
        return

    # Create a mapping of package names to versions (case-insensitive)
    installed_versions: dict[str, str] = {pkg["name"].lower(): pkg["version"] for pkg in installed_packages}

    # Read and parse the TOML file
    try:
        with open(pyproject_path, "rb") as f:
            toml_data: dict[str, Any] = tomllib.load(f)
    except Exception as e:
        console.print(f"[red]Error reading pyproject.toml: {e}")
        return

    def process_dependencies(deps: list[str], section_name: str) -> list[str]:
        """Process a list of dependencies and return updated versions."""
        updated_deps: list[str] = []

        # Packages that often have compatibility issues - skip these
        skip_list = {
            "pydantic",  # Often has breaking changes with pydantic-core
            "pydantic-core",  # Must match pydantic version
            # Add more problematic packages as needed
        }
        # Add user-specified packages to skip
        if skip_packages:
            skip_list.update(skip_packages)

        for dep in deps:
            try:
                req: Requirement = Requirement(dep)
            except Exception as e:
                console.print(f"[yellow]Failed to parse dependency '{dep}': {e}. Keeping original.")
                updated_deps.append(dep)
                continue

            package_name: str = req.name
            package_name_lower: str = package_name.lower()

            # Preserve extras and markers
            extras_str: str = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
            marker_str: str = f" ; {req.marker}" if req.marker else ""

            # Skip packages in skip list
            if package_name in skip_list:
                console.print(f"[yellow]{section_name}: Skipping {package_name} (in skip list)")
                updated_deps.append(dep)
                continue

            # Get installed version
            installed_version = installed_versions.get(package_name_lower)

            if installed_version is None:
                console.print(
                    f"[yellow]{section_name}: {package_name} not found in installed packages. Keeping original: {dep}"
                )
                updated_deps.append(dep)
                continue

            # Extract current version constraint
            current_version: str | None = None
            for spec in req.specifier:
                if spec.operator in (">=", ">", "=="):
                    current_version = spec.version
                    break

            # Check if update is needed
            if current_version != installed_version:
                new_dep = f"{package_name}{extras_str}>={installed_version}{marker_str}"
                updated_deps.append(new_dep)
                console.print(f"[green]{section_name}: Updated {dep} to {new_dep}")
            else:
                updated_deps.append(dep)
                console.print(f"[blue]{section_name}: {dep} already matches installed version")

        return updated_deps

    changes_made = False

    # Process main dependencies
    if not dev_only:
        project_data: dict[str, Any] | None = toml_data.get("project")
        if project_data and "dependencies" in project_data:
            deps: Any = project_data["dependencies"]
            if isinstance(deps, list):
                console.print("\n[cyan]Processing main dependencies...")
                updated_deps = process_dependencies(deps, "Main")
                if not dry_run:
                    toml_data["project"]["dependencies"] = updated_deps
                changes_made = True
            else:
                console.print("[yellow]Main dependencies should be a list in pyproject.toml.")
        else:
            console.print("[yellow]Main dependencies section not found under [project].")

    # Process dev dependencies
    if not main_only:
        dependency_groups: dict[str, Any] | None = toml_data.get("dependency-groups")
        if dependency_groups and "dev" in dependency_groups:
            dev_deps: Any = dependency_groups["dev"]
            if isinstance(dev_deps, list):
                console.print("\n[cyan]Processing dev dependencies...")
                updated_dev_deps = process_dependencies(dev_deps, "Dev")
                if not dry_run:
                    toml_data["dependency-groups"]["dev"] = updated_dev_deps
                changes_made = True
            else:
                console.print("[yellow]Dev dependencies should be a list in pyproject.toml.")
        else:
            console.print("[yellow]Dev dependencies section not found under [dependency-groups].")

    if not changes_made:
        console.print("[yellow]No dependencies found to process.")
        return

    if dry_run:
        console.print("\n[cyan]Dry run completed. No changes were made to pyproject.toml.")
        return

    # Write the updated TOML data
    try:
        with open(pyproject_path, "wb") as f:
            f.write(tomli_w.dumps(toml_data).encode("utf-8"))
        console.print("\n[green]pyproject.toml updated successfully.")
    except Exception as e:
        console.print(f"[red]Error writing updated pyproject.toml: {e}")
        return
