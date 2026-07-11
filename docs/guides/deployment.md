# Deployment Guide

Operational setup for PAR GPT: the Docker code sandbox lifecycle, Redis-backed memory,
headless/CI usage, and the automation pattern around `PARGPT_YES_TO_ALL`.

For diagnosing specific failures, see [Troubleshooting](../troubleshooting.md).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Sandbox lifecycle](#sandbox-lifecycle)
- [Redis-backed memory](#redis-backed-memory)
- [Headless and CI usage](#headless-and-ci-usage)
- [The PARGPT_YES_TO_ALL automation pattern](#the-pargpt_yes_to_all-automation-pattern)
- [Environment-variable summary](#environment-variable-summary)
- [Related Documentation](#related-documentation)

## Prerequisites

- Python 3.12 or higher (3.13 recommended), installed via [UV](https://docs.astral.sh/uv/)
- A provider API key in the environment (for example `OPENAI_API_KEY`)
- Docker, only if you use the code sandbox
- Redis, only if you enable memory features
- `ffmpeg`, only if you use image/audio features (see [Troubleshooting](../troubleshooting.md))

## Sandbox lifecycle

The code sandbox is a Docker container that lets the agent write and run Python in isolation.
Build and start it before using `--code-sandbox`.

The sandbox is managed through the `sandbox` subcommand or the equivalent Makefile target:

| Action | CLI | Makefile | Effect |
| --- | --- | --- | --- |
| Build | `par_gpt sandbox -a build` | `make sandbox` (also starts) | Build/rebuild the Docker image |
| Start | `par_gpt sandbox -a start` | `make sandbox` | Start the container |
| Stop | `par_gpt sandbox -a stop` | — | Stop the running container |

Typical first-time setup:

```bash
make sandbox
```

This runs `docker compose -p par_gpt_sandbox up -d --build --force-recreate` against
`src/sandbox/docker`, so the container is rebuilt and started in one step.

After changing the Dockerfile, rebuild explicitly:

```bash
par_gpt sandbox -a build
par_gpt sandbox -a start
```

Then use the sandbox from an agent run:

```bash
par_gpt --code-sandbox agent "summarize the files in the current directory"
```

> **Note:** The host Python REPL (`--repl`) and the sandboxed `execute_code` tool are mutually
> exclusive. If the REPL is enabled, the sandbox tool is not loaded.

## Redis-backed memory

Memory is **optional and disabled by default**. When enabled, PAR GPT stores and retrieves
memories in Redis via the `ai_memory_db` tool.

1. Run a Redis server (any standard method works):

   ```bash
   # macOS example
   brew install redis && brew services start redis
   ```

2. Point PAR GPT at it and enable memory:

   ```bash
   par_gpt --enable-redis --redis-host localhost --redis-port 6379 llm "remember I prefer concise answers"
   ```

   Or configure it persistently via environment variables (see the table below). PAR GPT falls
   back gracefully when Redis is not enabled — no server is required for basic functionality.

## Headless and CI usage

PAR GPT is a CLI and runs cleanly in non-interactive environments. For pipelines and CI:

1. Provide all configuration through environment variables rather than flags.
2. Provide the provider API key as a secret.
3. Decide your code-execution strategy up front (see the next section): either no code execution,
   or the sandboxed executor. Do **not** rely on the host REPL in automation.

Example one-shot in CI:

```bash
export OPENAI_API_KEY="$OPENAI_API_KEY_SECRET"
par_gpt llm "generate a release notes draft from the last commit" > notes.md
```

For agent runs that must execute code without prompts, start the sandbox first and combine
`--code-sandbox` with `--yes-to-all`:

```bash
par_gpt sandbox -a start
par_gpt --code-sandbox -y agent "refactor utils.py and verify the tests still pass"
```

`--yes-to-all` auto-accepts ordinary security warnings so the run does not block on
confirmations; combined with `--code-sandbox`, code runs in the container with no per-execution
prompt.

## The PARGPT_YES_TO_ALL automation pattern

`--yes-to-all` (env: `PARGPT_YES_TO_ALL=1`) auto-accepts security warnings and confirmation
prompts so the tool can run unattended. There is one deliberate exception you must understand for
automation:

> **`--yes-to-all` does NOT bypass the host Python REPL execution confirmation.**

Running `exec()` on AI-generated code on the host is irreversible and is reachable through prompt
injection (fetched URLs, search results). After the SEC-001 fix, the host REPL
(`--repl`) always prompts before executing, even under `--yes-to-all`. PAR GPT prints a warning
to make this explicit:

```text
Security: --yes-to-all is not applied to the host Python REPL (--repl);
execution confirmation stays enabled. Use --code-sandbox for unsupervised code execution.
```

**Automation-safe path:** use the sandboxed `execute_code` tool (`--code-sandbox`) instead of the
host REPL. The sandbox tool does not prompt per execution and runs code inside the Docker
container, which is the correct choice for CI and any unsupervised run.

```bash
# Persistent automation settings via environment
export PARGPT_YES_TO_ALL=1
export PARGPT_CODE_SANDBOX=1
export PARGPT_AI_PROVIDER=openai

par_gpt agent "..."
```

If your workload does not need code execution at all, simply omit both `--repl` and
`--code-sandbox` — nothing will prompt to execute code.

## Environment-variable summary

| Variable | Type | Default | Purpose |
| --- | --- | --- | --- |
| `PARGPT_AI_PROVIDER` | string | provider default | Active provider |
| `PARGPT_YES_TO_ALL` | flag | off | Auto-accept security warnings (not host REPL) |
| `PARGPT_CODE_SANDBOX` | flag | off | Enable the sandboxed `execute_code` tool |
| `PARGPT_ENABLE_REDIS` | flag | off | Enable Redis-backed memory |
| `PARGPT_REDIS_HOST` | string | `localhost` | Redis host |
| `PARGPT_REDIS_PORT` | integer | `6379` | Redis port |
| `PARGPT_REDIS_DB` | integer | `0` | Redis database number |

Provider keys (for example `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`) are read
directly by the selected provider. See the README for the full option list.

## Related Documentation

- [Troubleshooting](../troubleshooting.md) - common failure modes and fixes
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - security architecture and module layout
- [README.md](../../README.md) - installation and full option reference
