# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PAR GPT is a flexible command-line interface for interacting with multiple AI language models. It operates in two modes: basic LLM mode and Agent mode with dynamic tool loading. Built with Python 3.12 or higher (3.13 recommended) using UV package manager, Typer for CLI, and Rich for terminal output.

## Development Commands

### Setup and Environment
```bash
make setup          # First-time setup with UV
make resetup        # Recreate virtual environment from scratch
make depsupdate     # Update all dependencies
```

### Code Quality (Run Before Commits)
```bash
make checkall       # Format, lint, typecheck, and run tests - REQUIRED before commits
make format         # Format code with ruff
make lint           # Lint code with ruff
make typecheck      # Type check with pyright
make test           # Run the pytest test suite (tests live in tests/)
make pre-commit     # Run pre-commit hooks manually
```

### Development Utilities
```bash
make sandbox        # Start Docker code sandbox container
make clean          # Clean build directories
make package        # Build the package
```

## Command Invocation Tips
- Instead of using `echo "prompt" | uv run par_gpt agent` use `uv run par_gpt "prompt"`

## Development Patterns

### Lazy Loading Architecture
PAR GPT uses a two-layer lazy loading system:

1. **Generic Layer** (`par_utils.LazyImportManager`):
   - Thread-safe import caching
   - Module and item-specific lazy loading
   - Used directly in AI tools for simple imports

2. **Application Layer** (`par_gpt.lazy_import_manager.PARGPTLazyImportManager`):
   - Extends the generic LazyImportManager
   - Provides command-specific loading methods:
     - `load_agent_imports()` - For agent mode
     - `load_basic_llm_imports()` - For LLM mode
     - `load_media_imports()` - For image/TTS operations
     - And many more specialized loaders
   - Used in CLI config and command infrastructure

Example usage:
```python
# For generic lazy loading (e.g., in AI tools)
from par_utils import LazyImportManager
manager = LazyImportManager()

# Import an entire module (module_path only)
requests_module = manager.get_cached_import("requests")

# Import a specific item (module_path + item_name)
JSONEncoder = manager.get_cached_import("json", "JSONEncoder")

# For PAR GPT-specific loading (e.g., in commands)
from par_gpt.lazy_import_manager import PARGPTLazyImportManager
manager = PARGPTLazyImportManager()
imports = manager.load_agent_imports()
```

### AI Tools Development
When working with AI tools in `src/par_gpt/ai_tools/ai_tools.py`:

#### Import Dependencies for AI Tools
- **Utils Facade Pattern**: Most AI tools use `_utils.function_name()` to call utility functions
- **Utils Package Integration**: The utils package (`src/par_gpt/utils/`) uses lazy loading with `__getattr__`
- **Original Utils Functions**: Functions from `src/par_gpt/utils.py` need explicit exposure in utils package

#### Adding New Utils Functions to AI Tools
If adding a new utility function that AI tools need to access:

1. **Add to utils package** `src/par_gpt/utils/__init__.py`:
   ```python
   # In utils_maps dictionary within __getattr__():
   "your_function_name": lambda: _import_from_original_utils("your_function_name"),
   ```

2. **Add to __all__ list**:
   ```python
   # In __all__ list:
   "your_function_name",
   ```

3. **Use in AI tools**:
   ```python
   @tool(parse_docstring=True)
   def ai_your_tool() -> str:
       return _utils.your_function_name()
   ```

#### AI Tools Notes
AI tools live in `src/par_gpt/ai_tools/ai_tools.py` and are loaded conditionally based on keywords in the user prompt (see the README "Agent mode" section). When a tool stops working after a refactor, the cause is almost always a broken utils facade import — verify the function is exposed in `src/par_gpt/utils/__init__.py` (both `utils_maps` and `__all__`). For version-specific fix history, see [CHANGELOG.md](CHANGELOG.md).

### Testing AI Tools
```bash
# Test specific AI tool functionality
uv run par_gpt agent "list available screens"
uv run par_gpt agent "create figlet text that says TEST"
uv run par_gpt agent "take a screenshot of my screen"
```

### Performance Timing Development

PAR GPT includes an advanced timing system for performance analysis that distinguishes between processing time and user interaction time.

#### Timing Categories

**Processing Operations** (Category: "processing"):
- LLM operations, tool loading, agent execution
- Default category for all `timer()` context managers
- Counted in "Processing Total" metric

**User Interaction Operations** (Category: "user_interaction"):
- User prompts, security confirmations, REPL confirmations
- Use `user_timer()` context manager or `timer(category="user_interaction")`
- Counted in "User Wait Time" metric

#### Adding Timing to Code

**For Processing Operations:**
```python
from par_utils import timer

# Standard processing timing
with timer("llm_invoke", {"model": model_name}):
    result = llm.invoke(messages)

# Explicit processing category
with timer("tool_loading", category="processing"):
    tools = load_tools()
```

**For User Interactions:**
```python
from par_utils import user_timer, timer

# User interaction timing (recommended)
with user_timer("user_prompt", {"prompt_type": "confirmation"}):
    response = Prompt.ask("Do you want to continue?")

# Alternative explicit syntax
with timer("security_confirmation", category="user_interaction"):
    response = Prompt.ask("Execute this code?")
```

#### Timing Integration Points

When adding new user interaction features, ensure timing is captured:

1. **Rich Prompt Usage**:
   ```python
   with user_timer("feature_confirmation"):
       response = Prompt.ask("Your question here")
   ```

2. **Security Warnings**:
   ```python
   with user_timer("security_warning", {"warning_type": "code_execution"}):
       confirmed = get_user_confirmation()
   ```

3. **Interactive Modes**:
   ```python
   with user_timer("interactive_input"):
       user_input = get_user_input()
   ```

#### Testing Timing Features

```bash
# Test timing display
uv run par_gpt --show-times llm "test prompt"
uv run par_gpt --show-times-detailed agent "complex task"

# Test timing categories with Python
uv run python -c "
from par_utils import enable_timing, timer, user_timer, show_timing_summary
import time

enable_timing()

with timer('processing_example'):
    time.sleep(0.1)

with user_timer('user_interaction_example'):
    time.sleep(0.05)

show_timing_summary()
"
```

This will show dual totals: "Grand Total (All)" and "Processing Total" (excluding user wait time).