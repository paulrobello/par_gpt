# PAR GPT

## Description

A flexible command-line interface for interacting with various AI language models, supporting multiple providers and
customizable output formats.

**NOTE: This is a very work in progress project and may break at any time.**

## Features

* Can be run in basic LLM mode or agent mode that can use tools
* Shows pricing info when requested
* Support for multiple AI providers (OpenAI, Anthropic, Groq, Google, Ollama, Bedrock)
* Support for custom output formats Markdown, CSV, etc.
* Support for custom context sources stdin, file, url, and web search

## Technology

- Python 3.11+
- Rich for terminal output
- Typer for CLI interface
- Support for multiple AI providers (OpenAI, Ollama, Bedrock)

## Prerequisites

- Python 3.11 or higher
- UV package manager
- API keys for chosen AI provider (except for Ollama)
    - OpenAI: Set OPENAI_API_KEY environment variable
    - Other providers: See provider-specific documentation

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
uv tool install . -U --force
```

### GitHub

```shell
uv tool install -U --force git+https://github.com/paulrobello/par_gpt
```

## Usage

```shell
par_gpt [OPTIONS]
```

### CLI Options

```
--ai-provider          -a      [Ollama|OpenAI|Groq|Anthropic|Google|Bedrock|Github|LlamaCpp]  AI provider to use for processing [env var: PARGPT_AI_PROVIDER] [default: Github]
--model                -m      TEXT                                                           AI model to use for processing. If not specified, a default model will be used. [env var: PARGPT_MODEL] [default: None]
--light-model          -l                                                                     Use a light model for processing. If not specified, a default model will be used. [env var: PARGPT_LIGHT_MODEL]
--ai-base-url          -b      TEXT                                                           Override the base URL for the AI provider. [env var: PARGPT_AI_BASE_URL] [default: None]
--temperature          -t      FLOAT                                                          Temperature to use for processing. If not specified, a default temperature will be used. [env var: PARGPT_TEMPERATURE] [default: 0.5]
--user-agent-appid     -U      TEXT                                                           Extra data to include in the User-Agent header for the AI provider. [env var: PARGPT_USER_AGENT_APPID] [default: None]
--pricing              -p      [none|price|details]                                           Enable pricing summary display [env var: PARGPT_PRICING] [default: none]
--display-output       -d      [none|plain|md|csv|json]                                       Display output in terminal (none, plain, md, csv, or json) [env var: PARGPT_DISPLAY_OUTPUT] [default: md]
--context-location     -f      TEXT                                                           Location of context to use for processing.
--system-prompt        -s      TEXT                                                           System prompt to use for processing. If not specified, a default system prompt will be used. [default: None]
--user-prompt          -u      TEXT                                                           User prompt to use for processing. If not specified, a default user prompt will be used. [default: None]
--agent-mode           -g                                                                     Enable agent mode. [env var: PARGPT_AGENT_MODE]
--max-iterations       -i      INTEGER                                                        Maximum number of iterations to run when in agent mode. [env var: PARGPT_MAX_ITERATIONS] [default: 5]
--max-context-size     -M      INTEGER                                                        Maximum context size when provider supports it. 0 = default. [env var: PARGPT_MAX_CONTEXT_SIZE] [default: 0]
--debug                -D                                                                     Enable debug mode [env var: PARGPT_DEBUG]
--show-tool-calls      -T                                                                     Show tool calls [env var: PARGPT_SHOW_TOOL_CALLS]
--show-config          -S                                                                     Show config [env var: PARGPT_SHOW_CONFIG]
--yes-to-all           -y                                                                     Yes to all prompts [env var: PARGPT_YES_TO_ALL]
--copy-to-clipboard    -c                                                                     Copy output to clipboard
--copy-from-clipboard  -C                                                                     Copy context or context location from clipboard
--no-repl                                                                                     Disable REPL tool [env var: PARGPT_NO_REPL]                                                                                          
--version              -v
--help                                                                                        Show this message and exit.
```

## Environment Variables

### Create a file ~/.par_gpt.env with the following content adjusted for your needs

```shell
# AI Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
GITHUB_TOKEN=
GOOGLE_API_KEY=

# Search
GOOGLE_CSE_ID=
GOOGLE_CSE_API_KEY=
TAVILY_API_KEY=
BRAVE_API_KEY=

# Weather
WEATHERAPI_KEY=

### Tracing (optional)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=par_gpt

# Application Options
PARGPT_AI_PROVIDER=OpenAI
PARGPT_MODEL=# if blank, strong model default will be used
PARGPT_PRICING=price
PARGPT_DISPLAY_OUTPUT=md
PARGPT_DEBUG=false
PARGPT_SHOW_CONFIG=false
PARGPT_AGENT_MODE=false # if this is false par_gpt will only use basic LLM completion
PARGPT_NO_REPL=true # set this to false and enable agent mode to allow agent to write and execute code 
PARGPT_MAX_ITERATIONS=5 # maximum number of iterations to allow when in agent mode. Tool calls require iterations
PARGPT_YES_TO_ALL=false # set this to true to skip all confirmation prompts
PARGPT_SHOW_TOOL_CALLS=true

```

* GROQ_API_KEY is required for Groq. Get a free key from https://console.groq.com/
* ANTHROPIC_API_KEY is required for Anthropic. Get a key from https://console.anthropic.com/
* OPENAI_API_KEY is required for OpenAI. Get a key from https://platform.openai.com/account/api-keys
* GITHUB_TOKEN is required for GitHub Models. Get a free key from https://github.com/marketplace/models
* GOOGLE_API_KEY is required for Google Models. Get a free key from https://console.cloud.google.com
* LANGCHAIN_API_KEY is required for Langchain Langsmith tracing. Get a free key
  from https://smith.langchain.com/settings
* AWS_PROFILE is used for Bedrock authentication. The environment must already be authenticated with AWS.
* No key required to use with Ollama models.
* TAVILY_API_KEY is required for Tavily AI search. Get a free key from https://tavily.com/. Tavily is much better than
  google and is the recommended search provider.
* BRAVE_API_KEY is required for Brave search. Get a free key from https://brave.com/search/api/
* GOOGLE_CSE_ID and GOOGLE_CSE_API_KEY are required for Google search.
* WEATHERAPI_KEY is required for weather. Get a free key from https://www.weatherapi.com/

## Agent mode

NOTE: Agent mode enables tool use one of which is a Python code REPL which allows the AI to write and execute code on
your system.  
If the REPL tool is used it will prompt you before executing the code. Unless you specify --yes-to-all.

## Code Review mode

Code review mode sends code related files to AI for review. The review looks for bugs and issues in the code and provides a ranking of severity as well as suggestions for how to fix them.

Change to the root of the project you want to check (or sub folder for smaller / faster / more cost-effective checks) and run the following:
```shell
par_gpt 'code review'
```

## Example Usage

```shell
# Basic usage with stdin
echo "What is Python?" | par_gpt

# Use a the light model with custom temperature
par_gpt --light-model -t 0.7 "Explain quantum computing"

# Use Ollama with local models Note: you must have qwen2:latest pulled
par_gpt -a ollama -m qwen2:latest "Write a haiku"

# get 3d printer filament grade and properties from youtube then generate a sorted table and save to Obsidian vault.
# this example uses other commands that may not be available on your system however does showcase can it can be chainable
par_yt2text --transcript 'https://www.youtube.com/watch?v=weeG9yOp3i4' | \
par_gpt -p "use the transcript in the context and create a markdown table with 3 columns 'filament_name', 'properties' and 'grade' generate the table based on the feedback from the transcript" | \
par_gpt "sort the table by grade in the following order S,A,B,C,F" | \
save_vault fillament_grade_props

# get commit message for current changes
par_gpt  'display commit message for current changes'

# commit current changes with automatically generated commit message also show config and pricing
par_gpt --show-config --pricing 'commit current changes'

# copy commit message for current changes to clipboard using agent mode
par_gpt -t 0 --debug -g 'create a commit messages that would be relevant to the changes in the current repository and copy to clipboard'

# get details for new Macbook M4 Max (this will use web search and web scrape tools)
par_gpt -g 'get me the details for the new Macbook M4 Max'

# generate a csv file named data.csv filled with fake names and ages
par_gpt -g 'generate a csv file named data.csv filled with fake names and ages'

# read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser
par_gpt -g 'read csv file named data.csv and generate a PNG format image graph with age on the x axis and count of age on y axis. open the PNG in a browser'

# read csv file named data.csv and generate a graph with age on the x axis and count of age on y axis. display the image in the terminal
par_gpt -g 'read csv file named data.csv and generate a graph.png graph with age on the x axis and count of age on y axis. display the image in the terminal size large'

# display the current weather in Woodland CA
par_gpt -g 'current weather in Woodland CA and display the current conditions image / icon in the terminal'

par_gpt --pricing --debug -g -a OpenAI -d md 'what is the value of 4 times the ArcTangent of 1'

# tell me a joke using github model on azure
par_gpt --show-config --debug -p -a Github -m "Llama-3.2-90B-Vision-Instruct" "tell me a joke"
par_gpt --show-config --debug -p -a Github -m "gpt-4o" "tell me a joke"

# Groq vision model
par_gpt -a Groq -m 'llama-3.2-90b-vision-preview' -f PATH_TO_IMAGE "describe this image"

# get image from url and answer question
par_gpt -f "https://gratisography.com/wp-content/uploads/2024/10/gratisography-birthday-dog-sunglasses-1036x780.jpg" "describe the image"

# Get context from url and answer question about it. Note does not currently use RAG so can be token heavy
par_gpt --pricing -c url -f 'https://console.groq.com/docs/vision' "what model ids support vision"

# get image from url and answer question
par_gpt --pricing  -c url -f 'https://freerangestock.com/sample/157314/mystical-glowing-mushrooms-in-a-magical-forest.jpg' "describe this image"

# check code for bugs (change to root for project you want to check)
par_gpt 'code review'
```

## What's New
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
