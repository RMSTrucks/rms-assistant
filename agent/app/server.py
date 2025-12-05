"""
WebSocket Server for RMS Assistant Chrome Extension

Handles:
- WebSocket connections from the Chrome extension
- Message routing between extension and agent
- Streaming responses
- Browser action requests
"""

import asyncio
import json
import os
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import langwatch
from app.agent import get_agent
from app.conversation_logger import get_logger
from app.tools.browser import get_pending_action, deliver_action_result

# Load environment variables
load_dotenv()

# Initialize LangWatch
langwatch.api_key = os.getenv("LANGWATCH_API_KEY")


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.pending_actions: dict[str, asyncio.Future] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[Server] Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[Server] Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

    def create_action_request(self, action_id: str) -> asyncio.Future:
        """Create a future for an action that needs user approval."""
        future = asyncio.get_event_loop().create_future()
        self.pending_actions[action_id] = future
        return future

    def resolve_action(self, action_id: str, approved: bool):
        """Resolve a pending action request."""
        if action_id in self.pending_actions:
            future = self.pending_actions.pop(action_id)
            if not future.done():
                future.set_result(approved)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("[Server] Starting RMS Assistant Agent Server...")
    print("[Server] WebSocket endpoint: ws://localhost:8765/ws")
    yield
    print("[Server] Shutting down...")


app = FastAPI(
    title="RMS Assistant Agent Server",
    description="WebSocket server for Chrome extension communication",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BrowserTools:
    """
    Tools that execute browser actions via the Chrome extension.

    These are callable from the agent and send requests to the extension.
    """

    def __init__(self, websocket: WebSocket, manager: ConnectionManager):
        self.websocket = websocket
        self.manager = manager

    async def navigate(self, url: str) -> dict:
        """Navigate the browser to a URL."""
        action_id = str(uuid.uuid4())
        await self.manager.send_json(self.websocket, {
            "type": "browser_action",
            "actionId": action_id,
            "action": "navigate",
            "url": url
        })
        # Wait for result (with timeout)
        # For now, return immediately - extension will send result back
        return {"status": "requested", "action": "navigate", "url": url}

    async def screenshot(self) -> dict:
        """Capture a screenshot of the current tab."""
        action_id = str(uuid.uuid4())
        await self.manager.send_json(self.websocket, {
            "type": "browser_action",
            "actionId": action_id,
            "action": "screenshot"
        })
        return {"status": "requested", "action": "screenshot"}

    async def get_page_state(self) -> dict:
        """Get the current page state (forms, buttons, etc.)."""
        action_id = str(uuid.uuid4())
        await self.manager.send_json(self.websocket, {
            "type": "browser_action",
            "actionId": action_id,
            "action": "get_page_state"
        })
        return {"status": "requested", "action": "get_page_state"}

    async def click(self, selector: str) -> dict:
        """Click an element on the page."""
        action_id = str(uuid.uuid4())
        await self.manager.send_json(self.websocket, {
            "type": "browser_action",
            "actionId": action_id,
            "action": "click",
            "selector": selector
        })
        return {"status": "requested", "action": "click", "selector": selector}

    async def fill(self, selector: str, value: str) -> dict:
        """Fill a form field."""
        action_id = str(uuid.uuid4())
        await self.manager.send_json(self.websocket, {
            "type": "browser_action",
            "actionId": action_id,
            "action": "fill",
            "selector": selector,
            "value": value
        })
        return {"status": "requested", "action": "fill", "selector": selector}

    async def request_action_approval(
        self, action: str, target: str, description: str
    ) -> bool:
        """
        Request user approval for a sensitive action.

        Returns True if approved, False if denied.
        """
        action_id = str(uuid.uuid4())

        # Create future for response
        future = self.manager.create_action_request(action_id)

        # Send action request to extension
        await self.manager.send_json(self.websocket, {
            "type": "action_request",
            "actionId": action_id,
            "action": action,
            "target": target,
            "description": description
        })

        try:
            # Wait for user response (30 second timeout)
            approved = await asyncio.wait_for(future, timeout=30.0)
            return approved
        except asyncio.TimeoutError:
            return False


@langwatch.trace()
async def process_message(
    websocket: WebSocket,
    message: str,
    tab_state: Optional[dict] = None,
    files: Optional[list] = None,
    logger = None
) -> None:
    """
    Process a user message and stream the response.

    Args:
        websocket: The WebSocket connection
        message: User's message
        tab_state: Current browser tab state
        files: Optional list of file attachments (base64 encoded)
        logger: ConversationLogger instance for recording
    """
    # Update trace with input
    trace = langwatch.get_current_trace()
    if trace:
        trace.update(input=message)

    # Signal response starting
    await manager.send_json(websocket, {"type": "response_start"})

    full_response = ""  # Collect full response for logging

    try:
        # Get the agent
        agent = get_agent()

        # Build context with tab state if available
        context_message = message
        if tab_state:
            context_message = f"[Current tab: {tab_state.get('title', 'Unknown')} - {tab_state.get('url', 'Unknown')}]\n\n{message}"

        # Handle file attachments for Claude Vision
        images = []
        if files:
            for f in files:
                # Extract base64 data (remove data:mimetype;base64, prefix if present)
                base64_data = f.get("base64", "")
                if ";base64," in base64_data:
                    base64_data = base64_data.split(";base64,")[1]

                mime_type = f.get("mimeType", "image/png")
                file_name = f.get("name", "file")

                # For PDFs, add context about the file
                if mime_type == "application/pdf":
                    context_message = f"[Attached PDF: {file_name}]\n\n{context_message}"
                    # Note: For PDF support, you'd convert PDF pages to images
                    # For now, pass as image and let Claude try to handle it
                    images.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_data
                        }
                    })
                else:
                    # Image files
                    context_message = f"[Attached image: {file_name}]\n\n{context_message}"
                    images.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_data
                        }
                    })

        # Run agent in thread pool to avoid blocking the event loop
        # This is critical because browser tools need the event loop to process
        # WebSocket messages while they wait for results
        def run_agent():
            if images:
                # For multimodal, we need to use the model directly with image content
                # Agno Agent doesn't natively support images, so we call the model
                from anthropic import Anthropic
                client = Anthropic()

                # Build multimodal message content
                content = []
                for img in images:
                    content.append(img)
                content.append({"type": "text", "text": context_message})

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": content}]
                )
                # Return a simple object with content attribute
                class SimpleResponse:
                    def __init__(self, text):
                        self.content = text
                return SimpleResponse(response.content[0].text)
            else:
                return agent.run(context_message)

        response = await asyncio.get_event_loop().run_in_executor(None, run_agent)
        content = str(response.content)
        full_response = content  # Store for logging

        # Send response in chunks for streaming effect (faster than word-by-word)
        chunk_size = 5  # words per chunk
        words = content.split()
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            await manager.send_json(websocket, {
                "type": "response_chunk",
                "content": chunk
            })
            await asyncio.sleep(0.01)  # 10ms between chunks

    except Exception as e:
        error_msg = str(e)
        await manager.send_json(websocket, {
            "type": "error",
            "message": error_msg
        })
        # Log the error
        if logger:
            logger.log_error(error_msg, context={"message": message})

    finally:
        # Signal response complete
        await manager.send_json(websocket, {"type": "response_end"})

        # Update trace with output
        trace = langwatch.get_current_trace()
        if trace and full_response:
            trace.update(output=full_response)

        # Log assistant response
        if logger and full_response:
            logger.log_message(
                role="assistant",
                content=full_response,
                tab_state=tab_state
            )


async def run_carrier_quote(
    websocket: WebSocket,
    carrier: str,
    tab_id: int,
    quote_data: dict,
    config: dict
):
    """
    Run carrier quote automation as a background task.

    Args:
        websocket: WebSocket connection to send progress updates
        carrier: Carrier name (progressive, bhhc, geico, jmwilson)
        tab_id: Browser tab ID where carrier portal is open
        quote_data: Quote form data from sidepanel
        config: Carrier config (loginUrl, homeUrl, etc.)
    """
    try:
        # Send initial status
        await manager.send_json(websocket, {
            "type": "carrier_quote_progress",
            "carrier": carrier,
            "status": "Waiting for login...",
            "tabId": tab_id
        })

        if carrier == "progressive":
            from app.carriers.progressive import run_progressive_quote
            await run_progressive_quote(websocket, manager, tab_id, quote_data, config)
        else:
            await manager.send_json(websocket, {
                "type": "carrier_quote_progress",
                "carrier": carrier,
                "status": f"Automation not yet implemented for {carrier}",
                "tabId": tab_id
            })

    except Exception as e:
        print(f"[Server] Carrier quote error: {e}")
        await manager.send_json(websocket, {
            "type": "carrier_quote_progress",
            "carrier": carrier,
            "status": f"Error: {str(e)}",
            "tabId": tab_id
        })


async def browser_action_dispatcher(websocket: WebSocket):
    """
    Background task that monitors the action queue and sends to extension.

    This bridges the sync agent tools with the async WebSocket.
    """
    while True:
        try:
            action = get_pending_action()
            if action:
                action_id = action.get("action_id")
                action_type = action.get("action")
                print(f"[Server] Dispatching browser action: {action_type} (id={action_id[:8]}...)")

                # Build the message for the extension
                # Pass through all parameters from the action
                msg = {
                    "type": "browser_action",
                    "actionId": action_id,
                    "action": action_type,
                }

                # Add all other parameters from the action
                for key, value in action.items():
                    if key not in ("action_id", "action"):
                        msg[key] = value

                await manager.send_json(websocket, msg)

            # Small delay to prevent busy-waiting
            await asyncio.sleep(0.05)

        except Exception as e:
            print(f"[Server] Action dispatcher error: {e}")
            await asyncio.sleep(1)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for Chrome extension."""
    await manager.connect(websocket)

    # Start conversation logging session
    logger = get_logger()
    session_id = logger.start_session(metadata={"source": "chrome_extension"})

    # Start background task to dispatch browser actions
    dispatcher_task = asyncio.create_task(browser_action_dispatcher(websocket))

    try:
        while True:
            # Receive message from extension
            data = await websocket.receive_json()
            print(f"[Server] Received: {data.get('type', 'unknown')}")

            msg_type = data.get("type")

            if msg_type == "message":
                # User sent a chat message
                content = data.get("content", "")
                tab_state = data.get("tabState")
                files = data.get("files")  # Optional file attachments

                # Log user message
                log_content = content
                if files:
                    file_names = [f.get("name", "file") for f in files]
                    log_content = f"{content}\n[Attached: {', '.join(file_names)}]"

                logger.log_message(
                    role="user",
                    content=log_content,
                    tab_state=tab_state
                )

                await process_message(websocket, content, tab_state, files, logger)

            elif msg_type == "action_response":
                # User responded to an action request
                action_id = data.get("actionId")
                approved = data.get("approved", False)
                manager.resolve_action(action_id, approved)

            elif msg_type == "browser_action_result":
                # Result from a browser action we requested
                action_id = data.get("actionId")
                result = data.get("result", {})
                print(f"[Server] Browser action result: {action_id[:8] if action_id else '?'}...")

                # Deliver result back to the waiting tool
                if action_id:
                    deliver_action_result(action_id, result)

            elif msg_type == "tab_state":
                # Tab state update (informational)
                tab = data.get("tab", {})
                print(f"[Server] Tab state: {tab.get('title', 'Unknown')}")

            elif msg_type == "get_lead_for_quote":
                # Fetch lead data for quote form pre-fill
                lead_id = data.get("leadId")
                if lead_id:
                    print(f"[Server] Fetching lead for quote: {lead_id[:20]}...")
                    try:
                        from app.tools.close_crm import CloseCRMTools
                        close_tools = CloseCRMTools()
                        lead_data = close_tools.get_lead(lead_id)
                        await manager.send_json(websocket, {
                            "type": "lead_data_for_quote",
                            "lead": lead_data
                        })
                    except Exception as e:
                        print(f"[Server] Error fetching lead: {e}")
                        await manager.send_json(websocket, {
                            "type": "lead_data_for_quote",
                            "error": str(e)
                        })

            elif msg_type == "save_quote_note":
                # Save quote data as note to Close lead
                lead_id = data.get("leadId")
                note = data.get("note")
                if lead_id and note:
                    print(f"[Server] Saving quote note to lead: {lead_id[:20]}...")
                    try:
                        from app.tools.close_crm import CloseCRMTools
                        close_tools = CloseCRMTools()
                        result = close_tools.add_note_to_lead(lead_id, note)
                        await manager.send_json(websocket, {
                            "type": "quote_note_saved",
                            "leadId": lead_id,
                            "success": True
                        })
                    except Exception as e:
                        print(f"[Server] Error saving note: {e}")
                        await manager.send_json(websocket, {
                            "type": "quote_note_saved",
                            "leadId": lead_id,
                            "success": False,
                            "error": str(e)
                        })

            elif msg_type == "start_carrier_quote":
                # Start carrier quote automation in background
                carrier = data.get("carrier")
                tab_id = data.get("tabId")
                quote_data = data.get("quoteData", {})
                config = data.get("config", {})

                print(f"[Server] Starting {carrier} quote automation (tab {tab_id})")

                # Run carrier automation as background task
                asyncio.create_task(
                    run_carrier_quote(websocket, carrier, tab_id, quote_data, config)
                )

    except WebSocketDisconnect:
        dispatcher_task.cancel()
        logger.end_session()
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[Server] Error: {e}")
        dispatcher_task.cancel()
        logger.end_session(summary=f"Error: {e}")
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": len(manager.active_connections)
    }


# =========================================================================
# Debug API Endpoints (for Claude to query during iteration)
# =========================================================================

@app.get("/debug/recent-events")
async def debug_recent_events(limit: int = 50):
    """
    Get recent events from the current session.

    Claude can query this to see what happened:
    - WebFetch http://localhost:8765/debug/recent-events?limit=20
    """
    logger = get_logger()
    if logger.current_session_file and logger.current_session_file.exists():
        events = logger.read_session(
            str(logger.current_session_file.relative_to(logger.storage_dir))
        )
        return {"events": events[-limit:], "total": len(events)}
    return {"events": [], "total": 0, "note": "No active session"}


@app.get("/debug/sessions")
async def debug_sessions(days: int = 7):
    """
    List recent sessions.

    Returns session IDs and start times for the past N days.
    """
    logger = get_logger()
    sessions = logger.get_recent_sessions(days)
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/debug/session/{session_id}")
async def debug_session(session_id: str):
    """
    Get all events from a specific session.

    Use session_id from /debug/sessions list.
    """
    logger = get_logger()
    sessions = logger.get_recent_sessions(30)

    # Find the session file
    for session in sessions:
        if session.get("session_id") == session_id:
            events = logger.read_session(session.get("file", ""))
            return {"session_id": session_id, "events": events, "count": len(events)}

    return {"error": f"Session {session_id} not found"}


@app.get("/debug/tool-stats")
async def debug_tool_stats(days: int = 7):
    """
    Get aggregated tool usage statistics.

    Shows which tools have been called and how many times.
    """
    logger = get_logger()
    stats = logger.get_tool_usage_stats(days)
    return {"tool_counts": stats, "period_days": days}


@app.get("/debug/errors")
async def debug_errors(hours: int = 24):
    """
    Get recent errors from conversation logs.

    Returns tool_error and error events from recent sessions.
    """
    logger = get_logger()
    errors = []

    for session in logger.get_recent_sessions(7):
        events = logger.read_session(session.get("file", ""))
        for event in events:
            if event.get("event") in ["tool_error", "error"]:
                event["session_id"] = session.get("session_id")
                errors.append(event)

    # Sort by timestamp descending, limit to recent
    errors.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return {"errors": errors[:50], "count": len(errors)}


@app.get("/debug/health")
async def debug_health():
    """
    Detailed health check including agent state.

    Returns system state useful for debugging.
    """
    from app.agent import get_agent

    agent_info = {}
    try:
        agent = get_agent()
        agent_info = {
            "name": agent.name if hasattr(agent, "name") else "unknown",
            "tools_count": len(agent.tools) if hasattr(agent, "tools") else 0,
            "initialized": True
        }
    except Exception as e:
        agent_info = {"initialized": False, "error": str(e)}

    logger = get_logger()

    return {
        "status": "healthy",
        "websocket_connections": len(manager.active_connections),
        "agent": agent_info,
        "current_session": logger.current_session_id,
        "storage_dir": str(logger.storage_dir)
    }


def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=8765,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
