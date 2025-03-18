"""
CLI tool to analyze pyinstrument JSON profile reports and generate an AI-friendly summary.

This script filters profile data based on specified modules and produces a markdown
summary of the top time-consuming functions.
"""

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown


def is_in_scope(node: dict[str, Any], modules_in_scope: list[str]) -> bool:
    """
    Check if a node is within the scope of specified modules.

    Args:
        node: Profile node to check
        modules_in_scope: List of module paths to include in results

    Returns:
        bool: True if node is in scope, False otherwise
    """
    if not modules_in_scope:
        return True

    file_path = node.get("file_path", "")
    return any(module in file_path for module in modules_in_scope)


def extract_function_info(node: dict[str, Any], modules_in_scope: list[str], functions: list[dict[str, Any]]) -> None:
    """
    Recursively extract function information from profile nodes.

    Args:
        node: Current profile node to process
        modules_in_scope: List of module paths to include in results
        functions: List to store extracted function information
    """
    # Get function name
    function_name = node.get("function", "")

    # Add function to list if it's in scope and not named "<module>"
    if is_in_scope(node, modules_in_scope) and function_name != "<module>":
        functions.append(
            {
                "function": function_name,
                "file_path": node.get("file_path", ""),
                "line_no": node.get("line_no", 0),
                "time": node.get("time", 0),
            }
        )

    for child in node.get("children", []):
        extract_function_info(child, modules_in_scope, functions)


def generate_markdown_report(
    functions: list[dict[str, Any]], limit: int = 10, modules_in_scope: list[str] | None = None
) -> str:
    """
    Generate a markdown report of the top time-consuming functions.

    Args:
        functions: List of function information dictionaries
        limit: Maximum number of functions to include in the report
        modules_in_scope: List of modules that were included in the scope

    Returns:
        str: Markdown report string
    """
    # Sort functions by time (descending)
    sorted_functions = sorted(functions, key=lambda x: x.get("time", 0), reverse=True)

    # Take top N functions or fewer if less than N functions are available
    top_functions = sorted_functions[:limit]
    report = StringIO()
    with report as f:
        f.write("# Profile Analysis Summary\n\n")

        # Add modules in scope section
        f.write("## Modules in Scope\n\n")
        if modules_in_scope and len(modules_in_scope) > 0:
            for module in modules_in_scope:
                f.write(f"- `{module}`\n")
        else:
            f.write("- All modules (no filtering applied)\n")

        f.write("\n## Top Time-Consuming Functions\n\n")
        f.write("| Rank | Function | File | Line | Time (s) |\n")
        f.write("|------|----------|------|------|----------|\n")

        for i, func in enumerate(top_functions, 1):
            f.write(f"| {i} | `{func['function']}` | {func['file_path']} | {func['line_no']} | {func['time']:.6f} |\n")
        return report.getvalue()


class ProfileAnalysisError(Exception):
    """Exception raised for errors during profile analysis."""

    pass


def process_profile(
    profile_path: Path | str,
    modules_in_scope: list[str] | None = None,
    output_path: Path | str | None = None,
    limit: int = 10,
) -> str:
    """
    Process a pyinstrument JSON profile report and generate a markdown summary.

    Args:
        profile_path: Path to the profile JSON file
        modules_in_scope: List of modules to include in the analysis (None for all)
        output_path: Path for the output markdown file (None for default)
        limit: Maximum number of functions to include in the report

    Returns:
        Path to the generated markdown report

    Raises:
        ProfileAnalysisError: If errors occur during analysis
    """
    # Convert to Path object if string
    if isinstance(profile_path, str):
        profile_path = Path(profile_path)

    # Validate profile JSON file exists
    if not profile_path.exists():
        raise ProfileAnalysisError(f"Profile JSON file not found: {profile_path}")

    # Load profile data
    try:
        with open(profile_path, encoding="utf-8") as f:
            profile_data = json.load(f)
    except json.JSONDecodeError:
        raise ProfileAnalysisError(f"Invalid JSON in profile file: {profile_path}")
    except Exception as e:
        raise ProfileAnalysisError(f"Failed to read profile file: {e}")

    # Extract root frame
    root_frame = profile_data.get("root_frame", {})
    if not root_frame:
        raise ProfileAnalysisError("No root frame found in profile data")

    # Process modules in scope (empty list if None)
    modules = modules_in_scope or []

    # Extract function information
    functions = []
    extract_function_info(root_frame, modules, functions)

    if not functions:
        raise ProfileAnalysisError("No functions found in the specified scope")

    # Generate the markdown report
    report = generate_markdown_report(functions=functions, limit=limit, modules_in_scope=modules)

    # Generate markdown report path
    if output_path is None:
        return report

    if isinstance(output_path, str):
        output_path = Path(output_path)

    output_path.write_text(report, encoding="utf-8")

    return report


def main() -> None:
    """Parse arguments and process the profile report."""
    parser = argparse.ArgumentParser(
        description="Process pyinstrument JSON profile reports and generate AI-friendly summaries"
    )
    parser.add_argument("profile_json", type=str, help="Path to the pyinstrument JSON profile report")
    parser.add_argument(
        "--module", "-m", action="append", help="Module to include in analysis (can be specified multiple times)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output markdown file path (default: screen)",
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Maximum number of functions to include in the report (default: 10)"
    )

    args = parser.parse_args()
    console = Console()

    try:
        report = process_profile(
            profile_path=args.profile_json, modules_in_scope=args.module, output_path=args.output, limit=args.limit
        )
        if args.output:
            console.print(f"[bold green]Success:[/] Profile summary written to {args.output}")
        else:
            console.print(Markdown(report))
    except ProfileAnalysisError as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
