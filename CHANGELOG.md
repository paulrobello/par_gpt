# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Test suite (74+ tests) covering AI tools, utils, managers, and the repo subsystem; tests now run via `make test` and are included in `make checkall`.
- `CHANGELOG.md` and `CONTRIBUTING.md`.
- `docs/DOCUMENTATION_STYLE_GUIDE.md` — committed prose/diagram conventions for all project documentation.
- Consolidated environment-variable reference table in README.

### Changed
- Python version requirement tightened to `>=3.12,<3.15` across pyproject.toml, ruff, pyright, README, and CLAUDE.md (3.13 recommended).
- `utils.py` consolidated into a `utils/` package with lazy-loaded submodules (ARC-001).
- Lazy-import manager hardened to a thread-safe singleton (ARC-002/003).
- README table of contents added; all `echo "..." | par_gpt` examples rewritten to the preferred `par_gpt "prompt"` form.
- CLAUDE.md stale version-specific changelog replaced with a pointer to this file.

### Fixed
- `code_review` command name corrected to `code-review` (hyphen) throughout README.
- Dead `PATH_SECURITY_SUMMARY.md` link replaced with inline security note.
- Missing `extraction_prompt.md` removed from the sdist include list (was breaking `uv build --sdist`).
- Descriptive error messages on `FileNotFoundError` in the repo tool; consistent `"Error: {type}: {detail}"` convention across AI tools so the agent can distinguish success from failure.
- Multiple code-quality improvements across AI tools, utils submodules, managers, and the error subsystem (QA-001 through QA-015).
- Pre-existing invalid `.pre-commit-config.yaml` (gitleaks block indentation) — `pre-commit validate-config` now passes.

### Security
- **Host code execution no longer auto-confirms**: the `--repl` host REPL confirmation prompt now defaults to "no" and `--yes-to-all` no longer bypasses it. Use `--code-sandbox` for unsupervised runs (SEC-001).
- **Sandbox no longer fails open**: the AST `safety_check` now rejects `from <module> import <name>` of unsafe symbols (e.g. `from subprocess import call`) and restores `os` to the unsafe-module list (SEC-002).
- **Git commits run hooks by default**: `git_commit_tool` no longer passes `--no-verify`; pre-commit secret-scanning (e.g. `gitleaks`) runs unless explicitly bypassed (SEC-003).
- **SSRF guard on URL tools**: `ai_fetch_url`/`ai_open_url` now validate schemes (`http`/`https`) and reject hostnames that resolve to loopback/private/link-local/metadata addresses via a new `validate_url` helper (SEC-004).
- **Hardened host-REPL namespace**: `os`/`sys` are no longer pre-loaded into the host REPL exec namespace (SEC-005).

> This release is the result of a full project audit and its remediation. 68 of 71 issues were resolved; ARC-004 (typed command state), ARC-006 (tool-selection design), and ARC-007 (package splitting) are intentionally deferred as larger, separately-scheduled efforts. See `git log` for the per-phase commits.

## [0.15.0] - 2025-11-24

### Changed
- **Python version support**: Now requires Python 3.12+ (supports 3.12–3.14; 3.13 recommended).
- Type safety improvements across multiple modules.
- Dependencies updated to use `--all-extras` flag for comprehensive dependency management.
- CLI configuration and command handling improved with better type annotations.
- Agent command handling and lazy import management enhanced.
- Python REPL AI tool improved with better type safety.

## [0.14.1] - 2025-08-11

### Fixed
- **Tinify command**: Fixed image compression percentage calculation that was always showing 0% reduction. Root cause: when no output file was specified, the command overwrote the original file and compared compressed size with itself. Implemented proper temporary file handling with accurate size comparison and error cleanup.

## [0.14.0] - 2025-08-07

### Added
- **PAR Utils package**: Extracted reusable utilities into a separate `src/par_utils/` package with organized modules (`performance/`, `security/`, `errors/`, `caching/`, `console/`).
- Advanced user-interaction timing: dual grand totals (Grand Total vs Processing Total excluding user wait time), categorized tracking of security confirmations and interactive prompts.
- Architecture documentation updated to reflect the modular package structure.

### Changed
- Path security now uses `SecurePathValidator` with multiple validation layers.
- Lazy loading improved with `LazyImportManager` and `LazyUtilsLoader`.

### Removed
- Legacy duplicate files (`timing.py`, `error_registry.py`, `console_manager.py`, `cache_manager.py`) — functionality preserved in par_utils.

## [0.13.0] - 2025-07-03

### Fixed
- **AI tools import fix**: Resolved critical import issues affecting 10+ AI tools:
  - Screen capture tools (`ai_capture_screen_image`, `ai_capture_window_image`) for multi-monitor support.
  - Image generation (`ai_image_gen_dali`) for DALL-E.
  - Text generation (`ai_figlet`) for ASCII art.
  - GitHub integration (`ai_github_publish_repo`).
  - System interaction (`ai_list_visible_windows`, `ai_list_available_screens`).
  - Terminal image display (`ai_display_image_in_terminal`).
  - Root cause: utils package restructuring broke facade-pattern imports; fixed by extending utils `__init__.py` with dynamic loading.

### Changed
- Command syntax standardized to `uv run par_gpt "prompt"` instead of `echo "prompt" | uv run par_gpt agent`.
- Monolithic CLI refactored into modular architecture.

## [0.12.2]

### Added
- Global `--yes-to-all` security bypass flag for headless/scripted automation, with cross-tool support and `PARGPT_YES_TO_ALL` environment variable.
- Comprehensive startup performance optimization reducing startup time by 25–50% via command-specific import routing, lazy import manager with caching, and deferred global initialization.

### Changed
- Optimized command performance: `--version` (~1.45s), `show-env` (~1.5s), `llm` (significant startup improvement).

## [0.12.1]

### Added
- Lazy loading for AI tools, reducing startup time by ~10% (heavy imports deferred until needed).
- Performance monitoring: `--show-times` and `--show-times-detailed` CLI options with Rich-formatted output.
- Optional Redis memory system with smart defaults (disabled by default, `--enable-redis` flag, graceful fallback).

## [0.12.0]

### Added
- Screen capture tools with multi-monitor support (`ai_list_available_screens`, `ai_capture_screen_image`).
- Comprehensive path traversal protection across all file operations.

### Fixed
- Critical audio processing memory leaks with resource cleanup.

## [0.11.0]

### Added
- Stardew subcommand for creating pixel art avatar variations.

## [0.10.0]

### Fixed
- Sixel error on Windows.

## [0.8.0]

### Added
- Tinify image compression command.

## [0.7.1]

### Changed
- Updated PAR AI Core: OpenAI Reasoning Effort and Anthropic Reasoning token budget support.

## [0.7.0]

### Changed
- Updated PAR AI Core: Deepseek and LiteLLM support.

## [0.6.0]

### Added
- TTS output and screenshot support.

### Removed
- Aider support.

## [0.5.0]

### Added
- Aider command for code editing.

## [0.4.0]

### Changed
- Reworked subcommands and CLI options.

## [0.3.0]

### Added
- LlamaCPP support, code review agent, prompt generation agent.

## [0.2.1]

### Added
- Auto-detected context source, vision model selection, clipboard options.

## [0.2.0]

### Added
- Confirmation prompts, yes-to-all flag.
- Updated pricing data.

## [0.1.0]

- Initial release.
