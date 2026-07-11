# Troubleshooting

Common failure modes for PAR GPT, organized as **Symptom / Cause / Fix / Verify**. For
deployment and operational setup (sandbox lifecycle, Redis, headless/CI), see
[Deployment Guide](guides/deployment.md).

## Table of Contents

- [Redis connection failures](#redis-connection-failures)
- [Missing ffmpeg (image / audio features)](#missing-ffmpeg-image--audio-features)
- [Docker code sandbox setup](#docker-code-sandbox-setup)
- [Pydantic v1 warning on Python 3.14+](#pydantic-v1-warning-on-python-314)
- [Provider API-key errors](#provider-api-key-errors)
- [--yes-to-all does not skip code execution prompts](#--yes-to-all-does-not-skip-code-execution-prompts)

## Redis connection failures

**Symptom:** Errors mentioning Redis, or the agent has no `ai_memory_db` tool, even though you
expected memory features.

**Cause:** Redis-backed memory is **disabled by default**. It only activates when you pass
`--enable-redis` (or set `PARGPT_ENABLE_REDIS=1`), and it then needs a reachable Redis server.
When enabled and unreachable, you see connection errors; when not enabled at all, the memory
tool is simply absent (this is graceful, not an error).

**Fix:**

1. Confirm Redis is enabled intentionally:

   ```bash
   par_gpt --enable-redis llm "hello"
   ```

2. Ensure a Redis server is running and the connection settings are correct. Defaults are
   `localhost:6379`, database `0`:

   | Variable | Default | Purpose |
   | --- | --- | --- |
   | `PARGPT_REDIS_HOST` | `localhost` | Redis host |
   | `PARGPT_REDIS_PORT` | `6379` | Redis port |
   | `PARGPT_REDIS_DB` | `0` | Redis database number |
   | `PARGPT_ENABLE_REDIS` | unset (off) | Set `1` to enable memory |

3. If you do not need memory, drop `--enable-redis` / unset `PARGPT_ENABLE_REDIS` and the
   connection attempt goes away entirely.

**Verify:**

```bash
redis-cli -h localhost -p 6379 ping
```

Expected result: `PONG`. Then run `par_gpt --enable-redis llm "remember I like tea"` and confirm
no Redis error is printed.

## Missing ffmpeg (image / audio features)

**Symptom:** Image or audio features (TTS, audio playback, some media tools) fail with a message
about a missing codec or `ffmpeg`/`ffprobe` not found.

**Cause:** Several media operations depend on `ffmpeg`, which is not installed by PAR GPT.

**Fix:** Install ffmpeg for your platform.

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt update && sudo apt install ffmpeg

# Arch
sudo pacman -S ffmpeg

# Windows (Chocolatey)
choco install ffmpeg

# Windows (Scoop)
scoop install ffmpeg
```

**Verify:**

```bash
ffmpeg -version
```

Expected result: a version string is printed.

## Docker code sandbox setup

**Symptom:** `par_gpt --code-sandbox agent "..."` reports that the sandbox container is not
running, or the `execute_code` tool is unavailable.

**Cause:** The code sandbox is a separate Docker container you must build and start before using
`--code-sandbox`. The host Python REPL (`--repl`) and the sandboxed executor are mutually
exclusive — if the REPL is enabled, the sandbox tool is not loaded.

**Fix:** Build and start the sandbox.

```bash
# Either via the Makefile target
make sandbox

# Or via the CLI
par_gpt sandbox -a build
par_gpt sandbox -a start
```

Stop or rebuild it as needed:

```bash
par_gpt sandbox -a stop
par_gpt sandbox -a build   # rebuild after Dockerfile changes
```

**Verify:**

```bash
par_gpt sandbox -a start
```

Expected result: a running `par_gpt_sandbox` container. Then:

```bash
par_gpt --code-sandbox agent "write and run a python one-liner that prints 42"
```

Expected result: the agent executes code in the container and returns output.

## Pydantic v1 warning on Python 3.14+

**Symptom:** On Python 3.14, you previously saw:

```text
UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater
```

**Cause:** LangChain's internal `pydantic.v1` imports trigger this warning on Python 3.14. This is
a known upstream issue (langchain-ai/langchain#33926) pending Pydantic 2.13.

**Fix:** No action required. PAR GPT filters this specific warning at the application entry point
(`src/par_gpt/__main__.py`) using `warnings.filterwarnings(...)`, so it is suppressed
automatically. If you import `par_gpt` as a library and still see it, call the CLI entry point
rather than importing internals, or apply the same filter in your own entry point.

**Verify:** Run any command — the warning no longer appears in the output.

## Provider API-key errors

**Symptom:** A message that the provider API key is missing, empty, or unauthorized when running
`llm` or `agent` commands.

**Cause:** The selected provider (`--ai-provider`, default from `PARGPT_AI_PROVIDER`) requires its
API key environment variable, and PAR GPT validates the key at startup.

**Fix:**

1. Set the key your provider expects (for example `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
   `GROQ_API_KEY`). Keys can be exported in the shell or placed in `~/.par_gpt.env`.

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

2. Confirm the active provider matches the key you set:

   ```bash
   par_gpt -a openai llm "hello"
   ```

**Verify:** The command returns a response instead of an authentication error.

## --yes-to-all does not skip code execution prompts

**Symptom:** You run with `--yes-to-all` (`-y`) and the host Python REPL (`--repl`) still prompts
for confirmation before executing code, printing:

```text
Security: --yes-to-all is not applied to the host Python REPL (--repl);
execution confirmation stays enabled. Use --code-sandbox for unsupervised code execution.
```

**Cause:** This is intentional. As of the SEC-001 fix, `--yes-to-all` no longer bypasses the
confirmation for host `exec()` of AI-generated code, because that path is irreversible and
reachable through prompt injection (fetched URLs, search results). `--yes-to-all` still
auto-accepts other security warnings.

**Fix:** For unsupervised / automated code execution, use the sandboxed executor instead of the
host REPL:

```bash
# Start the sandbox once (see "Docker code sandbox setup" above)
par_gpt sandbox -a start

# Run without prompts; code runs inside the container
par_gpt --code-sandbox -y agent "..."
```

The sandboxed `execute_code` tool and the host REPL (`--repl`) are never both loaded — enabling
the REPL disables the sandbox tool.

**Verify:** With `--code-sandbox`, the agent writes and runs code with no per-execution
confirmation prompt.

## Related Documentation

- [Deployment Guide](guides/deployment.md) - sandbox lifecycle, Redis setup, headless/CI usage
- [ARCHITECTURE.md](../ARCHITECTURE.md) - module layout and security architecture
- [README.md](../README.md) - installation and full option reference
