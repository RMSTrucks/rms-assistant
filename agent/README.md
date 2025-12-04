# RMS Assistant - Python Agent

AI agent backend for the RMS Assistant Chrome extension. Powered by Claude (Anthropic) via the Agno framework.

## Quick Start

```bash
cd agent

# Install dependencies
uv sync

# Copy environment file and add your API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and LANGWATCH_API_KEY

# Start the WebSocket server
uv run python -m app.server
```

The server will start on `ws://localhost:8765` - the Chrome extension will auto-connect.

## Architecture

```
Chrome Extension (Side Panel)     Python Agent Server
+---------------------------+     +---------------------------+
| Chat UI                   |     | FastAPI + WebSocket       |
| - Message history         |<--->| - ws://localhost:8765     |
| - Streaming responses     |     | - Session management      |
+---------------------------+     +---------------------------+
            |                               |
            v                               v
+---------------------------+     +---------------------------+
| Service Worker            |     | Agno Agent + Claude       |
| - WebSocket client        |     | - Tool execution          |
| - Browser actions         |     | - Streaming responses     |
+---------------------------+     +---------------------------+
```

## Available Tools

| Tool | Description |
|------|-------------|
| `lookup_dot_number` | Look up carrier info from FMCSA |
| `search_carriers` | Search carriers by name |
| `check_safety_rating` | Get BASIC scores and safety info |
| `add_note_to_lead` | Add notes to Close CRM leads |
| `create_lead` | Create new leads in Close CRM |
| `search_leads` | Search existing leads |
| `search_insured` | Search NowCerts insureds |
| `get_policy_details` | Get policy information |
| `get_process_info` | Get insurance process documentation |
| `navigate_to_url` | Navigate browser to URL |
| `click_element` | Click page elements |
| `fill_form_field` | Fill form fields |

## WebSocket Protocol

**Extension -> Agent:**
```json
{"type": "message", "content": "Look up DOT 1234567", "tabState": {...}}
{"type": "action_response", "actionId": "...", "approved": true}
```

**Agent -> Extension:**
```json
{"type": "response_start"}
{"type": "response_chunk", "content": "..."}
{"type": "response_end"}
{"type": "browser_action", "action": "navigate", "url": "..."}
{"type": "action_request", "actionId": "...", "action": "click", ...}
```

## Development

### Running Tests

```bash
uv run pytest tests/scenarios/ -v
```

### CLI Mode (without extension)

```bash
uv run python -m app.main "Look up DOT 1234567"
```

### Interactive CLI

```bash
uv run python -m app.main
```

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required
LANGWATCH_API_KEY=...          # Required for tracing
CLOSE_API_KEY=...              # Optional - Close CRM
NOWCERTS_API_KEY=...           # Optional - NowCerts
```

## Files

| File | Purpose |
|------|---------|
| `app/server.py` | WebSocket server (FastAPI) |
| `app/agent.py` | Agent configuration and execution |
| `app/main.py` | CLI entry point |
| `app/tools/` | Tool implementations |
| `prompts/` | System prompts (YAML) |
| `tests/scenarios/` | Scenario tests |

See [AGENTS.md](AGENTS.md) for development guidelines.
