# PAR Utils

A comprehensive collection of reusable Python utilities for performance optimization, security validation, error handling, caching, and console management.

## Overview

PAR Utils provides a well-architected set of utilities that can be used across different Python projects. Originally extracted from the PAR GPT project, these utilities have been generalized and enhanced for broader applicability.

## Features

- 🚀 **Performance Optimization**: Timing measurement and lazy loading systems
- 🔒 **Security Validation**: Path traversal protection and filename sanitization
- 📝 **Error Management**: Centralized error registry with structured messaging
- 💾 **Caching System**: Thread-safe disk caching with URL download support
- 🖥️ **Console Management**: Rich-based terminal output management

## Installation

Since this package is included with PAR GPT, you can import it directly:

```python
import par_utils
```

For standalone use, you would typically install it via pip (when published):

```bash
pip install par-utils
```

## Quick Start

### Performance Timing

```python
from par_utils import timer, user_timer, timed, enable_timing, show_timing_summary
import time

# Enable timing collection
enable_timing()

# Processing operations (default category)
with timer("database_query"):
    time.sleep(0.2)

# User interaction operations 
with user_timer("user_confirmation"):
    time.sleep(0.5)  # Simulates user thinking time

# Use as decorator
@timed("expensive_calculation")
def calculate_something():
    time.sleep(0.1)
    return "result"

calculate_something()

# Show timing results with dual totals
show_timing_summary()

# Output shows:
# - Grand Total (All): Complete time including user interactions
# - Processing Total: Pure processing time (excludes user wait)
# - User Wait Time: Time spent in user interactions
```

### Lazy Loading

```python
from par_utils import LazyImportManager

# Create lazy import manager
manager = LazyImportManager()

# Lazy import modules
requests = manager.get_cached_import("requests")
json_loads = manager.get_cached_import("json", "loads")

# For application-specific methods, extend the base class
class MyAppLazyImportManager(LazyImportManager):
    def load_my_app_imports(self):
        return {
            "my_module": self.get_cached_import("myapp.module", "MyClass")
        }
```

### Path Security

```python
from par_utils import validate_within_base, sanitize_filename, PathSecurityError

try:
    # Validate path stays within base directory
    safe_path = validate_within_base("user/files/document.txt", "/app/data")
    
    # Sanitize user-provided filename
    clean_name = sanitize_filename("user<input>.txt")  # Returns "user_input_.txt"
    
except PathSecurityError as e:
    print(f"Security violation: {e}")
```

### Error Management

```python
from par_utils import ErrorRegistry, ErrorMessage, ErrorCategory, ErrorSeverity

# Create custom error registry
registry = ErrorRegistry()

# Register custom error
registry.register(ErrorMessage(
    code="CUSTOM_ERROR",
    message="Something went wrong with {operation}",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    solution="Check your input parameters"
))

# Format error with context
error_msg = registry.format_error("CUSTOM_ERROR", operation="file upload")
```

### Caching

```python
from par_utils import CacheManager

# Create cache manager
cache = CacheManager(app_name="myapp")

# Cache data
cache.set_item("key1", "some data")

# Download and cache URLs
file_path = cache.download("https://example.com/data.json")

# Check if item exists
if cache.item_exists("key1"):
    data = cache.get_item("key1")
```

### Console Management

```python
from par_utils import ConsoleManager, get_console

# Use default console
console = get_console()
console.print("Hello [bold]World[/bold]!", style="green")

# Create custom console manager
manager = ConsoleManager()
console = manager.create_console(stderr=False)
```

## Package Structure

```
par_utils/
├── __init__.py              # Main exports
├── performance/
│   ├── timing.py           # Performance measurement utilities
│   └── lazy_loading.py     # Lazy import management
├── security/
│   └── path_validation.py  # Path security validation
├── errors/
│   ├── registry.py         # Error message registry
│   └── handlers.py         # Error handling utilities
├── caching/
│   └── disk_cache.py       # Disk-based caching
└── console/
    └── manager.py          # Console management
```

## API Reference

### Performance Module

#### Timing Utilities

**Core Timing Functions:**
- **`timer(name, metadata=None, category="processing")`**: Context manager for timing operations
- **`user_timer(name, metadata=None)`**: Context manager specifically for user interactions
- **`timed(name=None, metadata=None)`**: Decorator for timing functions
- **`enable_timing()`**: Enable global timing collection
- **`disable_timing()`**: Disable global timing collection
- **`show_timing_summary(detailed=False)`**: Display timing results with dual totals
- **`show_timing_details()`**: Display detailed hierarchical timing breakdown

**Advanced Timing Registry:**
- **`TimingRegistry`**: Global registry for timing data with category support
- **`get_processing_total()`**: Get total time excluding user interactions
- **`get_user_interaction_total()`**: Get total time for user interactions only
- **`get_summary_by_category(category)`**: Get timing summary filtered by category

#### Lazy Loading

- **`LazyImportManager`**: Manages lazy imports with caching
- **`LazyUtilsLoader`**: Specialized loader for utils modules
- **`lazy_import(module_path, item_name=None)`**: Convenience function for lazy importing
- **`LazyAttribute`**: Descriptor for lazy attribute loading

### Security Module

#### Path Validation

- **`validate_within_base(path, base_dir)`**: Ensure path stays within base directory
- **`validate_relative_path(path, max_depth=10)`**: Validate relative path for security
- **`sanitize_filename(filename, replacement="_")`**: Clean dangerous characters from filenames
- **`SecurePathValidator`**: Class for comprehensive path validation
- **`PathSecurityError`**: Exception for security violations

### Error Management

#### Error Registry

- **`ErrorRegistry`**: Centralized error message management
- **`ErrorMessage`**: Structured error with metadata
- **`ErrorCategory`**: Enum for error categorization
- **`ErrorSeverity`**: Enum for error severity levels

#### Error Handlers

- **`ErrorHandler`**: Helper class for consistent error formatting
- **`log_error(error_code, logger=None, **kwargs)`**: Log errors with proper formatting
- **`suppress_error(error_code, **kwargs)`**: Suppress and return formatted error

### Caching Module

#### Disk Cache

- **`CacheManager`**: Thread-safe cache with URL download support
- **`create_cache_manager(cache_dir=None, app_name="par_utils")`**: Factory function

Key methods:
- **`download(url, force=False, timeout=10)`**: Download and cache URL
- **`set_item(key, value)`**: Store data in cache
- **`get_item(key)`**: Retrieve cached data
- **`item_exists(key)`**: Check if item is cached
- **`clear_cache()`**: Remove all cached items

### Console Module

#### Console Management

- **`ConsoleManager`**: Manages Rich console instances
- **`get_console(console=None)`**: Get console with fallback to default
- **`with_console(func)`**: Decorator to ensure console availability
- **`create_console(stderr=True, **kwargs)`**: Create new console instance

## Advanced Usage

### Custom Lazy Loading

```python
from par_utils import LazyUtilsLoader, create_lazy_loader

# Create loader for your package
loader = create_lazy_loader("myproject.utils")

# Get specific utility
config_manager = loader.get_utils_item("config", "ConfigManager")
```

### Error Handling with Rich Formatting

```python
from par_utils import ErrorHandler, create_rich_error_panel
from rich.console import Console

console = Console()
handler = ErrorHandler(console)

# Show formatted error
handler.show_error("VALIDATION_FAILED", field="email", error="Invalid format")

# Create error panel
panel = create_rich_error_panel("SECURITY_PATH_TRAVERSAL", console, path="../../../etc/passwd")
console.print(panel)
```

### Performance Monitoring

```python
from par_utils import timer, enable_timing, show_timing_details

enable_timing()

# Nested timing
with timer("main_operation"):
    with timer("sub_operation_1"):
        time.sleep(0.1)
    
    with timer("sub_operation_2", metadata={"items": 100}):
        time.sleep(0.2)

# Show detailed hierarchical breakdown
show_timing_details()
```

### Secure File Operations

```python
from par_utils import CacheManager, PathSecurityError

cache = CacheManager("/safe/cache/dir", "myapp")

try:
    # This will be validated for security
    data_path = cache.set_item("../../../etc/passwd", "malicious data")
except PathSecurityError:
    print("Security violation prevented!")

# Safe operations
safe_path = cache.set_item("legitimate_file.txt", "safe data")
```

## Security Features

PAR Utils includes comprehensive security measures:

### Path Traversal Protection
- Validates all file paths to prevent directory traversal attacks
- Regex-based detection of dangerous patterns (`../`, `..\\`)
- Cross-platform compatibility (Windows and Unix systems)

### Filename Sanitization
- Removes dangerous characters (`<`, `>`, `"`, `|`, `?`, `*`)
- Prevents Windows reserved names (CON, PRN, AUX, etc.)
- Length validation and trimming

### Secure Caching
- All cache operations validate paths within base directory
- Atomic file operations with backup/restore capabilities
- Thread-safe concurrent access

## Performance Features

### Lazy Loading Benefits
- **Reduced Startup Time**: Import modules only when needed
- **Memory Efficiency**: Lower memory footprint
- **Caching**: Prevent redundant imports
- **Command-Specific Loading**: Load only required modules

### Advanced Timing System Features
- **Dual Category Tracking**: Separates processing time from user interaction time
- **Triple Total Display**: Grand Total (All), Processing Total, User Wait Time
- **Hierarchical Timing**: Nested operation measurement with category inheritance
- **Rich Output**: Beautiful formatted timing reports with color-coded categories
- **Metadata Support**: Associate context with timings for detailed analysis
- **Thread-Safe**: Concurrent timing collection across categories
- **User Interaction Analysis**: Track user response times and think time
- **Performance Isolation**: Get pure processing metrics without user delays

### Timing Categories

**Processing Operations** (`category="processing"`):
- Application logic, computations, I/O operations
- LLM calls, database queries, file processing
- Default category for all timing operations
- Contributes to "Processing Total" metric

**User Interaction Operations** (`category="user_interaction"`):
- User prompts, confirmations, input collection
- Security warnings, interactive modes
- Use `user_timer()` or explicit category parameter
- Contributes to "User Wait Time" metric

**Example Output:**
```
                     Timing Summary                      
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Operation              ┃ Total Time ┃ Count ┃ Average ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ database_query         │     0.200s │     1 │  0.200s │
│ user_confirmation      │     0.500s │     1 │  0.500s │
│ expensive_calculation  │     0.100s │     1 │  0.100s │
├────────────────────────┼────────────┼───────┼─────────┤
│ Grand Total (All)      │     0.800s │     3 │  0.267s │
│ Processing Total       │     0.300s │     2 │  0.150s │
│ User Wait Time         │     0.500s │     1 │  0.500s │
└────────────────────────┴────────────┴───────┴─────────┘
```

## Error Handling Philosophy

PAR Utils follows a structured approach to error handling:

1. **Categorization**: Errors are grouped by category (Security, Network, File Operations, etc.)
2. **Severity Levels**: INFO, WARNING, ERROR, CRITICAL
3. **Solution Guidance**: Each error includes potential solutions
4. **Consistent Formatting**: Rich-formatted output with color coding
5. **Centralized Management**: Single source of truth for error messages

## Thread Safety

All PAR Utils components are designed to be thread-safe:

- **CacheManager**: Uses threading.Lock for concurrent access
- **TimingRegistry**: Thread-safe timing collection
- **LazyImportManager**: Safe concurrent imports
- **ErrorRegistry**: Immutable after initialization

## Contributing

When contributing to PAR Utils:

1. **Maintain Generality**: Keep utilities generic and reusable
2. **Add Type Annotations**: Full type hints for all public APIs
3. **Include Tests**: Comprehensive test coverage
4. **Document Thoroughly**: Clear docstrings and examples
5. **Follow Security Best Practices**: Validate all inputs

## Compatibility

- **Python**: 3.11+
- **Dependencies**: Rich, Requests, Pydantic (minimal external dependencies)
- **Platforms**: Windows, macOS, Linux

## Version History

- **0.1.1**: Architecture refinement
  - Made `LazyImportManager` truly generic (removed application-specific methods)
  - Clear separation between generic utilities and application-specific extensions
  - Better support for inheritance patterns

- **0.1.0**: Initial release with core utilities extracted from PAR GPT
  - Performance timing and lazy loading
  - Security path validation
  - Error management system
  - Disk caching with security features
  - Console management utilities

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## Author

Paul Robello - probello@gmail.com
GitHub: paulrobello