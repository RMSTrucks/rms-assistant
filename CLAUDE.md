# RMS Work Assistant - Chrome Extension

AI-powered work assistant that lives in a Chrome browser side panel. Chat interface for delegating tasks, controlling the browser, and integrating with work systems.

## Architecture

```
Chrome Extension (Side Panel)     Python Agent Server
+---------------------------+     +---------------------------+
| Chat UI                   |     | FastAPI + WebSocket       |
| - Message history         |<--->| - Session management      |
| - Action confirmations    |     | - Streaming responses     |
| - Tab state display       |     +---------------------------+
+---------------------------+               |
            |                               v
            v                     +---------------------------+
+---------------------------+     | Agno Agent                |
| Service Worker            |     | - Claude reasoning        |
| - WebSocket client        |     | - Conversation memory     |
| - Tab management          |     | - Tool execution          |
| - Screenshot capture      |     +---------------------------+
+---------------------------+               |
            |                               v
            v                     +---------------------------+
+---------------------------+     | MCP Tools                 |
| Content Scripts           |     | - browser_tools (proxy)   |
| - DOM interaction         |     | - close_crm (MCP)         |
| - Form filling            |     | - nowcerts (MCP)          |
| - Page state extraction   |     +---------------------------+
+---------------------------+
```

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension config (MV3), permissions, content scripts |
| `sidepanel/sidepanel.html` | Chat UI layout |
| `sidepanel/sidepanel.js` | Chat logic, streaming, actions, WebSocket |
| `sidepanel/sidepanel.css` | Chat styling |
| `background/service-worker.js` | WebSocket client, message routing, browser actions |
| `content/browser-tools.js` | DOM interaction, page state extraction |

## WebSocket Protocol

**Extension -> Agent:**
```json
{"type": "message", "content": "...", "tabState": {...}}
{"type": "action_response", "actionId": "...", "approved": true}
{"type": "tab_state", "tab": {...}}
```

**Agent -> Extension:**
```json
{"type": "response_start"}
{"type": "response_chunk", "content": "..."}
{"type": "response_end"}
{"type": "tool_call", "tool": "...", "args": {...}}
{"type": "tool_result", "result": {...}}
{"type": "action_request", "actionId": "...", "action": "click", "target": "..."}
{"type": "browser_action", "action": "navigate|screenshot|fill|click", ...}
```

## Features

### Chat Interface
- Message history with persistence
- Streaming word-by-word responses
- User/assistant message bubbles
- Markdown formatting support
- Thinking indicator

### Action Confirmations
- Modal overlay for sensitive actions
- Allow/Deny buttons
- Agent asks before clicking submit buttons, etc.

### Browser Tools
- Navigate to URLs
- Capture screenshots
- Get page state (forms, buttons, text)
- Fill form fields (ExtJS compatible)
- Click elements
- Select dropdowns and radio buttons

### Tab Awareness
- Tracks active tab
- Shows current page in UI
- Sends tab context with messages

## Development

1. Load unpacked extension:
   - Open `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select this folder

2. Test without server:
   - Extension has mock response mode
   - Messages show simulated streaming

3. Test with agent server:
   - Start Python agent on `ws://localhost:8765`
   - Extension auto-connects

## TODO

- [ ] Add placeholder icons (16, 48, 128 px)
- [ ] Connect to Python agent server (Better Agents)
- [ ] Add MCP tool integrations (Close CRM, NowCerts)
- [ ] Screenshot viewing in chat
- [ ] Message search/history

## Related Projects

- **Python Agent Server:** To be created via Better Agents
- **Close CRM MCP:** `C:\Users\Jake\WorkProjects\Close-CRM-MCP`
- **NowCerts MCP:** `C:\Users\Jake\WorkProjects\NowCerts-MCP`
- **Insurance Quote Extension (legacy):** `C:\Users\Jake\Jake-Workspaces\insurance-quote-extension`
