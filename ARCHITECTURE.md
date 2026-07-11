# PAR GPT Architecture Documentation

This document provides a comprehensive overview of PAR GPT's architecture, design patterns, and module organization.

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Module Organization](#module-organization)
4. [Design Patterns](#design-patterns)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Performance Optimizations](#performance-optimizations)
8. [Extension Points](#extension-points)

## Overview

PAR GPT is a sophisticated command-line AI interface built with Python 3.12 or higher (3.13 recommended). The architecture follows modern software engineering principles including modularity, separation of concerns, lazy loading, and comprehensive security measures. The application is built around the **PAR Utils** package - a fully-integrated reusable utilities framework that provides core functionalities like performance monitoring, security validation, error handling, and caching systems.

### Key Architectural Principles

- **Modular Design**: Clear separation between CLI, commands, core logic, and external services
- **Security First**: Comprehensive path validation, code execution safety, and user confirmation systems
- **Performance Optimized**: Lazy loading system reducing startup time by 25-50%
- **Thread Safety**: Thread-safe context management for concurrent operations
- **Extensibility**: Plugin-style tool loading and command pattern for easy extension

## High-Level Architecture

```mermaid
graph TB
    subgraph "PAR GPT Architecture"
        subgraph CLI["CLI Layer"]
            A1[app.py]
            A2[options.py]
            A3[config.py]
            A4[context.py]
            A5[security.py]
        end
        
        subgraph CMD["Command Layer"]
            B1[base.py]
            B2[llm.py]
            B3[agent.py]
            B4[git.py]
            B5[...]
        end
        
        subgraph CORE["Core Logic Layer"]
            C1[agents.py]
            C2[utils/]
            C3[ai_tools/]
            C4[memory_utils.py]
            C5[...]
        end
        
        subgraph PROVIDER["Provider Layer"]
            subgraph AICORE["PAR AI Core Library"]
                D1[OpenAI Provider]
                D2[Anthropic Provider]
                D3[Ollama Provider]
                D4[...]
            end
        end
        
        subgraph EXT["External Services"]
            E1[Redis Memory]
            E2[Docker Sandbox]
            E3[GitHub API]
            E4[Weather API]
        end
        
        CLI --> CMD
        CMD --> CORE
        CORE --> PROVIDER
        CORE --> EXT
    end
```

## Module Organization

### Core Structure

```
src/par_gpt/
├── __main__.py                 # Entry point: Typer app + command registration
├── cli/                        # CLI Infrastructure Layer
│   ├── app.py                 # Main Typer app, state construction, option wiring
│   ├── options.py             # CLI option definitions
│   ├── config.py              # Configuration setup and global initialization
│   ├── context.py             # Context processing (files, URLs, stdin, images)
│   └── security.py            # Security validation and mutual-exclusivity checks
├── commands/                   # Command Pattern Implementation
│   ├── base.py                # BaseCommand + LLMCommandMixin / LoopableCommandMixin / ChatHistoryMixin
│   ├── llm.py                 # LLM command
│   ├── agent.py               # Agent command
│   ├── git.py                 # Git operations
│   └── ...                    # code-review, sandbox, stardew, generate-prompt, etc.
├── ai_tools/                  # AI Tools (Plugin System)
│   ├── ai_tools.py            # Tool implementations (each small, @tool(parse_docstring=True))
│   └── par_python_repl.py     # Host & sandboxed REPL tools
├── utils/                     # Domain submodule package (post-ARC-001; the utils.py monolith is deleted)
│   ├── __init__.py            # Re-exports the public surface from submodules + par_utils
│   ├── _singletons.py         # Process-wide shared singletons (cache_manager), constructed exactly once
│   ├── utils_facade.py        # Backward-compat facade bridging ai_tools -> utils / par_utils
│   ├── weather.py             # Weather lookup
│   ├── figlet_utils.py        # ASCII art (figlet)
│   ├── terminal_image.py      # Terminal image rendering (sixel / pixel blocks)
│   ├── env_context.py         # Environment / system context gathering
│   ├── screen_capture.py      # macOS window / screen enumeration and capture
│   ├── image_description.py   # LLM-based image description
│   ├── media_generation.py    # DALL-E image generation, TTS (speak)
│   ├── pyproject_deps.py      # pyproject dependency updating
│   ├── github_utils.py        # GitHub repo publishing
│   ├── redis_client.py        # Redis client construction
│   ├── audio_manager.py       # Audio playback and cleanup
│   ├── image_processor.py     # Image preprocessing
│   ├── redis_manager.py       # Redis-backed memory management
│   ├── config.py              # EnvironmentConfig model
│   ├── config_validation.py   # Pydantic-based configuration validation
│   ├── context_manager.py     # ThreadSafeContextManager (locked, per-thread contexts)
│   ├── llm_invoker.py         # Single LLM call helper
│   ├── path_security.py       # Path-security helpers (re-exports par_utils validators)
│   ├── security_warnings.py   # Security warning panels
│   └── error_helpers.py       # Backward-compat re-export of par_utils error handlers
├── memory_utils.py            # Redis-based persistent memory utilities
├── agents.py                  # Agent orchestration (tool agent, single LLM call)
├── lazy_import_manager.py     # PARGPTLazyImportManager (PAR GPT-specific loaders)
└── tool_context.py            # Global tool context (thread-safe backend)

src/par_utils/                  # PAR Utils Package
├── __init__.py                # Main exports
├── py.typed                   # Type declarations
├── performance/               # Performance Utilities
│   ├── timing.py              # Performance measurement
│   └── lazy_loading.py        # LazyImportManager (lazy import management)
├── security/                  # Security Utilities
│   └── path_validation.py     # Path security validation
├── errors/                    # Error Management (ErrorMessage / ErrorRegistry live here)
│   ├── registry.py            # Error message registry (ErrorMessage, register_error, ...)
│   └── handlers.py            # Error handling utilities (ErrorHandler)
├── caching/                   # Caching System
│   └── disk_cache.py          # Thread-safe disk cache
└── console/                   # Console Management
    └── manager.py             # Rich console utilities
```

> Note: line counts are intentionally omitted — they rot quickly. See `wc -l` for current sizes.

### Layer Responsibilities

#### CLI Layer (`cli/`)
- **Command Line Interface**: Typer app setup and argument parsing
- **Configuration Management**: Environment loading and validation
- **Context Processing**: File, URL, and image handling
- **Security Validation**: Mutual exclusivity checks and warnings

#### Command Layer (`commands/`)
- **Command Pattern**: Consistent command structure with mixins
- **Business Logic**: Implementation of specific commands
- **State Management**: Context passing and result handling
- **Error Handling**: Consistent error processing

#### Core Logic Layer
- **Agent Orchestration**: AI tool coordination and execution
- **Memory Management**: Redis-based persistent memory
- **Utility Functions**: Shared functionality across modules
- **Security Framework**: Path validation and execution safety

#### PAR Utils Package
- **Performance Optimization**: Timing measurement and lazy loading
- **Security Validation**: Path traversal protection and filename sanitization
- **Error Management**: Centralized error registry with structured messaging
- **Caching System**: Thread-safe disk caching with URL downloads
- **Console Management**: Rich-based terminal output management

## Design Patterns

### 1. Command Pattern

```mermaid
classDiagram
    class Client {
        +main()
    }
    
    class BaseCommand {
        +execute()
        +handle_output()
        +handle_exception()
    }
    
    class LLMCommand {
        +do_llm_call()
    }
    
    class AgentCommand {
        +run_agent()
        +load_tools()
    }
    
    class LLMCommandMixin {
        +build_model()
        +setup_provider()
    }
    
    class LoopableCommandMixin {
        +handle_loop()
        +process_input()
    }
    
    class ChatHistoryMixin {
        +load_history()
        +save_history()
    }
    
    Client --> BaseCommand : uses
    BaseCommand <|-- LLMCommand
    BaseCommand <|-- AgentCommand
    LLMCommand ..|> LLMCommandMixin : implements
    LLMCommand ..|> LoopableCommandMixin : implements
    AgentCommand ..|> LLMCommandMixin : implements
    AgentCommand ..|> ChatHistoryMixin : implements
```

### 2. Strategy Pattern (Providers)

```mermaid
classDiagram
    class LlmConfig {
        +provider: LlmProvider
        +model_name: str
        +temperature: float
        +build_chat_model()
    }
    
    class LlmProvider {
        <<interface>>
        +build_chat_model()
        +validate_config()
    }
    
    class OpenAIProvider {
        +create_model()
        +get_available_models()
    }
    
    class AnthropicProvider {
        +create_model()
        +get_available_models()
    }
    
    class OllamaProvider {
        +create_model()
        +get_available_models()
    }
    
    class GroqProvider {
        +create_model()
        +get_available_models()
    }
    
    LlmConfig --> LlmProvider : uses
    LlmProvider <|-- OpenAIProvider
    LlmProvider <|-- AnthropicProvider
    LlmProvider <|-- OllamaProvider
    LlmProvider <|-- GroqProvider
```

### 3. Facade Pattern (Utils Import)

```mermaid
classDiagram
    class AITools {
        +ai_capture_window()
        +ai_capture_screen()
        +ai_show_image()
        +ai_get_weather()
        +ai_figlet()
        +ai_github_publish_repo()
        +ai_image_gen_dali()
        +ai_list_windows()
        +ai_list_screens()
        +... 29 total tools
    }
    
    class UtilsFacade {
        +capture_window()
        +capture_screen()
        +show_image()
        +get_weather()
        +_get_utils_function()
        +_utils_cache: dict
    }
    
    class ParUtilsPackage {
        +timing utilities
        +lazy loading
        +path security
        +error management
        +caching system
        +console management
    }
    
    class ComplexUtils {
        +capture_window_image()
        +capture_screen_image()
        +show_image_in_terminal()
        +get_weather_current()
        +get_weather_forecast()
        +github_publish_repo()
        +describe_image_with_llm()
        +... 50+ functions
    }
    
    class LazyImportManager {
        +get_cached_import()
        +clear_cache()
    }
    
    class PARGPTLazyImportManager {
        +load_agent_imports()
        +load_basic_llm_imports()
        +... other loaders
    }
    
    AITools --> UtilsFacade : uses facade
    UtilsFacade --> ParUtilsPackage : imports from
    UtilsFacade --> ComplexUtils : delegates to
    UtilsFacade --> LazyImportManager : lazy loads via
    ParUtilsPackage --> LazyImportManager : contains
    PARGPTLazyImportManager --|> LazyImportManager : extends
    
    note for UtilsFacade "Resolves circular imports\nProvides clean interface\nCaches loaded functions\nFixed in v0.13.0: Added dynamic loading"
    note for ParUtilsPackage "Reusable utilities package\nModular architecture\nGeneralized for broader use"
    note for ComplexUtils "Large utils.py module\nWith complex dependencies\nPotential circular imports"
```

### 4. Singleton Pattern (Registries)

The process-wide registries use a `__new__`-based singleton so a single instance is
shared across threads:

```mermaid
classDiagram
    class TimingRegistry {
        -_instance: TimingRegistry
        -_timings: dict
        +__new__()
        +start_timing()
        +end_timing()
        +get_stats()
    }
    
    class ErrorRegistry {
        -_instance: ErrorRegistry
        -_errors: dict
        +__new__()
        +register()
        +get()
        +list_all()
    }
    
    class ContextManager {
        -_instance: ContextManager
        -_contexts: dict
        +__new__()
        +set_context()
        +get_context()
        +clear_context()
    }
    
    class Client1
    class Client2
    class ClientN
    
    Client1 --> TimingRegistry : uses
    Client2 --> TimingRegistry : uses
    ClientN --> TimingRegistry : uses
    
    Client1 --> ErrorRegistry : uses
    Client2 --> ContextManager : uses
    ClientN --> ContextManager : uses
    
    note for TimingRegistry "From par_utils package\nSingleton ensures single\ninstance across threads"
    note for ErrorRegistry "From par_utils package\nCentralized error message\nregistry with validation"
    note for ContextManager "From par_gpt.utils package\nLocked, per-thread contexts"
```

> `LazyImportManager` is intentionally **not** shown here. It is currently *not* a
> singleton: each module constructs its own instance with a private `_import_cache`
> (20+ `LazyImportManager()` constructions across the codebase), and `get_cached_import`
> holds no lock, so the cache is not coordinated across modules or safe under
> concurrent first-access. Consolidating to a single process-wide, thread-safe manager
> is tracked as **ARC-003** (Phase 3b, in progress); see *Lazy Loading Architecture*
> below.

### 5. Provider Dependency Boundary (`par_ai_core` / `par_utils`)

PAR GPT does not implement model providers itself. It depends on the `par_ai_core` library for
provider selection, configuration, and model construction, and on the bundled `par_utils` package
for cross-cutting utilities. The diagram below shows that boundary: `par_gpt` wires an
`LlmConfig` and invokes the model; `par_ai_core` owns the provider implementations and the
`build_chat_model()` step; concrete provider SDKs are pulled in by `par_ai_core`, not by
`par_gpt` directly.

```mermaid
flowchart TD
    subgraph par_gpt["par_gpt (this package)"]
        CLI["cli/app.py<br/>options + LlmConfig wiring"]
        Commands["commands/<br/>build model per request"]
        Agents["agents.py<br/>do_single_llm_call"]
    end

    subgraph par_ai_core["par_ai_core (provider library)"]
        LlmConfig["LlmConfig<br/>provider, model_name, temperature"]
        LlmProvider["LlmProvider enum"]
        Providers["Provider impls<br/>OpenAI / Anthropic / Ollama / Groq / ..."]
        Build["build_chat_model()<br/>returns BaseChatModel"]
    end

    subgraph par_utils["par_utils (bundled utilities)"]
        Utils["timing / lazy_loading<br/>security / errors<br/>caching / console"]
    end

    subgraph SDKs["Provider SDKs (external)"]
        Sdks["langchain-openai<br/>langchain-anthropic<br/>langchain-groq / ollama"]
    end

    CLI -->|"creates LlmConfig"| LlmConfig
    Commands -->|"uses"| LlmConfig
    Agents -->|"invokes model"| Build
    LlmConfig -->|"selects"| LlmProvider
    LlmProvider --> Providers
    Providers --> Build
    Build -->|"BaseChatModel"| Agents
    Providers -->|"wraps"| Sdks

    par_gpt -.->|"imports"| par_utils
    par_ai_core -.->|"imports"| par_utils

    style CLI fill:#ef6c00
    style Commands fill:#ef6c00
    style Agents fill:#ef6c00
    style LlmConfig fill:#c62828
    style LlmProvider fill:#c62828
    style Providers fill:#c62828
    style Build fill:#1b5e20
    style Utils fill:#2e7d32
    style Sdks fill:#6a1b9a
```

Key points:

- `par_gpt` never imports a provider SDK directly; it goes through `LlmConfig.build_chat_model()`.
- Provider routing (`LlmProvider` enum, base URLs, reasoning-model detection) is owned by `par_ai_core`.
- `par_utils` is a dependency of both packages and supplies timing, lazy loading, path security, error handling, caching, and console management.

## Data Flow

### 1. Basic LLM Mode Flow

```mermaid
flowchart LR
    A[User Input] --> B[CLI Parser]
    B --> C[LLM Command]
    C --> D[Provider]
    D --> E[Response]
    E --> F[Output]
    
    A -.-> G[args]
    B -.-> H[config]
    C -.-> I[context]
    D -.-> J[prompt]
    E -.-> K[text]
    
    style A fill:#1565c0
    style B fill:#6a1b9a
    style C fill:#ef6c00
    style D fill:#d32f2f
    style E fill:#00695c
    style F fill:#1b5e20
```

### 2. Agent Mode Flow

```mermaid
flowchart TB
    A[User Input] --> B[CLI Parser]
    B --> C[Agent Command]
    C --> D[Tool Loader]
    D --> E[AI Tools]
    C --> F[Agent Executor]
    F --> G[LLM Provider]
    G --> H[Response]
    E --> I[Tool Results]
    H --> J[Final Output]
    I --> J
    F --> J
    
    subgraph "Agent Processing"
        F
        G
        H
    end
    
    subgraph "Tool System"
        D
        E
        I
    end
    
    style A fill:#0277bd
    style J fill:#2e7d32
    style F fill:#ef6c00
    style G fill:#c62828
```

### 3. Security Validation Flow

```mermaid
flowchart TD
    A[User Operation] --> B{Security Check}
    B -->|Path Valid?<br/>File Safe?<br/>Code Safe?| C{Validation}
    C -->|No| D[Reject and Error]
    C -->|Yes| E{Security Warning}
    E -->|Show Risk<br/>Get Consent| F{User Choice}
    F -->|No| G[Cancel Operation]
    F -->|Yes / --yes-to-all| H[Execute Operation]
    
    style A fill:#1565c0
    style D fill:#b71c1c
    style G fill:#e65100
    style H fill:#1b5e20
    style B fill:#6a1b9a
    style E fill:#f9a825
```

## Security Architecture

### 1. Multi-Layer Security

```mermaid
flowchart TD
    A[User Input] --> B[Layer 1: Input Validation]
    B --> C[Layer 2: User Confirmation] 
    C --> D[Layer 3: Execution Isolation]
    D --> E[Safe Execution]
    
    subgraph Layer1 ["🛡️ Layer 1: Input Validation (PAR Utils)"]
        B1[Path traversal detection]
        B2[Filename sanitization]
        B3[Size limits]
        B4[Content type validation]
    end
    
    subgraph Layer2 ["⚠️ Layer 2: User Confirmation"]
        C1[Security warnings]
        C2[Operation descriptions]
        C3[Risk explanations]
        C4[Consent prompts]
    end
    
    subgraph Layer3 ["🔒 Layer 3: Execution Isolation"]
        D1[Docker sandbox for code]
        D2[Process isolation]
        D3[Resource limits]
        D4[Network restrictions]
    end
    
    B --> Layer1
    C --> Layer2
    D --> Layer3
    
    style A fill:#1565c0
    style E fill:#1b5e20
    style Layer1 fill:#ef6c00
    style Layer2 fill:#f9a825
    style Layer3 fill:#6a1b9a
```

### 2. Path Security Implementation (PAR Utils)

```mermaid
flowchart TD
    A[User Path Input] --> B[Normalize Path]
    B --> C[Validate Pattern]
    C --> D[Check Characters]
    D --> E[Validate Length]
    E --> F[Resolve and Check]
    F --> G[✅ Safe Path]
    
    B1["Remove ..\ and ../ patterns"]
    C1["Check against traversal regex"]
    D1["Scan for dangerous characters"]
    E1["Ensure reasonable path length"]
    F1["Ensure stays within base directory"]
    
    B -.-> B1
    C -.-> C1
    D -.-> D1
    E -.-> E1
    F -.-> F1
    
    subgraph ParUtils ["PAR Utils Security Module"]
        H[SecurePathValidator]
        I[validate_within_base]
        J[sanitize_filename]
        K[PathSecurityError]
    end
    
    G --> ParUtils
    
    style A fill:#1565c0
    style G fill:#1b5e20
    style B fill:#ef6c00
    style C fill:#f9a825
    style D fill:#6a1b9a
    style E fill:#00838f
    style F fill:#c62828
    style ParUtils fill:#2e7d32
```

## Performance Optimizations

### 1. Lazy Loading System (PAR Utils)

```mermaid
flowchart TD
    A[Startup Request] --> B[Command Detection]
    B --> C{Import Strategy}
    C -->|--version| D[Minimal: Core only]
    C -->|llm| E[Basic LLM: LLM + providers]
    C -->|agent| F[Full Agent: All tools when needed]
    
    D --> G[Module Cache]
    E --> G
    F --> G
    
    G --> H[Persistent Module Cache]
    H --> I[⚡ 25-50% startup time reduction]
    
    subgraph "Import Management"
        C
        D
        E
        F
        M[LazyImportManager - Generic]
        N[PARGPTLazyImportManager - Specific]
    end
    
    subgraph "Performance Benefits"
        I
        J[Faster command execution]
        K[Reduced memory footprint]
        L[Better user experience]
    end
    
    I --> J
    I --> K  
    I --> L
    
    G --> M
    N --> M
    
    style A fill:#1565c0
    style I fill:#1b5e20
    style G fill:#ef6c00
    style H fill:#6a1b9a
```

### 2. Command Classification

```mermaid
graph LR
    subgraph "Command Performance Comparison"
        A[Minimal Commands<br/>--version, --help<br/>⏱️ ~1.45s]
        B[Basic LLM Commands<br/>llm command<br/>⏱️ ~2.5s]
        C[Full Agent Commands<br/>agent command<br/>⏱️ ~3.5s]
    end
    
    subgraph "Modules Loaded"
        A1[Core only<br/>• __main__.py<br/>• Basic CLI]
        B1[Core + LLM<br/>• Provider libraries<br/>• Configuration<br/>• Security modules]
        C1[All modules on-demand<br/>• Tools loaded by keyword<br/>• Heavy deps when used]
    end
    
    A --> A1
    B --> B1
    C --> C1
    
    style A fill:#2e7d32
    style B fill:#f9a825
    style C fill:#c62828
    style A1 fill:#1b5e20
    style B1 fill:#f57f17
    style C1 fill:#ff6f00
```

### 3. Advanced Timing System (PAR Utils)

```mermaid
flowchart TD
    A[User Action] --> B{Action Type}
    
    B -->|Processing| C[Processing Timer]
    B -->|User Input| D[User Interaction Timer]
    
    C --> E[Category: processing]
    D --> F[Category: user_interaction]
    
    E --> G[TimingRegistry]
    F --> G
    
    G --> H[Dual Totals Calculation]
    
    H --> I[Grand Total All]
    H --> J[Processing Total]
    H --> K[User Wait Time]
    
    subgraph "Processing Operations"
        C1[LLM Invoke]
        C2[Tool Loading]
        C3[Agent Execution]
        C4[Context Processing]
    end
    
    subgraph "User Interaction Operations"
        D1[Interactive Prompts]
        D2[Security Confirmations]
        D3[REPL Confirmations]
        D4[AI Tool Prompts]
    end
    
    C --> C1
    C --> C2
    C --> C3
    C --> C4
    
    D --> D1
    D --> D2
    D --> D3
    D --> D4
    
    style I fill:#1565c0
    style J fill:#2e7d32
    style K fill:#f9a825
    style C fill:#1b5e20
    style D fill:#ff6f00
```

**Key Benefits:**
- **Accurate Performance Metrics**: Pure processing time without user delay skew
- **User Experience Analytics**: Track actual user response times
- **Bottleneck Identification**: Distinguish processing vs user interaction delays
- **Automation Planning**: Estimate true processing time for automated workflows

## Lazy Loading Architecture

PAR GPT uses a two-layer lazy loading system:

### Generic Layer (PAR Utils)
The base `LazyImportManager` from PAR Utils provides:
- Module and item-specific lazy loading (per-instance `_import_cache`)
- Cache management and statistics

> Current-state caveat: `LazyImportManager` is **not** a process-wide singleton and
> `get_cached_import` holds **no lock**. Each module constructs its own instance
> (20+ `LazyImportManager()` constructions across the codebase, plus 16 copy-pasted
> local `def lazy_import(...)` wrappers), so caches are not shared across modules and
> the claim of "thread-safe import caching" does not hold today. Consolidating to a
> single shared, thread-safe manager is tracked as **ARC-003** (Phase 3b, in progress);
> this section will be refreshed once that refactor lands.

### Application Layer (PAR GPT)
The `PARGPTLazyImportManager` extends the base class with:
- Command-specific import loading (`load_agent_imports`, `load_basic_llm_imports`, etc.)
- Integration with PAR GPT's command structure
- Provider and tool-specific loading strategies

### Usage Pattern

```python
# For PAR GPT-specific functionality
from par_gpt.lazy_import_manager import PARGPTLazyImportManager

manager = PARGPTLazyImportManager()
agent_imports = manager.load_agent_imports()

# For generic lazy loading (e.g., in AI tools)
from par_utils import LazyImportManager

generic_manager = LazyImportManager()
module = generic_manager.get_cached_import("some_module")
```

## Extension Points

### 1. Adding New Commands

```python
# 1. Create command class
class MyCommand(BaseCommand, LLMCommandMixin):
    def execute(self, ctx: typer.Context, my_option: bool) -> None:
        state = ctx.obj
        # Implementation here

# 2. Create factory function
def create_my_command():
    def my_command(ctx: typer.Context, my_option: bool = False) -> None:
        command = MyCommand()
        command.execute(ctx, my_option)
    return my_command

# 3. Register in __main__.py
app.command()(create_my_command())
```

### 2. Adding New AI Tools

```python
# 1. Create tool function
@tool(parse_docstring=True)
def my_new_tool(param: str) -> str:
    """Tool description.
    
    Args:
        param: Parameter description.
        
    Returns:
        Result description.
    """
    return "Tool result"

# 2. Register the tool in lazy_tool_loader.py
# Tools are added inside LazyToolLoader.get_conditional_tools(), where selection is
# gated on the question text (current behavior tracked under ARC-006). The public
# entry point is build_ai_tool_list:
def build_ai_tool_list(
    question: str,
    *,
    repl: bool = False,
    code_sandbox: bool = False,
    yes_to_all: bool = False,
    enable_redis: bool = False,
) -> tuple[list[BaseTool], dict[str, Any]]:
    ...
    # Returns (all_tools, local_modules); local_modules holds any REPL namespaces
    # the caller is responsible for cleaning up.
```

### 3. Adding New Providers

```python
# In par_ai_core library:
class MyProvider(BaseLlmProvider):
    def build_chat_model(self) -> BaseChatModel:
        # Implementation
        pass

# Register provider in par_ai_core
LlmProvider.MY_PROVIDER = "MyProvider"
```

### 4. Custom Error Messages

```python
from par_utils.errors.registry import ErrorMessage, ErrorCategory, ErrorSeverity, register_error

# Register new error
register_error(ErrorMessage(
    code="MY_CUSTOM_ERROR",
    message="Custom error: {details}",
    category=ErrorCategory.CUSTOM,
    severity=ErrorSeverity.ERROR,
    solution="Fix the custom issue",
))

# Use in code
from par_gpt.utils.error_helpers import ErrorHandler
handler = ErrorHandler(console)
handler.show_error("MY_CUSTOM_ERROR", details="specific issue")
```

## Threading and Concurrency

### Thread-Safe Context Management

```mermaid
graph TB
    subgraph "Thread Isolation"
        T1[Thread 1<br/>Context:<br/>- user: A<br/>- debug: True<br/>- yes2all: False]
        T2[Thread 2<br/>Context:<br/>- user: B<br/>- debug: False<br/>- yes2all: True]
        T3[Thread N<br/>Context:<br/>- user: C<br/>- debug: True<br/>- yes2all: False]
    end
    
    subgraph "ThreadSafeContextManager"
        CM[Context Manager<br/>🔒 _lock: threading.Lock]
        
        subgraph "Thread Contexts"
            C1["thread_id_1: {user: A, debug: T, ...}"]
            C2["thread_id_2: {user: B, debug: F, ...}"]
            CN["thread_id_n: {user: C, debug: T, ...}"]
        end
    end
    
    T1 --> CM
    T2 --> CM
    T3 --> CM
    
    CM --> C1
    CM --> C2
    CM --> CN
    
    style T1 fill:#1565c0
    style T2 fill:#6a1b9a
    style T3 fill:#00695c
    style CM fill:#ef6c00
    style C1 fill:#0277bd
    style C2 fill:#ad1457
    style CN fill:#2e7d32
```

## Conclusion

This architecture provides a solid foundation for a secure, performant, and extensible AI CLI tool. The modular design allows for easy maintenance and extension, while the comprehensive security measures ensure safe operation even with potentially dangerous AI-generated code execution.

Key architectural strengths:
- **Clean separation of concerns** between layers and packages
- **Comprehensive security** with multiple validation layers powered by PAR Utils
- **High performance** through lazy loading optimization from PAR Utils
- **Easy extensibility** via plugin patterns and modular utilities
- **Thread safety** for concurrent operations using PAR Utils registries
- **Consistent error handling** with centralized registry in PAR Utils
- **Reusable utilities** via the generalized PAR Utils package
- **Backward compatibility** maintained through facade patterns

The architecture has evolved through multiple iterations to address technical debt while maintaining backward compatibility and enhancing security and performance. The extraction of PAR Utils creates a reusable foundation that can benefit other projects while keeping PAR GPT's core functionality intact.