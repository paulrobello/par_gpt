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
--tts                   -T                                                                                                   Use TTS for LLM response. [env var: PARGPT_TTS]
--tts-provider                  [local|kokoro|elevenlabs|openai]                                                             Provider to use for TTS. Defaults to kokoro [env var: PARGPT_TTS_PROVIDER] [default: None]
--tts-voice                     TEXT                                                                                        Voice to use for TTS. Depends on TTS provider chosen. [env var: PARGPT_TTS_VOICE] [default: None]
--tts-list-voices                                                                                                            List voices for selected TTS provider.
--voice-input                                                                                                                Use voice input.
--chat-history                  TEXT                                                                                        Save and or resume chat history from file [env var: PARGPT_CHAT_HISTORY] [default: None]
--loop-mode             -L      [one_shot|infinite]                                                                         One shot or infinite mode [env var: PARGPT_LOOP_MODE] [default: one_shot]
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
--yes-to-all       -y               Yes to all prompts [env var: PARGPT_YES_TO_ALL]
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
PARGPT_DEBUG=false
PARGPT_SHOW_CONFIG=false
PARGPT_REPL=false # set this to true to allow agent to WRITE and EXECUTE CODE ON HOST MACHINE 
PARGPT_CODE_SANDBOX=false # set this to true to allow agent to write and execute code in a secure docker container sandbox
PARGPT_MAX_ITERATIONS=5 # maximum number of iterations to allow when in agent mode. Tool calls require iterations
PARGPT_YES_TO_ALL=false # set this to true to skip all confirmation prompts
PARGPT_SHOW_TOOL_CALLS=true
PARGPT_REASONING_EFFORT=medium # used by o1 and o3 reasoning models
PARGPT_REASONING_BUDGET=0 # used by sonnet 3.7 to enable reasoning mode. 1024 minimum

# REDIS (Currently used for memories)
PARGPT_REDIS_HOST=localhost
PARGPT_REDIS_PORT=6379
PARGPT_REDIS_DB=0

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

Currently par_gpt has a tool to store and retrieve memory.  
Memories are stored on a per user basis defaulting to the logged in user but can be overridden.  
Any memories stored are loaded into context when calling LLMs. 
Currently Redis is used to store memories but this may change

## Agent mode

NOTE: Agent mode enables tool use.  
Some tools require API keys to be available and various keywords in your request to be present to be enabled. 
Only enabling some tools when keywords are present helps to reduce context and LLM confusion.

If the REPL tool is enabled the Code sandbox tool will not be used.

### AI Tools
- Memory - allows storage and retrival of memories in a persistent DB. Currently Redis.
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
- List visible windows - Gets info on all visible windows. Can be used for window / screen capture.
  - keywords: windows
- Figlet - Displays Figlet style text in terminal.
  - keywords: figlet
- Capture Window Image - Capture screenshot of of window or desktop
  - keywords: capture, screenshot
- Image Gen - Generate image using Dall-E-3
  - keywords: image

## Security Features

PAR GPT implements comprehensive security measures to protect against common vulnerabilities:

### Path Traversal Protection
- **Comprehensive validation** of all user-provided file paths
- **Directory traversal prevention** using regex patterns and path resolution
- **Filename sanitization** to remove dangerous characters and reserved names
- **Base directory enforcement** to ensure paths stay within allowed directories
- **Cross-platform compatibility** for Windows and Unix systems

### File Operation Security
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

For detailed security implementation, see [PATH_SECURITY_SUMMARY.md](PATH_SECURITY_SUMMARY.md).

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
par_gpt git 'display commit message for current changes'

# commit current changes with automatically generated commit message also show config and pricing
par_gpt --show-config --pricing details git 'commit current changes'

# copy commit message for current changes to clipboard using agent mode
par_gpt -t 0 --debug agent 'create a commit messages that would be relevant to the changes in the current repository and copy to clipboard'

# get details for new Macbook M4 Max (this will use web search and web scrape tools)
par_gpt agent 'get me the details for the new Macbook M4 Max'

# generate a csv file named data.csv filled with fake names and ages
par_gpt agent 'generate a csv file named data.csv filled with fake names and ages'

# read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser
par_gpt agent 'read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser'

# read csv file named data.csv and generate a graph with age on the x axis and count of age on y axis. display the image in the terminal
par_gpt agent 'read csv file named data.csv and generate a graph.png graph with age on the x axis and count of age on y axis. display the image in the terminal size large'

# display the current weather in Woodland CA
par_gpt agent 'current weather in Woodland CA and display the current conditions image / icon in the terminal'

par_gpt -p details -a OpenAI -d md agent --repl 'what is the value of 4 times the ArcTangent of 1'

# tell me a joke using github model on azure
par_gpt --show-config --debug -p -a Github -m "Llama-3.2-90B-Vision-Instruct" llm "tell me a joke"
par_gpt --show-config --debug -p -a Github -m "gpt-4o" llm "tell me a joke"

# Groq vision model
par_gpt -a Groq -m 'llama-3.2-90b-vision-preview' -f PATH_TO_IMAGE llm "describe this image"

# get image from url and answer question
par_gpt -f "https://gratisography.com/wp-content/uploads/2024/10/gratisography-birthday-dog-sunglasses-1036x780.jpg" llm "describe the image"

# Get context from url and answer question about it. Note does not currently use RAG so can be token heavy
par_gpt -p details -f 'https://console.groq.com/docs/vision' llm "what model ids support vision"

# get image from url and answer question
par_gpt -p details -f 'https://freerangestock.com/sample/157314/mystical-glowing-mushrooms-in-a-magical-forest.jpg' llm "describe this image"

# check code for bugs (change to root for project you want to check)
par_gpt code_review
```

## What's New
- Version 0.12.0:
  - **Major Security Update**: Implemented comprehensive path traversal protection across all file operations
  - **Memory Management**: Fixed critical audio processing memory leaks with resource cleanup
  - **Code Quality**: Centralized utility classes and improved type safety
  - **Configuration**: Secure environment variable handling with Pydantic and SecretStr
  - **File Security**: All file operations now validate user-provided paths to prevent directory traversal attacks
- Version 0.11.0:
  - Added new stardew subcommand for creating pixel art avatar variations
- Version 0.10.0:
  - Fixed sixel error on windows
- Version 0.8.0:
  - Added the tinify image compression command
- Version 0.7.1:
  - Updated PAR AI CORE: Now supports OpenAI Reasoning Effort and Anthropic Reasoning token budget
- Version 0.7.0:
  - Updated PAR AI CORE: Now supports Deepseek and LiteLLM
- Version 0.6.0:
  - Added support for TTS output
  - Added screenshot support
  - Aider support removed (too many dependency conflicts)
- Version 0.5.0:
  - Added Aider command for code editing
- Version 0.4.0:
  - Reworked sub commands and cli options 
- Version 0.3.0:
  - Added support for LlamaCPP (use base_url and run llamacpp in option ai server mode)
  - Added code review agent
  - Added prompt generation agent (work in progress)
  - Updated pricing data
  - Lots of bug fixes and improvements
- Version 0.2.1:
  - Removed --context-source cli option as it is now auto-detected
  - When working with images and model is not specified a suitable vision model will be selected
  - added options to copy context from clipboard and results to clipboard
- Version 0.2.0:
  - Added confirmation prompt for agent mode REPL tool
  - Added yes-to-all flag to skip confirmation prompts
  - Updated pricing data
- Version 0.1.0:
  - Initial release

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Before contributing:

1. Ensure you have Python 3.11+
2. Use UV for dependency management
3. Follow the existing code style
4. Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Paul Robello - probello@gmail.com
GitHub: paulrobello
