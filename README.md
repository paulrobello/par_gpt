# PAR GPT

## Description

A flexible command-line interface for interacting with various AI language models, supporting multiple providers and
customizable output formats.

PAR GPT has grown into a swiss army tool that help accelerate many tasks I deal with on a daily basis.
Some features / functions may be kind of niche to things I work on but could be useful to others as well.

**NOTE: This is a very work in progress project and may break at any time.**

## Features

* Can be run in basic LLM mode or agent mode that can use tools
* Shows pricing info when requested
* Support for multiple AI providers (OpenAI, Anthropic, Groq, Google, Ollama, Bedrock)
* Support for custom output formats Markdown, CSV, etc.
* Support for custom context sources stdin, file, url, and web search
* **Comprehensive security features** with path traversal protection and secure file operations
* **Memory management** with optimized resource cleanup and caching
* **Docker sandbox support** for safe code execution

## Technology

- Python 3.11+
- Rich for terminal output
- Typer for CLI interface
- Support for multiple AI providers (OpenAI, Ollama, Bedrock)
- Uses my [PAR AI Core](https://github.com/paulrobello/par_ai_core)
- **PAR Utils** - Internal utilities package for performance, security, and error management
- **PARGPTLazyImportManager** - Application-specific lazy loading system extending PAR Utils

## Prerequisites

- Python 3.11 or higher
- UV package manager
- API keys for chosen AI provider (except for Ollama and LlamaCpp)
    - See provider-specific documentation for required API key environment variables
- If you want to use image or audio features ensure you install ffmpeg
- If you want to use audio features you may need portaudio installed

### **Install ffmpeg**:

You can download an installer for your OS from the [ffmpeg Website](https://ffmpeg.org/download.html).  

Or use a package manager:

- **On Ubuntu or Debian**:
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```

- **On Arch Linux**:
    ```bash
    sudo pacman -S ffmpeg
    ```

- **On MacOS using Homebrew** ([https://brew.sh/](https://brew.sh/)):
    ```bash
    brew install ffmpeg
    ```

- **On Windows using Winget** [official documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/) :
    ```bash
    winget install Gyan.FFmpeg
    ```
      
- **On Windows using Chocolatey** ([https://chocolatey.org/](https://chocolatey.org/)):
    ```bash
    choco install ffmpeg
    ```

- **On Windows using Scoop** ([https://scoop.sh/](https://scoop.sh/)):
    ```bash
    scoop install ffmpeg
    ```    

### **Install portaudio**:

- **On Linux**:
  ```bash
  sudo apt-get update
  sudo apt-get install portaudio19-dev
  ```

- **On MacOS**:
  ```bash
  brew install portaudio
  ```

### **Install Clang**:
- **On Linux**:
  ```bash
  sudo apt-get update
  sudo apt-get install clang
  ```


## Installation

### Source

```shell
git clone https://github.com/paulrobello/par_gpt.git
cd par_gpt
uv tool install .
```

### GitHub

```shell
uv tool install git+https://github.com/paulrobello/par_gpt
```

## Update

### Source

```shell
cd par_gpt
git pull
uv tool install -U --force .
```

### GitHub

```shell
uv tool install -U --force git+https://github.com/paulrobello/par_gpt
```

## Usage

```shell
par_gpt [OPTIONS]
```

## CLI Args
### Global Options

```
--ai-provider           -a      [Ollama|LlamaCpp|OpenRouter|OpenAI|Google|Github|XAI|Anthropic|Groq|Mistral|Bedrock|LiteLLM]  AI provider to use for processing [env var: PARGPT_AI_PROVIDER] [default: OpenAI]
--model                 -m      TEXT                                                                                         AI model to use for processing. If not specified, a default model will be used. [env var: PARGPT_MODEL] [default: None]
--fallback-models       -B      TEXT (multiple)                                                                              Fallback models to use if the specified model is not available. [env var: PARGPT_FALLBACK_MODELS] [default: None]
--light-model           -l                                                                                                   Use a light model for processing. If not specified, a default model will be used. [env var: PARGPT_LIGHT_MODEL]
--ai-base-url           -b      TEXT                                                                                         Override the base URL for the AI provider. [env var: PARGPT_AI_BASE_URL] [default: None]
--temperature           -t      FLOAT                                                                                        Temperature to use for processing. If not specified, a default temperature will be used. [env var: PARGPT_TEMPERATURE] [default: 0.5]
--user-agent-appid      -U      TEXT                                                                                         Extra data to include in the User-Agent header for the AI provider. [env var: PARGPT_USER_AGENT_APPID] [default: None]
--pricing               -p      [none|price|details]                                                                         Enable pricing summary display [env var: PARGPT_PRICING] [default: none]
--display-output        -d      [none|plain|md|csv|json]                                                                     Display output in terminal (none, plain, md, csv, or json) [env var: PARGPT_DISPLAY_OUTPUT] [default: md]
--context-location      -f      TEXT                                                                                         Location of context to use for processing.
--system-prompt         -s      TEXT                                                                                         System prompt to use for processing. If not specified, a default system prompt will be used. [default: None]
--user-prompt           -u      TEXT                                                                                         User prompt to use for processing. If not specified, a default user prompt will be used. [default: None]
--max-context-size      -M      INTEGER                                                                                      Maximum context size when provider supports it. 0 = default. [env var: PARGPT_MAX_CONTEXT_SIZE] [default: 0]
--reasoning-effort              [low|medium|high]                                                                            Reasoning effort level to use for o1 and o3 models. [env var: PARGPT_REASONING_EFFORT]
--reasoning-budget              INTEGER                                                                                      Maximum context size for reasoning. [env var: PARGPT_REASONING_BUDGET]
--copy-to-clipboard     -c                                                                                                   Copy output to clipboard
--copy-from-clipboard   -C                                                                                                   Copy context or context location from clipboard
--debug                 -D                                                                                                   Enable debug mode [env var: PARGPT_DEBUG]
--show-config           -S                                                                                                   Show config [env var: PARGPT_SHOW_CONFIG]
--user                  -P      TEXT                                                                                         User to use for memory and preferences. [env var: PARGPT_USER] [default: logged in user's username]
--redis-host            -r      TEXT                                                                                         Host or ip of redis server. Used for memory functions. [env var: PARGPT_REDIS_HOST] [default: localhost]
--redis-port            -R      INTEGER                                                                                      Redis port number. Used for memory functions. [env var: PARGPT_REDIS_PORT] [default: 6379]
--enable-redis                                                                                                               Enable Redis memory functionality. [env var: PARGPT_ENABLE_REDIS]
--tts                   -T                                                                                                   Use TTS for LLM response. [env var: PARGPT_TTS]
--tts-provider                  [local|kokoro|elevenlabs|openai]                                                             Provider to use for TTS. Defaults to kokoro [env var: PARGPT_TTS_PROVIDER] [default: None]
--tts-voice                     TEXT                                                                                        Voice to use for TTS. Depends on TTS provider chosen. [env var: PARGPT_TTS_VOICE] [default: None]
--tts-list-voices                                                                                                            List voices for selected TTS provider.
--voice-input                                                                                                                Use voice input.
--chat-history                  TEXT                                                                                        Save and or resume chat history from file [env var: PARGPT_CHAT_HISTORY] [default: None]
--loop-mode             -L      [one_shot|infinite]                                                                         One shot or infinite mode [env var: PARGPT_LOOP_MODE] [default: one_shot]
--show-times                                                                                                                 Show timing information for various operations [env var: PARGPT_SHOW_TIMES]
--show-times-detailed                                                                                                        Show detailed timing information with hierarchical breakdown [env var: PARGPT_SHOW_TIMES_DETAILED]
--yes-to-all            -y                                                                                                   Automatically accept all security warnings and confirmation prompts [env var: PARGPT_YES_TO_ALL]
--version               -v                                                                                                   Show version and exit.
--install-completion                                                                                                         Install completion for the current shell.
--show-completion                                                                                                            Show completion for the current shell, to copy it or customize the installation.
--help                                                                                                                       Show this message and exit.
```

### CLI Commands
```
show-env          Show environment context.
llm               Basic LLM mode with no tools.
agent             Full agent with dynamic tools.
git               Git commit helper.
code-review       Review code.
generate-prompt   Use meta prompting to generate a new prompt.
sandbox           Build and run code runner docker sandbox.
update-deps       Update python project dependencies.
pub-repo-gh       Create and publish a github repository using current local git repo as source.
tinify            Compress image using tinify.
pi-profile        Convert Pyinstrument json report to markdown.
stardew           Generate pixel art avatar variation.
```

### CLI agent Arguments
```
--max-iterations   -i      INTEGER  Maximum number of iterations to run when in agent mode. [env var: PARGPT_MAX_ITERATIONS] [default: 5]
--show-tool-calls  -T               Show tool calls [env var: PARGPT_SHOW_TOOL_CALLS]
--repl                              Enable REPL tool [env var: PARGPT_REPL]
--code-sandbox     -c               Enable code sandbox tool. Requires a running code sandbox container. [env var: PARGPT_CODE_SANDBOX]
```

### CLI sandbox Arguments
```
--action  -a      [start|stop|build]  Sandbox action to perform. [required]
```

### Update deps Arguments
```
--no-uv-update  -n        Don't run 'uv sync -U'
```

### Publish Repo to Github
```
--repo-name  -r      TEXT  Name of the repository. (Defaults to repo root folder name)
--public     -p            Publish as public repo.
```

### Tinify arguments
```
--image         -i      TEXT  Image to tinify. [default: None] [required]
--output-image  -o      TEXT  File to save compressed image to. Defaults to image_file.
```

## Pyinstrument (pi-profile) arguments
```
--profile_json  -p      TEXT     JSON report to examine. [default: None] [required]
--module        -m      TEXT     Module to include in analysis. Can be specified more than once. [default: None]
--output        -o      TEXT     File to save markdown to. Defaults to screen. [default: None]
--limit         -l      INTEGER  Max number of functions to include. [default: 15]
```

## Stardew arguments
```
--prompt         -p      TEXT  User request for avatar variation. [default: None] [required]
--system-prompt  -S      TEXT  System prompt to use
                               [env var: PARGPT_SD_SYSTEM_PROMPT]
                               [default: Make this character {user_prompt}. ensure you maintain the pixel art style.]
--src            -s      PATH  Source image to use as reference. [env var: PARGPT_SD_SRC_IMAGE] [default: None]
--out-folder     -O      PATH  Output folder for generated images. [env var: PARGPT_SD_OUT_FOLDER] [default: None]
--out            -o      TEXT  Output image name. [default: None]
--display        -d            Display resulting image in the terminal. [env var: PARGPT_SD_DISPLAY_IMAGE]
```

## Environment Variables

### Create a file ~/.par_gpt.env with the following content adjusted for your needs

```shell
# AI API KEYS
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
XAI_API_KEY=
GOOGLE_API_KEY=
MISTRAL_API_KEY=
GITHUB_TOKEN=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
# Used by Bedrock
AWS_PROFILE=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Search
GOOGLE_CSE_ID=
GOOGLE_CSE_API_KEY=
SERPER_API_KEY=
SERPER_API_KEY_GOOGLE=
TAVILY_API_KEY=
JINA_API_KEY=
BRAVE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Misc api
WEATHERAPI_KEY=
GITHUB_PERSONAL_ACCESS_TOKEN=
TINIFY_KEY=

### Tracing (optional)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=par_gpt

# Application Options
PARGPT_AI_PROVIDER=OpenAI
PARGPT_MODEL=# if blank, strong model default will be used
PARGPT_PRICING=price # none | price | details
PARGPT_DISPLAY_OUTPUT=md
# PARGPT_DEBUG=1 # uncomment to enable debug mode
# PARGPT_SHOW_CONFIG=1 # uncomment to show config by default
# PARGPT_REPL=1 # uncomment to allow agent to WRITE and EXECUTE CODE ON HOST MACHINE 
# PARGPT_CODE_SANDBOX=1 # uncomment to allow agent to write and execute code in a secure docker container sandbox
PARGPT_MAX_ITERATIONS=5 # maximum number of iterations to allow when in agent mode. Tool calls require iterations
# PARGPT_YES_TO_ALL=1 # uncomment to skip all confirmation prompts
PARGPT_SHOW_TOOL_CALLS=1 # comment out or remove this line to hide tool calls
PARGPT_REASONING_EFFORT=medium # used by o1 and o3 reasoning models
PARGPT_REASONING_BUDGET=0 # used by sonnet 3.7 to enable reasoning mode. 1024 minimum

# Performance Monitoring
# PARGPT_SHOW_TIMES=1 # uncomment to show timing summary by default
# PARGPT_SHOW_TIMES_DETAILED=1 # uncomment to show detailed timing breakdown by default

# REDIS (Currently used for memories)
PARGPT_REDIS_HOST=localhost
PARGPT_REDIS_PORT=6379
PARGPT_REDIS_DB=0
PARGPT_ENABLE_REDIS=1 # set to 1 to enable Redis memory functionality, comment out or omit to disable (default: disabled)

# NEO4J (Just testing)
PARGPT_NEO4J_HOST=localhost
PARGPT_NEO4J_PORT=7687
PARGPT_NEO4J_USER=neo4j
PARGPT_NEO4J_PASS=neo4j
```

### AI API KEYS

* ANTHROPIC_API_KEY is required for Anthropic. Get a key from https://console.anthropic.com/
* OPENAI_API_KEY is required for OpenAI. Get a key from https://platform.openai.com/account/api-keys
* GITHUB_TOKEN is required for GitHub Models. Get a free key from https://github.com/marketplace/models
* GOOGLE_API_KEY is required for Google Models. Get a free key from https://console.cloud.google.com
* XAI_API_KEY is required for XAI. Get a free key from https://x.ai/api
* GROQ_API_KEY is required for Groq. Get a free key from https://console.groq.com/
* MISTRAL_API_KEY is required for Mistral. Get a free key from https://console.mistral.ai/
* OPENROUTER_KEY is required for OpenRouter. Get a key from https://openrouter.ai/
* DEEPSEEK_API_KEY is required for Deepseek. Get a key from https://platform.deepseek.com/
* AWS_PROFILE or AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are used for Bedrock authentication. The environment must
  already be authenticated with AWS.
* No key required to use with Ollama or LlamaCpp.

### Search

* TAVILY_API_KEY is required for Tavily AI search. Get a free key from https://tavily.com/. Tavily is much better than
* JINA_API_KEY is required for Jina search. Get a free key from https://jina.ai
* BRAVE_API_KEY is required for Brave search. Get a free key from https://brave.com/search/api/
* SERPER_API_KEY is required for Serper search. Get a free key from https://serper.dev
* SERPER_API_KEY_GOOGLE is required for Google Serper search. Get a free key from https://serpapi.com/
* GOOGLE_CSE_ID and GOOGLE_CSE_API_KEY are required for Google search.
* REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are needed for Reddit search. Get a free key
  from https://www.reddit.com/prefs/apps/

### Misc

* GITHUB_PERSONAL_ACCESS_TOKEN is required for GitHub related tools. Get a free key
  from https://github.com/settings/tokens
* WEATHERAPI_KEY is required for weather. Get a free key from https://www.weatherapi.com/
* LANGCHAIN_API_KEY is required for Langchain / Langsmith tracing. Get a free key
  from https://smith.langchain.com/settings
* TINIFY_KEY is required to use the tinify images compression tools

### Database and Memory

PAR GPT includes an optional memory system for storing and retrieving persistent memories across sessions.  
Memories are stored on a per-user basis (defaulting to the logged-in user) and are automatically loaded into context when calling LLMs.

**Redis Memory System**:
- **Disabled by default** - No Redis server required for basic functionality
- **Optional functionality** - Enable with `--enable-redis` flag or `PARGPT_ENABLE_REDIS=1` environment variable
- **Smart loading** - Memory tool (`ai_memory_db`) only available when Redis is enabled
- **Graceful fallback** - Applications runs normally without Redis, no connection errors
- **Per-user storage** - Memories isolated by username, customizable with `--user` option

To use memory functionality:
1. Install and start a Redis server
2. Enable with `--enable-redis` flag or set `PARGPT_ENABLE_REDIS=1` in your environment
3. The `ai_memory_db` tool will become available in agent mode for storing/retrieving memories

## Agent mode

NOTE: Agent mode enables tool use.  
Some tools require API keys to be available and various keywords in your request to be present to be enabled. 
Only enabling some tools when keywords are present helps to reduce context and LLM confusion.

If the REPL tool is enabled the Code sandbox tool will not be used.

### AI Tools
- Memory (`ai_memory_db`) - Allows storage and retrieval of memories in Redis (optional, requires `--enable-redis`).
- REPL - Allows the AI to **WRITE AND EXECUTE CODE ON YOUR SYSTEM**.  
  The REPL tool must be manually enabled. If the REPL tool is used it will prompt you before executing the code. Unless you specify --yes-to-all.
- Code sandbox - Allows AI to write and execute code in a secure docker sandbox container which must be setup separately.
  The Code sandbox tool must be manually enabled.
- Open URL - Opens a URL in the default browser.
- Fetch URL - Fetches the content of one or more webpages and returns as markdown.
- Show image in terminal - Displays low resolution image in terminal sized based on terminal dimensions.
- Youtube search - Search youtube and get video info.
  - keywords: youtube
- Youtube transcript - Get youtube transcript for video.
  - keywords: youtube
- Hacker News - Fetch top posts from HackerNews.
  - keywords: hackernews
- Git - Allows interaction with local git repos.
  - keywords: git, commit
- Tavily search - Search web and get scraped web results.
- Serper search - Search web using serper.
- Google search - Search web using google.
- Brave search - Search web using brave search.
- Reddit search - Search reddit and get posts and optionally comments.
  - keywords: reddit
- Clipboard - Allows copy to and from clipboard.
  - keywords: clipboard
- RSS - Fetch RSS feed content.
  - keywords: rss
- Weather - Fetch weather info.
  - keywords: weather, wx
- Github - Allows creation, publishing to and listing of personal Github repos.
  - keywords: github
- List visible windows - Gets info on all visible windows. Can be used for window capture.
  - keywords: window
- List available screens - Gets info on all connected displays (physical and virtual). Used for screen capture.
  - keywords: screen, display
- Figlet - Displays Figlet style text in terminal.
  - keywords: figlet
- Capture Window Image - Capture screenshot of specific application window
  - keywords: capture, screenshot
- Capture Screen Image - Capture screenshot of entire screen/display with multi-monitor support
  - keywords: capture, screenshot
- Image Gen - Generate image using Dall-E-3
  - keywords: image

## PAR Utils Package

PAR GPT is built around the **PAR Utils** package - a fully-integrated collection of reusable Python utilities that replaced legacy duplicate modules:

- 🚀 **Performance Optimization**: Timing measurement and lazy loading systems
- 🔒 **Security Validation**: Path traversal protection and filename sanitization  
- 📝 **Error Management**: Centralized error registry with structured messaging
- 💾 **Caching System**: Thread-safe disk caching with URL download support
- 🖥️ **Console Management**: Rich-based terminal output management

For detailed documentation, see [PAR Utils README](src/par_utils/README.md).

## Security Features

PAR GPT implements comprehensive security measures to protect against common vulnerabilities, powered by the PAR Utils security module:

### Path Traversal Protection (PAR Utils)
- **Comprehensive validation** of all user-provided file paths
- **Directory traversal prevention** using regex patterns and path resolution
- **Filename sanitization** to remove dangerous characters and reserved names
- **Base directory enforcement** to ensure paths stay within allowed directories
- **Cross-platform compatibility** for Windows and Unix systems

### File Operation Security (PAR Utils)
- **Secure file validation** for all read/write operations
- **Content type validation** for uploaded files and downloads
- **Atomic file operations** with backup and restore capabilities
- **Size limits** enforced on file operations to prevent resource exhaustion

### Code Execution Safety
- **Docker sandbox isolation** for AI-generated code execution
- **User confirmation prompts** for potentially dangerous operations
- **Input validation** and sanitization for all external inputs
- **Memory management** with proper resource cleanup and limits

### Environment Security
- **Secure credential handling** using Pydantic SecretStr
- **Environment variable validation** and type checking
- **API key protection** from logs and debug output

### Security Warnings and Automation Control

PAR GPT includes comprehensive security warnings for potentially dangerous operations, with flexible automation controls:

#### Security Warning Types
- **Code Execution Warnings** - Before executing arbitrary code via REPL or sandbox
- **Command Execution Warnings** - Before running system commands (screen capture, file operations)
- **Environment Modification Warnings** - Before setting environment variables

#### Automation and Silent Operation
- **`--yes-to-all` Global Flag** - Automatically accepts all security warnings and confirmation prompts
- **Silent automation support** - Enables headless/scripted usage without interactive prompts
- **Per-operation control** - Individual tools respect the global automation setting
- **Environment variable** - `PARGPT_YES_TO_ALL=1` for persistent automation mode

#### Usage Examples
```bash
# Interactive mode (default) - shows security warnings and prompts for confirmation
par_gpt agent "write and execute Python code to analyze data"

# Automated mode - silently executes without prompts
par_gpt --yes-to-all agent "write and execute Python code to analyze data"

# Environment variable for persistent automation
export PARGPT_YES_TO_ALL=1
par_gpt agent "take a screenshot and analyze it"
```

For detailed security implementation, see [PATH_SECURITY_SUMMARY.md](PATH_SECURITY_SUMMARY.md).

## Performance Monitoring

PAR GPT includes built-in timing utilities (powered by PAR Utils) to help analyze performance and identify bottlenecks across different operations.

### Timing Options

- **`--show-times`** - Display a summary table with operation timings, counts, averages, and grand total
- **`--show-times-detailed`** - Show hierarchical timing breakdown with nested operations and metadata

### What Gets Timed

The timing system tracks key performance areas across two categories:

**Processing Operations:**
- **Startup Operations**: Environment loading, LLM configuration setup, context processing
- **LLM Operations**: Chat model building, LLM invoke calls, agent executor calls  
- **Tool Loading**: Core tools loading, conditional tool loading based on keywords
- **Agent Operations**: Tool execution, multi-step agent workflows

**User Interaction Operations:**
- **Interactive Input**: User prompts in loop mode and question entry
- **Security Confirmations**: Command execution, environment modification, code execution warnings
- **REPL Confirmations**: Python code execution prompts in agent mode
- **AI Tool Prompts**: Agent-requested user input during execution

### Example Output

**Simple Summary (`--show-times`):**
```
                     Timing Summary                      
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Operation              ┃ Total Time ┃ Count ┃ Average ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ llm_invoke             │     5.327s │     1 │  5.327s │
│ user_input_prompt      │     2.150s │     1 │  2.150s │
│ security_confirmation  │     0.800s │     1 │  0.800s │
│ build_chat_model       │     0.070s │     1 │  0.070s │
│ llm_config_setup       │     0.000s │     1 │  0.000s │
├────────────────────────┼────────────┼───────┼─────────┤
│ Grand Total (All)      │     8.347s │     5 │  1.669s │
│ Processing Total       │     5.397s │     3 │  1.799s │
│ User Wait Time         │     2.950s │     2 │  1.475s │
└────────────────────────┴────────────┴───────┴─────────┘
```

**Detailed View (`--show-times-detailed`):**
```
Timing Details (Grand Total: 8.347s, 5 operations | Processing: 5.397s | User Wait: 2.950s)
├── llm_config_setup: 0.000s
├── build_chat_model: 0.070s
├── user_input_prompt: 2.150s
├── llm_invoke: 5.327s (model=gpt-4o)
└── security_confirmation: 0.800s
```

### Timing Categories and Analysis

The timing system provides three key metrics:

- **Grand Total (All)**: Complete wall-clock time including all operations and user interactions
- **Processing Total**: Pure application processing time excluding user wait time (shown in green)
- **User Wait Time**: Time spent waiting for user input, confirmations, and interactions (shown in yellow)

This dual-total approach enables:
- **Accurate Performance Analysis**: Get true application performance without user delays
- **User Experience Insights**: Understand how long users take to respond to prompts
- **Bottleneck Identification**: Distinguish between slow processing vs slow user response
- **Automation Planning**: Estimate pure processing time for automated workflows

### Environment Variables

Timing can also be enabled via environment variables:
- `PARGPT_SHOW_TIMES=1` - Enable basic timing summary
- `PARGPT_SHOW_TIMES_DETAILED=1` - Enable detailed timing view

### Usage Examples

```bash
# Show timing summary for LLM operations
echo "Analyze performance" | par_gpt --show-times llm

# Show detailed timing for agent operations with tools
echo "Search web and analyze results" | par_gpt --show-times-detailed agent

# Combine with other debugging options
par_gpt --show-times --debug --pricing details agent "complex task"
```

The timing information helps identify performance bottlenecks, optimize workflows, and understand the execution profile of different PAR GPT operations.

## Code sandbox
The code sandbox allows the AI agent mode to write and execute code safely contained in a docker container.  
To use the sandbox you must have `docker` installed as well as build and run the sandbox container.  
Sandbox setup steps:
### From code
```bash
git clone https://github.com/paulrobello/par_gpt.git
cd par_gpt
make sandbox
```
### From installed tool
```bash
par_gpt sandbox -a build
```

## Code Review mode

Code review mode sends code related files to AI for review. The review looks for bugs and issues in the code and
provides a ranking of severity as well as suggestions for how to fix them.

Change to the root of the project you want to check (or sub folder for smaller / faster / more cost-effective checks)
and run the following:

```shell
par_gpt code_review
```


## Example Usage

```shell
# Basic usage with stdin
echo "What is Python?" | par_gpt llm

# Use a the light model with custom temperature
par_gpt --light-model -t 0.7 llm "Explain quantum computing"

# Use Ollama with local models Note: you must have qwen2:latest pulled
par_gpt -a ollama -m qwen2:latest llm "Write a haiku"

# get 3d printer filament grade and properties from youtube then generate a sorted table and save to Obsidian vault.
# this example uses other commands that may not be available on your system however does showcase can it can be chainable
par_yt2text --transcript 'https://www.youtube.com/watch?v=weeG9yOp3i4' | \
par_gpt -p "use the transcript in the context and create a markdown table with 3 columns 'filament_name', 'properties' and 'grade' generate the table based on the feedback from the transcript" llm | \
par_gpt llm "sort the table by grade in the following order S,A,B,C,F" | \
save_vault fillament_grade_props

# get commit message for current changes
par_gpt git "display commit message for current changes"

# commit current changes with automatically generated commit message also show config and pricing
par_gpt --show-config --pricing details git "commit current changes"

# copy commit message for current changes to clipboard using agent mode
par_gpt -t 0 --debug agent "create a commit messages that would be relevant to the changes in the current repository and copy to clipboard"

# Performance monitoring examples
# Show timing summary for LLM operations
par_gpt --show-times llm "Analyze this complex problem"

# Show detailed timing breakdown for agent operations
par_gpt --show-times-detailed agent "search for latest AI news and summarize findings"

# Combine timing with other debugging options
par_gpt --show-times --debug --pricing details agent "complex research task"

# get details for new Macbook M4 Max (this will use web search and web scrape tools)
par_gpt agent "get me the details for the new Macbook M4 Max"

# generate a csv file named data.csv filled with fake names and ages
par_gpt agent "generate a csv file named data.csv filled with fake names and ages"

# read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser
par_gpt agent "read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser"

# read csv file named data.csv and generate a graph with age on the x axis and count of age on y axis. display the image in the terminal
par_gpt agent "read csv file named data.csv and generate a graph.png graph with age on the x axis and count of age on y axis. display the image in the terminal size large"

# display the current weather in Woodland CA
par_gpt agent "current weather in Woodland CA and display the current conditions image / icon in the terminal"

par_gpt -p details -a OpenAI -d md agent --repl "what is the value of 4 times the ArcTangent of 1"

# tell me a joke using github model on azure
par_gpt --show-config --debug -p -a Github -m "Llama-3.2-90B-Vision-Instruct" llm "tell me a joke"
par_gpt --show-config --debug -p -a Github -m "gpt-4o" llm "tell me a joke"

# Groq vision model
par_gpt -a Groq -m "llama-3.2-90b-vision-preview" -f PATH_TO_IMAGE llm "describe this image"

# get image from url and answer question
par_gpt -f "https://gratisography.com/wp-content/uploads/2024/10/gratisography-birthday-dog-sunglasses-1036x780.jpg" llm "describe the image"

# Get context from url and answer question about it. Note does not currently use RAG so can be token heavy
par_gpt -p details -f "https://console.groq.com/docs/vision" llm "what model ids support vision"

# get image from url and answer question
par_gpt -p details -f "https://freerangestock.com/sample/157314/mystical-glowing-mushrooms-in-a-magical-forest.jpg" llm "describe this image"

# check code for bugs (change to root for project you want to check)
par_gpt code_review

# list available screens/displays
par_gpt agent "list available screens"

# capture screenshot of primary screen
par_gpt agent "take a screenshot of my screen"

# capture specific display in multi-monitor setup
par_gpt agent "capture screenshot of display 2"

# use memory functionality (requires Redis server and --enable-redis flag)
par_gpt --enable-redis agent "remember that I prefer concise responses"
par_gpt --enable-redis agent "what do you remember about my preferences?"

# default behavior (no Redis required, memory tool not available)
par_gpt agent "tell me a joke"  # clean startup, no Redis errors

# automatically accept all security warnings and confirmation prompts
par_gpt --yes-to-all agent "write and execute a python script to analyze data.csv"

# combine with other global options
par_gpt --yes-to-all --debug --show-config agent "complex task with code execution"

# use environment variable to set globally
export PARGPT_YES_TO_ALL=1
par_gpt agent "task that might require confirmations"

# AI tools examples (now working after import fixes)
# create ASCII art text
par_gpt agent "create figlet text that says HELLO"

# generate an image using DALL-E and display in terminal
par_gpt agent "generate an image of a cyberpunk city and display it in the terminal"

# list all available screens/displays
par_gpt agent "list available screens"

# capture screenshot of primary screen
par_gpt agent "take a screenshot of my screen"

# list all visible windows
par_gpt agent "list visible windows"
```

## What's New
- Version 0.14.0:
  - **PAR Utils Package Creation**: Major architectural refactoring to extract reusable utilities into a separate package
    - **Modular Architecture** - Created `src/par_utils/` package with organized utility modules:
      - `performance/` - Timing measurement and lazy loading systems
      - `security/` - Path validation and filename sanitization utilities
      - `errors/` - Centralized error registry with structured messaging
      - `caching/` - Thread-safe disk caching with URL download support
      - `console/` - Rich-based terminal output management
    - **Backward Compatibility** - Maintained full compatibility via facade pattern in `par_gpt/utils/__init__.py`
    - **Generalized Design** - Utilities made generic for broader applicability beyond PAR GPT
    - **Enhanced Security** - Path security now uses comprehensive `SecurePathValidator` with multiple validation layers
    - **Performance Benefits** - Improved lazy loading with `LazyImportManager` and `LazyUtilsLoader`
    - **Documentation** - Complete API documentation and usage examples in PAR Utils README.md
  - **Architecture Documentation**: Updated ARCHITECTURE.md to reflect the new modular package structure
  - **Advanced User Interaction Timing**: Enhanced timing system to distinguish between processing time and user wait time
    - **Dual Grand Totals** - Shows both "Grand Total (All)" and "Processing Total" (excluding user wait time)
    - **User Interaction Categorization** - Tracks time spent waiting for user input/confirmations separately
    - **Comprehensive Coverage** - Times all user prompts: interactive input, security confirmations, REPL confirmations, AI tool prompts
    - **Enhanced Analytics** - Get accurate performance metrics without user think time skewing results
  - **Duplicate Code Cleanup**: Removed legacy duplicate files (timing.py, error_registry.py, console_manager.py, cache_manager.py) after confirming all functionality is preserved in par_utils
  - **Comprehensive Testing**: All utilities moved successfully with maintained functionality across 26+ files
- Version 0.13.0:
  - **AI Tools Import Fix**: Resolved critical import issues affecting 10+ AI tools
    - **Screen capture tools** - Fixed `ai_capture_screen_image()` and `ai_capture_window_image()` for multi-monitor support
    - **Image generation** - Restored `ai_image_gen_dali()` for DALL-E image creation with terminal display
    - **Text generation** - Fixed `ai_figlet()` for ASCII art text generation
    - **GitHub integration** - Restored `ai_github_publish_repo()` for repository publishing
    - **System interaction** - Fixed `ai_list_visible_windows()` and `ai_list_available_screens()` for window/display management
    - **Root cause**: Utils package restructuring broke facade pattern imports; fixed by extending utils `__init__.py` with dynamic loading from original `utils.py`
  - **Documentation Updates**: Updated README.md, CLAUDE.md, and ARCHITECTURE.md with corrected command syntax and AI tools information
  - **Command Syntax**: Standardized examples to use `uv run par_gpt "prompt"` instead of `echo "prompt" | uv run par_gpt agent`
- Version 0.12.2:
  - **Global `--yes-to-all` Security Bypass**: Added comprehensive global flag to automatically accept all security warnings and confirmation prompts
    - **Silent automation** - Enables headless/scripted usage without interactive prompts
    - **Cross-tool support** - Works with REPL code execution, screen capture, window capture, and all security-sensitive operations
    - **Environment variable** - `PARGPT_YES_TO_ALL=1` for persistent configuration
    - **Security conscious** - Maintains warnings by default, only bypasses when explicitly requested
  - **Major Startup Performance Optimization**: Comprehensive lazy loading system reducing startup time by 25-50%
    - **Command-specific import routing** - Only loads modules needed for specific commands
    - **Lazy import manager** with caching to prevent duplicate module loading
    - **Deferred global initialization** - Clipboard and warning configuration only when needed
    - **Function-level lazy imports** for heavy modules (LLM config, providers, Rich components)
    - **Utils module restructuring** with dynamic `__getattr__` lazy loading
  - **Optimized Command Performance**:
    - `--version` command: ~1.45s (minimal imports)
    - `show-env` command: ~1.5s (optimized startup)
    - `llm` command: Significant startup improvement with lazy provider loading
  - **Lazy Loading Architecture**:
    - Created `lazy_import_manager.py` for command-specific imports
    - Created `lazy_utils_loader.py` for utils module lazy loading
    - Modified `__init__.py` for deferred global initialization
    - Updated `utils/__init__.py` with dynamic attribute access
  - **Performance Monitoring Integration**: Timing utilities show optimization impact
- Version 0.12.1:
  - **Performance Optimization**: Implemented lazy loading for AI tools, reducing startup time by ~10%
    - Heavy imports (PIL, Redis, GitHub APIs) now loaded only when needed
    - Conditional tool loading based on keywords and requirements
    - Module-level imports moved to function-level for better performance
  - **Performance Monitoring**: Added comprehensive timing utilities for performance analysis
    - `--show-times` CLI option for summary timing table with grand total
    - `--show-times-detailed` CLI option for hierarchical timing breakdown
    - Tracks startup, LLM operations, tool loading, and agent execution times
    - Rich-formatted output with operation counts, averages, and metadata
  - **Redis Memory Control**: Added optional Redis memory system with smart defaults
    - **Disabled by default** - No Redis server required for basic functionality
    - `--enable-redis` CLI flag and `PARGPT_ENABLE_REDIS` environment variable
    - Graceful fallback when Redis unavailable, no connection errors
    - Memory tool (`ai_memory_db`) only loads when Redis enabled
  - **Improved Startup Experience**: Clean startup without Redis connection errors
  - **Better Resource Management**: Tools and dependencies loaded on-demand
- Version 0.12.0:
  - **New Screen Capture Tools**: Added comprehensive screen capture functionality with multi-monitor support
    - `ai_list_available_screens` - Detects all connected displays (physical and virtual)
    - `ai_capture_screen_image` - Captures screenshots of specific screens with intelligent display selection
    - Integrates with existing security warning system for safe operation
  - **Major Security Update**: Implemented comprehensive path traversal protection across all file operations
  - **Memory Management**: Fixed critical audio processing memory leaks with resource cleanup
  - **Code Quality**: Centralized utility classes and improved type safety
  - **Configuration**: Secure environment variable handling with Pydantic and SecretStr
  - **File Security**: All file operations now validate user-provided paths to prevent directory traversal attacks
- Version 0.11.0:
  - Added new stardew subcommand for creating pixel art avatar variations
- **older...**
  - Version 0.10.0: Fixed sixel error on windows
  - Version 0.8.0: Added the tinify image compression command
  - Version 0.7.1: Updated PAR AI CORE: Now supports OpenAI Reasoning Effort and Anthropic Reasoning token budget
  - Version 0.7.0: Updated PAR AI CORE: Now supports Deepseek and LiteLLM
  - Version 0.6.0: Added support for TTS output, screenshot support, removed Aider support
  - Version 0.5.0: Added Aider command for code editing
  - Version 0.4.0: Reworked sub commands and cli options
  - Version 0.3.0: Added LlamaCPP support, code review agent, prompt generation agent
  - Version 0.2.1: Auto-detected context source, vision model selection, clipboard options
  - Version 0.2.0: Added confirmation prompts, yes-to-all flag, updated pricing data
  - Version 0.1.0: Initial release

## Architecture

PAR GPT follows a sophisticated modular architecture with comprehensive security measures and performance optimizations. For detailed information about the system design, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Key Architectural Features

- **Modular Design**: Clean separation between CLI, commands, and core logic
- **PAR Utils Integration**: Reusable utilities package for performance, security, and error management
- **Two-Layer Lazy Loading**: Generic `LazyImportManager` (PAR Utils) + `PARGPTLazyImportManager` (application-specific)
- **Security First**: Comprehensive path validation and execution safety (powered by PAR Utils)
- **Performance Optimized**: Lazy loading reducing startup time by 25-50% (PAR Utils timing system)
- **Thread Safety**: Thread-safe context management for concurrent operations
- **Extensible**: Plugin-style tool loading and command patterns

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Before contributing:

1. Ensure you have Python 3.11+
2. Use UV for dependency management
3. Follow the existing code style
4. Update documentation as needed
5. Review the [Architecture Documentation](ARCHITECTURE.md) for design patterns

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Paul Robello - probello@gmail.com
GitHub: paulrobello
