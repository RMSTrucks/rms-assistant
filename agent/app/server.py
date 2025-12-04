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
    tab_state: Optional[dict] = None
) -> None:
    """
    Process a user message and stream the response.

    Args:
        websocket: The WebSocket connection
        message: User's message
        tab_state: Current browser tab state
    """
    # Signal response starting
    await manager.send_json(websocket, {"type": "response_start"})

    try:
        # Get the agent
        agent = get_agent()

        # Build context with tab state if available
        context_message = message
        if tab_state:
            context_message = f"[Current tab: {tab_state.get('title', 'Unknown')} - {tab_state.get('url', 'Unknown')}]\n\n{message}"

        # Run agent and get response
        response = agent.run(context_message)
        content = str(response.content)

        # Stream the response word by word for better UX
        words = content.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            await manager.send_json(websocket, {
                "type": "response_chunk",
                "content": chunk
            })
            # Small delay for streaming effect
            await asyncio.sleep(0.02)

    except Exception as e:
        await manager.send_json(websocket, {
            "type": "error",
            "message": str(e)
        })

    finally:
        # Signal response complete
        await manager.send_json(websocket, {"type": "response_end"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for Chrome extension."""
    await manager.connect(websocket)

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
                await process_message(websocket, content, tab_state)

            elif msg_type == "action_response":
                # User responded to an action request
                action_id = data.get("actionId")
                approved = data.get("approved", False)
                manager.resolve_action(action_id, approved)

            elif msg_type == "browser_action_result":
                # Result from a browser action we requested
                action_id = data.get("actionId")
                result = data.get("result")
                print(f"[Server] Browser action result: {action_id} -> {result}")

            elif msg_type == "tab_state":
                # Tab state update (informational)
                tab = data.get("tab", {})
                print(f"[Server] Tab state: {tab.get('title', 'Unknown')}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[Server] Error: {e}")
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": len(manager.active_connections)
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
