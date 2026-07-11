# Contributing to PAR GPT

Thanks for your interest in contributing! This guide covers the environment, the required quality gate, and the conventions the project follows. For prose/documentation conventions, see [`docs/DOCUMENTATION_STYLE_GUIDE.md`](docs/DOCUMENTATION_STYLE_GUIDE.md).

## Requirements

- **Python 3.12 or higher (3.13 recommended)** — the project targets `>=3.12,<3.15`.
- [UV](https://docs.astral.sh/uv/) package manager.
- API keys for your chosen AI provider (Ollama and LlamaCpp need none). See the [Environment Variables](README.md#environment-variables) reference.
- Optional: `ffmpeg` for image/audio features, `portaudio` for audio input.

## Setup

```bash
git clone https://github.com/paulrobello/par_gpt.git
cd par_gpt
make setup          # creates the venv via UV and installs dependencies
```

If anything behaves oddly, recreate the environment from scratch with `make resetup`.

## The required quality gate

**Every pull request must pass `make checkall` before it is merged.** This runs the full gate:

```bash
make checkall       # format + lint + typecheck + test
```

Individual stages (useful while iterating):

| Target | What it does |
|--------|--------------|
| `make format` | Reformat code with `ruff` |
| `make lint` | Lint with `ruff` |
| `make typecheck` | Static type checks with `pyright` |
| `make test` | Run the pytest suite under `tests/` |
| `make pre-commit` | Run the configured pre-commit hooks manually |

The gate is non-negotiable: do not report work as complete until `make checkall` is green locally. If you add behavior, add a test under `tests/` so the gate covers it — the suite runs on every `checkall`.

Tooling configuration lives in [`ruff.toml`](ruff.toml) (formatter/linter, targeting `py312`) and [`pyrightconfig.json`](pyrightconfig.json) (`pythonVersion` 3.12).

## Adding a new utility that AI tools can call

PAR GPT uses a two-layer lazy-loading architecture and a `utils/` package of domain submodules bridged by `utils/utils_facade.py`. When you add a utility that the AI tools should reach via `par_gpt.utils`:

1. Implement it in the appropriate `src/par_gpt/utils/<domain>.py` submodule (group by domain — do not re-centralize into one file).
2. Export it from `src/par_gpt/utils/__init__.py` (add to `__all__` and, for heavy optional dependencies, expose it via the lazy `__getattr__` so import stays cheap).
3. Call it from the tool as `_utils.your_function_name()`.

## Conventions

### Code style

- Follow `ruff` formatting and lint rules (enforced by `make format` / `make lint`).
- Use type annotations on public functions and anything you substantially change.
- Prefer the shared `get_console()` (Rich) over ad-hoc `print()` for diagnostic output; reserve bare `print()` for genuine stdout/pipe output.
- Keep error returns recognizable: the AI-tool layer uses a consistent `"Error: {type(e).__name__}: {e}"` convention so the agent can distinguish success from failure.

### Docstrings

- **Google-style** docstrings on all public functions, classes, and modules.
- AI tools (`src/par_gpt/ai_tools/ai_tools.py`) are decorated with `@tool(parse_docstring=True)`, so the docstring IS the tool's description shown to the model — keep them accurate and complete; docs and code cannot be allowed to diverge.

### Commits

This project uses **Conventional Commits** (visible in `git log`). Prefix commits with a type and optional scope:

```
feat(agent): add <thing>
fix(security): <what was fixed>
refactor(quality): <what changed>
docs(architecture): <what was updated>
chore: <housekeeping>
```

Keep commits atomic and focused; one logical change per commit.

## Pull request workflow

1. Fork the repo and create a feature branch from `main`.
2. Make your change, following the conventions above.
3. Add or update tests under `tests/` for any behavioral change.
4. Run `make checkall` and resolve every error and warning you introduced.
5. Update `CHANGELOG.md` under `[Unreleased]` if your change is user-visible.
6. Open a pull request with a clear description of what changed and why.

## Reporting issues

When filing an issue, include the PAR GPT version (`par_gpt --version`), your Python version, the provider/model in use, and the smallest reproduction you can manage. Security-related reports should be private — do not open a public issue for an active vulnerability.
