# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

IMPORTANT: Ensure you've thoroughly reviewed the [AGENTS.md](AGENTS.md) file before beginning any work.

## Development Commands

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run ty check

# Run tests
uv run pytest

# Run single test
uv run pytest tests/path/to/test.py::test_function

# Run tests with specific marker
uv run pytest -m contract
uv run pytest -m live

# Start the proxy server
uv run uvicorn server:app --host 0.0.0.0 --port 8082

# Run smoke tests (requires FCC_LIVE_SMOKE=1)
FCC_LIVE_SMOKE=1 uv run pytest smoke -n 0 -s --tb=short
```

Run checks in this order before pushing: `uv run ruff format`, `uv run ruff check`, `uv run ty check`, `uv run pytest`.

## Architecture Overview

This is an Anthropic-compatible proxy that routes Claude Code API traffic to multiple providers (NVIDIA NIM, OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama, Kimi).

### Dependency Direction

```
config → api, providers, messaging
core.anthropic → api, providers, messaging
providers → api
api → cli, messaging
cli → messaging
```

### Package Structure

- `api/` - FastAPI routes, services, model routing, optimizations, web tools
- `providers/` - Provider adapters, registry, rate limiting, error mapping
- `messaging/` - Discord/Telegram adapters, sessions, voice, tree-based queuing
- `cli/` - Package entrypoints and Claude CLI subprocess management
- `config/` - Settings, provider catalog, logging, constants
- `core/anthropic/` - Shared Anthropic protocol helpers (SSE, conversion, tools, thinking)
- `ui/` - Admin UI with dashboard, providers, models, routing, settings, logs, system, health, diagnostics, CLI, docs
- `smoke/` - E2E smoke tests (prereq and product scenarios)
- `tests/` - Unit and contract tests

### Key Components

**API Layer** (`api/`):
- `app.py` - FastAPI application factory with graceful lifespan failure reporting
- `runtime.py` - Application runtime composition and lifecycle ownership
- `routes.py` - FastAPI route handlers (`/v1/messages`, `/v1/models`, `/v1/messages/count_tokens`)
- `services.py` - Request optimization, model routing, token count, provider coordination
- `model_router.py` - Resolves incoming Claude model names to configured provider/model pairs
- `dependencies.py` - Dependency injection for FastAPI (provider resolution, auth)
- `optimization_handlers.py` - Fast-path API responses (quota checks, title generation, prefix detection)
- `web_tools/` - Local web_search/web_fetch handling with SSRF guard

**Provider Layer** (`providers/`):
- `registry.py` - Provider descriptors, factory, and runtime registry
- `base.py` - Base provider interface (`BaseProvider`, `ProviderConfig`)
- `openai_compat.py` - OpenAI-style chat base for NIM and similar providers
- `anthropic_messages.py` - Shared transport for native Anthropic Messages endpoints
- `nvidia_nim/`, `open_router/`, `deepseek/`, `lmstudio/`, `llamacpp/`, `ollama/`, `kimi/` - Provider implementations

**Core Protocol** (`core/anthropic/`):
- `sse.py` - SSE event builder for Anthropic-format streaming responses
- `conversion.py` - Message and tool format converters (Anthropic ↔ OpenAI)
- `stream_contracts.py` - Neutral SSE parsing and Anthropic stream shape assertions
- `thinking.py` - Think tag parser for reasoning content
- `tools.py` - Heuristic tool parser for OpenAI-style tool calls
- `tokens.py` - Token estimation utilities

**Messaging Layer** (`messaging/`):
- `handler.py` - Platform-agnostic Claude interaction logic
- `platforms/base.py` - Abstract base class for messaging platforms
- `platforms/discord.py` - Discord platform adapter
- `platforms/telegram.py` - Telegram platform adapter
- `session.py` - Persistent storage for message ↔ Claude session mappings
- `trees/queue_manager.py` - Tree-based message queue for conversation branches
- `voice.py` - Platform-neutral voice note helpers
- `transcription.py` - Voice note transcription (local Whisper or NVIDIA NIM)

**CLI Layer** (`cli/`):
- `manager.py` - Manages multiple CLISession instances for parallel conversations
- `session.py` - Manages a single persistent Claude Code CLI subprocess
- `entrypoints.py` - CLI entry points (`free-claude-code`, `fcc-init`)

**Configuration** (`config/`):
- `settings.py` - Centralized configuration using Pydantic Settings
- `provider_catalog.py` - Neutral provider catalog (IDs, credentials, defaults, capabilities)
- `nim.py` - Fixed NVIDIA NIM settings (temperature, top_p, etc.)
- `logging_config.py` - Loguru-based structured logging configuration

**Admin UI** (`ui/`):
- `routes/` - Admin routes for dashboard, providers, models, routing, settings, logs, system, health, diagnostics, CLI, docs
- `templates/` - Jinja2 templates with HTMX for interactivity and Tailwind CSS for styling
- `auth.py` - Basic authentication with bcrypt password hashing

## Architecture Principles

- **Shared utilities**: Put shared Anthropic protocol logic in neutral `core/anthropic/` modules
- **DRY**: Extract shared base classes to eliminate duplication
- **Encapsulation**: Use accessor methods for internal state (e.g., `set_current_task()`)
- **Provider-specific config**: Keep provider-specific fields in provider constructors
- **No type ignores**: Fix the underlying type issue instead of using `# type: ignore`
- **Complete migrations**: When moving modules, update imports to the new owner and remove old compatibility shims
- **Maximum test coverage**: Add tests for new changes, including edge cases

## Import Boundaries

- `api/` may only import `providers`, `providers.base`, `providers.exceptions`, and `providers.registry` from the providers package
- `core/` stays free of `api`, `messaging`, `cli`, `providers`, `config`, and `smoke`
- `messaging/` does not import `api`, `cli`, or `smoke`, and may import `providers` only via `providers.nvidia_nim.voice`
- `config/` does not import non-config packages

## Provider Registration

To add a new provider:

1. Add provider descriptor to `config.provider_catalog.PROVIDER_CATALOG`
2. Create provider module in `providers/` extending `BaseProvider` or `OpenAIChatTransport`/`AnthropicMessagesTransport`
3. Add factory function to `providers.registry.PROVIDER_FACTORIES`
4. Update `SUPPORTED_PROVIDER_IDS` in `config.provider_catalog`

## Smoke Tests

Smoke tests are local-only and can launch subprocesses, call real providers, and touch local model servers. They are enabled with `FCC_LIVE_SMOKE=1`.

- `smoke/prereq/` - Liveness checks (server, routes, auth, CLI scripts, provider pings)
- `smoke/product/` - End-to-end product scenarios
- `smoke/features.py` - Source-of-truth feature map

Run smoke tests with:
```bash
FCC_LIVE_SMOKE=1 uv run pytest smoke -n 0 -s --tb=short
```

## Environment Variables

See `.env.example` for the canonical list. Key variables:

- `MODEL`, `MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU` - Model routing
- `NVIDIA_NIM_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `KIMI_API_KEY` - Provider credentials
- `ANTHROPIC_AUTH_TOKEN` - Optional server API key
- `MESSAGING_PLATFORM` - "discord" | "telegram" | "none"
- `ENABLE_WEB_SERVER_TOOLS` - Local web_search/web_fetch handling
- `ENABLE_ADMIN_UI` - Enable admin UI at `/admin/`
- `ADMIN_USER`, `ADMIN_PASSWORD_HASH` - Admin UI credentials

## Testing

- Unit tests live in `tests/`
- Contract tests enforce import boundaries and stream contracts
- Smoke tests live in `smoke/` and require `FCC_LIVE_SMOKE=1`
- Use `uv run pytest` to run tests
- Use `uv run pytest smoke -n 0 -s --tb=short` for smoke tests

Test markers:
- `live` - Opt-in local smoke tests that can touch real services
- `interactive` - Smoke tests requiring manual user interaction
- `provider` - Live provider checks
- `messaging` - Live messaging platform checks
- `cli` - CLI integration checks
- `clients` - Client compatibility checks
- `voice` - Voice transcription checks
- `contract` - Deterministic feature contract checks

## Important Notes

- Always use `uv run` to run files instead of the global `python` command
- Current uv ruff formatter is set to py314 which supports multiple exception types without parentheses
- All CI checks must pass; failing checks block merge
- Do not add `# type: ignore` or `# ty: ignore`; fix the underlying type issue
- The syntax `except X, Y:` is supported in Python 3.14 final version
- Admin UI uses HTMX for interactivity and Tailwind CSS via CDN for styling
- Admin UI authentication uses basic auth with bcrypt password hashing
- Admin UI routes are prefixed with `/admin/` and require authentication

## Troubleshooting

### Claude Code says `undefined ... input_tokens`, `$.speed`, or malformed response

Update to the latest commit first. Then check:
- `ANTHROPIC_BASE_URL` is `http://localhost:8082`, not `http://localhost:8082/v1`
- The proxy is returning Server-Sent Events for `/v1/messages`
- `server.log` contains no upstream 400/500 response before the malformed-response error

### llama.cpp or LM Studio returns HTTP 400

This usually means the local runtime rejected the Anthropic Messages request before the proxy could stream a model answer. Check:
- The local server supports `POST /v1/messages`
- The model and runtime support the requested context length and tools
- llama.cpp was started with enough `--ctx-size` for Claude Code prompts
- The configured base URL includes `/v1` for LM Studio and llama.cpp

### Provider disconnects during streaming

Errors like `incomplete chunked read`, `server disconnected`, or a peer closing the body usually come from the upstream provider or gateway. Reduce concurrency, raise timeouts, or retry later.

### Tool calls work on one model but not another

Tool support is model and provider dependent. Some OpenAI-compatible models emit malformed tool-call deltas, omit tool names, or return tool calls as plain text. Try another model or provider before assuming the proxy is broken.
