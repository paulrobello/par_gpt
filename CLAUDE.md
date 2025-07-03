# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PAR GPT is a flexible command-line interface for interacting with multiple AI language models. It operates in two modes: basic LLM mode and Agent mode with dynamic tool loading. Built with Python 3.11+ using UV package manager, Typer for CLI, and Rich for terminal output.

## Development Commands

### Setup and Environment
```bash
make setup          # First-time setup with UV
make resetup        # Recreate virtual environment from scratch
make depsupdate     # Update all dependencies
```

### Code Quality (Run Before Commits)
```bash
make checkall       # Format, lint, and typecheck - REQUIRED before commits
make format         # Format code with ruff
make lint           # Lint code with ruff
make typecheck      # Type check with pyright
make pre-commit     # Run pre-commit hooks manually
```

### Development Utilities
```bash
make sandbox        # Start Docker code sandbox container
make clean          # Clean build directories
make package        # Build the package
```

## Architecture and Key Components

### Core Application Structure
- **Entry Point**: `src/par_gpt/__main__.py` - Main Typer CLI application
- **Agent System**: `src/par_gpt/agents.py` - AI agent implementations with dynamic tool loading
- **Tool System**: `src/par_gpt/ai_tools/` - Keyword-activated tools for agent mode
- **Provider Layer**: Uses `par-ai-core` for multi-provider AI model abstraction

### Agent Mode Tool Loading
Tools are dynamically loaded based on keywords in user requests:
- **Always Available**: Memory, URL fetching, image display, user prompting
- **Keyword-Activated**: YouTube, Git, Reddit, clipboard, weather, GitHub, DALL-E, screen capture
- **Special Modes**: REPL (host execution with confirmation), Sandbox (Docker container)

### Security Architecture
- **Docker Sandbox**: `src/sandbox/docker/` - Isolated Python 3.12 environment for code execution
- **REPL Protection**: Confirmation prompts before executing code on host system
- **Environment Isolation**: API keys in `~/.par_gpt.env`, validation for all providers
- **Path Security**: Comprehensive path traversal protection via `src/par_gpt/utils/path_security.py`
- **File Validation**: All file operations validated to prevent directory traversal attacks
- **Input Sanitization**: User-provided paths and filenames sanitized across all modules
- **Optional Redis**: Memory functionality disabled by default, requires explicit enablement

### Code Standards Configuration
- **Line Length**: 120 characters (enforced by ruff)
- **Type Checking**: Pyright basic mode, Python 3.12 target
- **Docstrings**: Google-style required for all public APIs
- **Import Organization**: Grouped and sorted automatically

## Common Development Patterns

### Adding New AI Tools
1. Create tool class in `src/par_gpt/ai_tools/ai_tools.py`
2. Add keyword mapping in agent's tool loading logic
3. Include appropriate security measures for external API calls
4. Add environment variable configuration if needed

#### Screen Capture Tools Implementation
The screen capture functionality demonstrates a complete tool implementation pattern:

**Core Utilities (`src/par_gpt/utils.py`)**:
- `AvailableScreen` - Pydantic model for screen information
- `list_available_screens()` - Cross-platform screen detection (macOS with Quartz, fallback for others)
- `capture_screen_image()` - Screen capture with security warnings and multiple output formats

**AI Tool Wrappers (`src/par_gpt/ai_tools/ai_tools.py`)**:
- `ai_list_available_screens()` - Tool for listing available displays
- `ai_capture_screen_image()` - Tool for capturing screen with auto-detection and LLM description
- Circular import handling using `importlib.util.spec_from_file_location`

**Tool Registration (`src/par_gpt/__main__.py`)**:
- Import tools in main module
- Add keyword-based loading in `build_ai_tool_list()` function
- Keywords: "screen", "display", "capture", "screenshot"

**Key Implementation Features**:
- Multi-monitor support with primary display detection
- Automatic display selection when no screen_id specified
- Integration with existing security warning system
- Reuses shared image processing and description utilities
- Comprehensive error handling and fallback mechanisms

### Working with New Utility Modules
- **Audio Operations**: Use `AudioResourceManager` or convenience functions `safe_tts()`, `safe_voice_input()`
  ```python
  from par_gpt.utils import safe_tts, TTSProvider
  
  with safe_tts(TTSProvider.LOCAL) as tts:
      tts.speak("Hello world")
  # Resources automatically cleaned up
  ```
- **LLM Operations**: Use `LLMInvoker` for standardized model interactions
  ```python
  from par_gpt.utils import LLMInvoker, LlmConfig
  
  invoker = LLMInvoker(config)
  response = invoker.get_text_response([("user", "Hello")])
  ```
- **Configuration**: Use `EnvironmentConfig` for centralized environment management
  ```python
  from par_gpt.utils import EnvironmentConfig
  
  config = EnvironmentConfig()
  api_key = config.openai_api_key.get_secret_value() if config.openai_api_key else None
  ```
- **Path Security**: Use path validation functions to prevent directory traversal attacks
  ```python
  from par_gpt.utils.path_security import validate_within_base, sanitize_filename
  
  # Validate user-provided paths stay within allowed directory
  safe_path = validate_within_base(user_path, allowed_base_dir)
  
  # Sanitize filenames to remove dangerous characters
  safe_filename = sanitize_filename(user_filename)
  ```
- **Timing and Performance**: Use timing utilities for performance monitoring
  ```python
  from par_gpt.utils.timing import timer, timed, enable_timing
  
  # Context manager for timing operations
  with timer("database_query", {"table": "users"}):
      result = expensive_operation()
  
  # Decorator for timing functions
  @timed("expensive_calculation")
  def my_function():
      # Your code here
      pass
  
  # Enable timing globally (usually done via CLI options)
  enable_timing()
  ```

### Provider Integration
- All providers use `par-ai-core` abstraction layer
- Configuration managed through environment variables in `~/.par_gpt.env`
- Model selection handled automatically based on provider capabilities

### Memory and Caching
- **Cache Manager**: `src/par_gpt/cache_manager.py` handles response caching
- **Memory Utils**: `src/par_gpt/memory_utils.py` for Redis-based agent memory
- **Audio Resource Management**: `src/par_gpt/utils/audio_manager.py` prevents memory leaks
- **Persistence**: Agent conversations and context maintained across sessions

### Performance Monitoring and Timing
- **Timing Utilities**: `src/par_gpt/utils/timing.py` provides comprehensive performance monitoring
- **TimingRegistry**: Singleton class for collecting and managing timing data
- **Context Managers**: `timer()` for easy operation timing with nested support
- **CLI Integration**: `--show-times` and `--show-times-detailed` options
- **Instrumented Operations**: Startup, LLM calls, tool loading, agent execution
- **Rich Output**: Tables and trees with grand totals, averages, and metadata

### Comprehensive Lazy Loading System (v0.12.2+)
PAR GPT implements a complete lazy loading system that reduces startup time by 25-50%:

#### **Lazy Import Architecture:**
- **`lazy_import_manager.py`** - Command-specific import routing with caching system and comprehensive import categories
- **`lazy_utils_loader.py`** - Utils module lazy loading with dynamic `__getattr__` pattern
- **Deferred initialization** - Global state (clipboard, warnings) loaded only when needed
- **Function-level imports** - Heavy modules loaded at usage points
- **Comprehensive Coverage** - All heavy dependencies now lazy loaded

#### **Complete Lazy Loading Coverage:**
**AI Tools Module** (`ai_tools.py`):
- GitHub API imports (Auth, Github, AuthenticatedUser)
- Clipboard operations (clipman)
- Rich UI components (Panel, Text, Prompt)
- Feed processing (feedparser)

**TTS Manager** (`tts_manager.py`):
- All TTS provider imports (ElevenLabs, OpenAI, Kokoro, pyttsx3)
- Audio processing (numpy)
- Audio playback (elevenlabs.play)

**Voice Input Manager** (`voice_input_manager.py`):
- Real-time speech recognition (RealtimeSTT)
- Type annotations updated for lazy-loaded types

**Utils Module** (`utils.py`):
- HTTP requests library (requests) - lazy loaded in weather functions
- GitHub API operations - complete lazy loading pattern
- All other heavy imports already properly lazy loaded

**Main Application** (`__main__.py`):
- Helper functions for cross-function lazy imports
- Fixed scoping issues with path security functions
- Proper import organization and error handling

#### **Extended LazyImportManager Categories:**
- `load_tts_imports()` - TTS provider dependencies
- `load_voice_input_imports()` - Voice input functionality
- `load_github_imports()` - GitHub API operations
- `load_feed_imports()` - RSS/feed processing
- `load_rich_imports()` - Rich UI components
- `load_clipboard_imports()` - Clipboard operations

#### **Command Classification System:**
```python
# Minimal commands: --version, --help, show-env (~1.45s)
# Basic LLM: llm command (optimized startup)
# Heavy operations: agent, git, sandbox (lazy loaded)
```

#### **Optimization Techniques:**
- **Environment loading** moved after command determination
- **Provider utilities** loaded lazily per command requirements  
- **Rich components** (Panel, Pretty, Prompt) loaded on demand
- **LLM configuration** lazy loaded with timing integration
- **Utils modules** accessed via `__getattr__` dynamic loading
- **Cross-function imports** handled via helper functions to prevent scoping issues

#### **Performance Results:**
- `--version` command: ~1.45s (minimal imports)
- `show-env` command: ~1.5s (optimized startup)
- `llm` command: Significant startup improvement with lazy provider loading
- `agent` command: Heavy dependencies loaded only when tools are activated
- **Overall startup time reduction: 25-50% comprehensive improvement**

#### **Implementation Patterns:**
```python
# Function-level lazy import pattern
def my_function():
    heavy_module = lazy_import('heavy.module', 'SpecificClass')
    return heavy_module.do_something()

# Cross-function helper pattern (for __main__.py)
def get_clipboard():
    return lazy_import("clipman")

# Usage in functions
def some_function():
    clipboard = get_clipboard()
    clipboard.copy(content)

# LazyImportManager extension pattern
def load_my_imports(self) -> dict[str, Any]:
    imports = {}
    imports['MyTool'] = self.get_cached_import('my_module', 'MyTool')
    return imports
```

### Audio Memory Leak Prevention
See `examples/audio_memory_example.py` for comprehensive examples of:
- Safe voice input with automatic cleanup
- TTS operations with memory management
- Background resource cleanup threads
- Proper weakref finalizer usage
- Manual cleanup patterns (not recommended)

### Path Security Protection
See `examples/path_security_example.py` for comprehensive examples of:
- Basic path validation and traversal prevention
- Filename sanitization for dangerous characters
- Base directory validation to prevent escapes
- Secure path joining operations
- File operation protection patterns

## Security Development Guidelines

### File Operations Security
**ALWAYS** use path validation for any user-provided file paths:
```python
# ✅ CORRECT - Validate paths before use
from par_gpt.utils.path_security import validate_within_base, PathSecurityError

try:
    safe_path = validate_within_base(user_path, base_directory)
    with open(safe_path, 'r') as f:
        content = f.read()
except PathSecurityError as e:
    logger.error(f"Path security violation: {e}")
    return error_response()

# ❌ WRONG - Direct path use without validation
with open(user_path, 'r') as f:  # Vulnerable to path traversal!
    content = f.read()
```

### Filename Sanitization
**ALWAYS** sanitize user-provided filenames:
```python
# ✅ CORRECT - Sanitize before use
from par_gpt.utils.path_security import sanitize_filename

safe_name = sanitize_filename(user_filename)
output_path = os.path.join(output_dir, safe_name)

# ❌ WRONG - Direct filename use
output_path = os.path.join(output_dir, user_filename)  # Vulnerable!
```

### Import Fallbacks
All modules must include fallback implementations for security functions:
```python
try:
    from par_gpt.utils.path_security import PathSecurityError, validate_relative_path
except ImportError:
    # Fallback implementation
    from pathlib import Path
    
    class PathSecurityError(Exception):
        pass
    
    def validate_relative_path(path: str, max_depth: int = 10) -> Path:
        if "../" in path or "..\\" in path:
            raise PathSecurityError("Path traversal detected")
        return Path(path)
```

### Security Testing
- Test with dangerous path patterns: `../../../etc/passwd`, `..\\windows\\system32`
- Validate filename sanitization with special characters: `<>:"|?*`
- Verify base directory enforcement with various escape attempts
- Check cross-platform compatibility (Windows and Unix paths)

### Security Warnings and Automation

PAR GPT includes a comprehensive security warning system with automation controls for development and production use:

#### **Security Warning Functions** (`src/par_gpt/utils/security_warnings.py`):
- **`warn_code_execution()`** - For arbitrary code execution (REPL, scripts)
- **`warn_command_execution()`** - For system command execution (screen capture, file operations)
- **`warn_environment_modification()`** - For environment variable changes

#### **Tool Context System** (`src/par_gpt/tool_context.py`):
Global state management for AI tools to access runtime configuration:
```python
from par_gpt.tool_context import set_tool_context, is_yes_to_all_enabled

# In agent execution (done automatically)
set_tool_context(yes_to_all=state["yes_to_all"])

# In AI tools
skip_confirmation = is_yes_to_all_enabled()
result = capture_screen_image(skip_confirmation=skip_confirmation)
```

#### **Using Security Warnings in New Tools**:
```python
from par_gpt.utils.security_warnings import warn_command_execution

def my_dangerous_operation(command: str, skip_confirmation: bool = False):
    if not warn_command_execution(
        command=command,
        operation_description="Execute dangerous operation",
        skip_confirmation=skip_confirmation
    ):
        raise ValueError("Operation cancelled by user")
    
    # Proceed with operation
    return execute_command(command)
```

#### **Best Practices**:
- **Always use security warnings** for operations that execute code, commands, or modify system state
- **Respect `skip_confirmation` parameter** in all security-sensitive functions
- **Test both interactive and automated modes** (`--yes-to-all` flag)
- **Use tool context** for AI tools that need access to runtime state

## Performance Development Guidelines

### Lazy Loading Patterns
PAR GPT implements comprehensive lazy loading across all modules. When adding new functionality, follow these established patterns:

#### **Function-Level Lazy Imports (Primary Pattern):**
```python
def my_function():
    # Lazy load heavy modules when function is called
    heavy_module = lazy_import('heavy.module', 'SpecificClass')
    return heavy_module.do_something()
```

#### **Cross-Function Helper Pattern (For Main Application):**
```python
# Define helper functions at module level for shared imports
def get_my_heavy_import():
    return lazy_import("my_heavy_module", "MyClass")

def function_a():
    heavy_class = get_my_heavy_import()
    return heavy_class.method_a()

def function_b():
    heavy_class = get_my_heavy_import()
    return heavy_class.method_b()
```

#### **Command-Specific Loading (LazyImportManager):**
```python
# Add new commands to lazy_import_manager.py
def load_my_command_imports(self) -> dict[str, Any]:
    imports = {}
    imports['my_tool'] = self.get_cached_import('my_module', 'MyTool')
    return imports

# Update get_command_imports() function
elif command == 'my_command':
    return _lazy_import_manager.load_my_command_imports()
```

#### **Utils Module Lazy Loading:**
```python
# Add to utils/__init__.py __getattr__ function
'MyUtility': lambda: lazy_utils_import('my_utils', 'MyUtility'),

# Add to lazy_utils_loader.py
def get_my_utils(self) -> dict[str, Any]:
    return {
        'MyUtility': self.get_utils_item('my_utils', 'MyUtility'),
    }
```

#### **Type Annotation Handling for Lazy Imports:**
```python
# When types are lazy loaded, use Any with explanatory comments
from typing import Any

class MyManager:
    def __init__(self):
        # Type annotation updated to use Any since HeavyClass is lazy loaded
        self.heavy_instance: Any | None = None
    
    def init_heavy(self):
        HeavyClass = lazy_import("heavy_module", "HeavyClass")
        self.heavy_instance = HeavyClass()
```

#### **Scoping and Error Prevention:**
```python
# ✅ CORRECT - Lazy imports outside try-except blocks when used across multiple scopes
def image_generation_function():
    # Load security functions at function start, outside try-except blocks
    sanitize_filename = lazy_import("security", "sanitize_filename")
    validate_path = lazy_import("security", "validate_path")
    
    if user_provided_path:
        try:
            safe_path = sanitize_filename(user_provided_path)
        except SecurityError:
            handle_error()
    
    # validate_path is available here because it was loaded outside the try block
    final_path = validate_path(computed_path)

# ❌ WRONG - Lazy imports inside try blocks when used outside
def bad_function():
    if user_provided_path:
        try:
            validate_path = lazy_import("security", "validate_path")  # Only loaded if try executes
            safe_path = sanitize_filename(user_provided_path)
        except SecurityError:
            handle_error()
    
    # ERROR: validate_path may not be defined if try block didn't execute
    final_path = validate_path(computed_path)
```

#### **Conditional Imports:**
```python
# Only import when specific conditions are met
if context_is_image:
    image_utils = lazy_import('image_processing', 'ImageUtils')
    result = image_utils.process(image)
```

#### **Established Conversion Examples:**
Reference these real implementations for best practices:
- **`ai_tools.py`**: GitHub API, clipboard, Rich components lazy loading
- **`tts_manager.py`**: Provider-specific imports with proper variable naming
- **`voice_input_manager.py`**: Type annotation patterns for lazy-loaded classes
- **`utils.py`**: Weather function requests lazy loading
- **`__main__.py`**: Cross-function helper pattern implementation

### Performance Testing
- Use `--show-times-detailed` to measure impact of changes
- Test minimal commands (`--version`) for baseline performance
- Verify no regressions in startup time for existing commands
- Profile with different command types (minimal, basic LLM, heavy)

## Testing and Deployment

### Quality Assurance
- Pre-commit hooks enforce formatting, linting, and type checking
- Run `make checkall` before every commit - this is mandatory
- Manual testing required for agent tools and CLI commands

### Package Management
- Use UV for all dependency operations: `uv add`, `uv remove`
- Lock file committed: `uv.lock` ensures reproducible builds
- Version managed in `src/par_gpt/__init__.py`

### Docker Sandbox Management
```bash
make sandbox                    # Start sandbox container
par_gpt sandbox -a start       # CLI command to start sandbox
par_gpt sandbox -a stop        # CLI command to stop sandbox
```

## Environment Configuration

### Required Environment Variables
- Provider API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- Optional: Redis connection for agent memory
- Optional: Voice/TTS service configurations

### CLI Modes
```bash
# Basic modes
par_gpt llm [prompt]                      # Basic LLM mode (no tools)
par_gpt agent [prompt]                    # Full agent with dynamic tools (Redis disabled by default)
par_gpt --enable-redis agent              # Agent with Redis memory functionality enabled

# Code execution modes
par_gpt --repl agent [prompt]             # Agent with host code execution (interactive)
par_gpt --code-sandbox agent              # Agent with Docker sandbox execution

# Automation modes (silent operation)
par_gpt --yes-to-all agent [prompt]       # Agent with automatic security confirmation acceptance
par_gpt --yes-to-all --repl agent         # Agent with host execution, no security prompts
par_gpt --yes-to-all agent "screenshot"   # Silent screen capture without warnings

# Combined automation examples
PARGPT_YES_TO_ALL=1 par_gpt agent "code"  # Environment variable for persistent automation
par_gpt --yes-to-all --debug agent        # Automated with debug output for troubleshooting
```

## Recent Improvements (v0.12.2+)

### Complete Lazy Loading Implementation (v0.12.2+)
- **Comprehensive Lazy Loading Conversion**: Completed system-wide lazy loading implementation
  - **AI Tools Module**: Converted GitHub API, clipboard, Rich components, feedparser
  - **TTS Manager**: Converted all TTS providers (ElevenLabs, OpenAI, Kokoro, pyttsx3), numpy, audio playback
  - **Voice Input Manager**: Converted RealtimeSTT with proper type annotation handling
  - **Utils Module**: Converted requests library and completed GitHub API lazy loading
  - **Main Application**: Fixed import scoping issues and added cross-function lazy import helpers
- **Extended LazyImportManager**: Added 6 new import categories for comprehensive coverage
  - TTS, voice input, GitHub, feed processing, Rich components, clipboard operations
- **Performance Impact**: Startup time reduction of 25-50% across all command types
- **Quality Assurance**: All modules pass lint checks, error handling preserved
- **Bug Fixes**: Resolved path security function scoping issues in image generation commands

### Global Security Automation System (v0.12.2)
- **Comprehensive `--yes-to-all` Flag**: Global automation for all security warnings and confirmation prompts
  - **Cross-tool support** - Works with REPL, screen capture, window capture, command execution
  - **Tool Context System** (`tool_context.py`) - Global state management for AI tools
  - **Silent operation** - Enables headless/scripted usage without interactive prompts
  - **Security conscious** - Maintains security by default, automation only when explicitly requested
- **Enhanced Security Warning Functions**: Complete silence mode when `skip_confirmation=True`
  - Updated `warn_command_execution()`, `warn_code_execution()`, `warn_environment_modification()`
  - Bypasses both warning display AND confirmation prompts in automation mode
- **AI Tool Integration**: Screen capture and window capture tools respect global automation state
- **Environment Variable Support**: `PARGPT_YES_TO_ALL=1` for persistent automation configuration

### Foundation Startup Performance Optimization (v0.12.2)
- **Initial Lazy Loading Framework**: Established the foundation for comprehensive lazy loading
  - **Command-specific import routing** with `lazy_import_manager.py`
  - **Utils module restructuring** with dynamic `__getattr__` lazy loading via `lazy_utils_loader.py`
  - **Deferred global initialization** for clipboard and warning configuration
  - **Function-level lazy imports** for LLM config, provider utilities, Rich components
- **Performance Architecture**: 
  - `lazy_import_manager.py` - Command-specific imports with caching
  - `lazy_utils_loader.py` - Dynamic utils loading with `__getattr__`
  - Modified `__init__.py` - Deferred global state initialization
  - Updated `utils/__init__.py` - Dynamic attribute access system
- **Command Classification**: Minimal (~1.45s), Basic LLM (optimized), Heavy (lazy loaded)

### Previous Performance Optimization (v0.12.1)
- **Lazy Loading System**: Implemented lazy loading for AI tools reducing startup time by ~10%
  - Heavy imports (PIL, Redis, GitHub APIs) now loaded only when needed
  - Conditional tool loading based on keywords and requirements
  - Module-level imports moved to function-level for better performance
- **Tool Loading Architecture**: `src/par_gpt/lazy_tool_loader.py` with caching and conditional loading
- **Import Optimization**: Deferred expensive imports until first use

### Redis Memory Control System
- **Optional Redis Integration**: Memory functionality disabled by default for cleaner startup
  - `--enable-redis` CLI flag and `PARGPT_ENABLE_REDIS` environment variable
  - Smart tool loading: `ai_memory_db` only available when Redis enabled
  - Graceful fallback when Redis unavailable, no connection errors
- **Global Redis Manager**: `src/par_gpt/utils/redis_manager.py` with enable/disable control
  - `set_redis_enabled()` and `is_redis_enabled()` functions
  - Disabled manager returns dummy operations to prevent connections

### Code Quality and Architecture Improvements
- **Fixed File Naming**: Corrected typos in filenames (`cache_manger` → `cache_manager`, etc.)
- **Memory Leak Prevention**: Comprehensive audio resource management with automatic cleanup
- **Utility Module Restructuring**: Created new utility classes to reduce code duplication by 15-20%
- **Type Safety**: Fixed major type annotation issues throughout the codebase
- **Configuration Management**: Centralized environment configuration with Pydantic and SecretStr

### New Utility Modules (`src/par_gpt/utils/`)
- **`AudioResourceManager`**: Comprehensive audio resource management with background cleanup
- **`LLMInvoker`**: Standardized LLM interactions across the application
- **`ConsoleManager`**: Centralized console handling patterns
- **`RedisOperationManager`**: Consistent Redis operations with error handling
- **`EnvironmentConfig`**: Secure configuration management with Pydantic validation
- **`ImageProcessor`**: Unified image handling and processing logic

### Security Enhancements
- **Path Traversal Protection**: Comprehensive path validation to prevent directory traversal attacks
- **SecretStr Implementation**: All API keys now use Pydantic SecretStr for secure handling
- **Dependency Updates**: Updated security-critical packages (cryptography, etc.)
- **Memory Safety**: Fixed audio processing memory leaks with proper resource management
- **File Security**: All file operations now validate paths to prevent unauthorized access

## Key Technical Considerations

### Tool Activation System
- Tools load dynamically based on keyword detection in user prompts
- Each tool class implements security validation
- External API calls include timeout and error handling
- Resource-intensive tools (image generation, code execution) require explicit user confirmation

### Multi-Provider Support
- Automatic model selection based on provider capabilities
- Fallback mechanisms for provider failures
- Consistent interface across all supported AI providers
- Support for local (Ollama) and cloud-based models