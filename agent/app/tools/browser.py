"""
Browser Tools

Tools for interacting with the browser via the Chrome extension.
These tools send requests to the extension via WebSocket.
"""

import threading
import uuid
from queue import Queue, Empty
from typing import Optional, Any

from agno.tools.toolkit import Toolkit

from app.observability import observe_tool


# ===========================================================================
# Global communication between agent tools (sync) and WebSocket server (async)
# ===========================================================================

_action_queue: Queue = Queue()
_result_store: dict[str, Any] = {}
_result_events: dict[str, threading.Event] = {}


def queue_browser_action(action: str, timeout: float = 30.0, **kwargs) -> dict:
    """
    Queue a browser action and wait for result.

    Called by agent tools (sync). The WebSocket server monitors
    the queue and executes actions asynchronously.

    Args:
        action: Action type (navigate, click, fill, screenshot, get_page_state)
        timeout: How long to wait for result (seconds)
        **kwargs: Action-specific parameters

    Returns:
        dict: Result from browser extension
    """
    action_id = str(uuid.uuid4())
    event = threading.Event()

    # Register for result callback
    _result_events[action_id] = event

    # Queue the action for the WebSocket server to pick up
    _action_queue.put({
        "action_id": action_id,
        "action": action,
        **kwargs
    })

    print(f"[BrowserTools] Queued action: {action} (id={action_id[:8]}...)")

    # Wait for result from extension
    if event.wait(timeout=timeout):
        result = _result_store.pop(action_id, {"error": "Result not found"})
        _result_events.pop(action_id, None)
        print(f"[BrowserTools] Got result for {action}: {str(result)[:100]}...")
        return result
    else:
        # Timeout - clean up
        _result_events.pop(action_id, None)
        _result_store.pop(action_id, None)
        print(f"[BrowserTools] Timeout waiting for {action}")
        return {"error": f"Browser action timed out after {timeout}s. Is the extension connected?"}


def get_pending_action() -> Optional[dict]:
    """
    Get next pending action from queue (non-blocking).

    Called by the WebSocket server's background task.
    """
    try:
        return _action_queue.get_nowait()
    except Empty:
        return None


def deliver_action_result(action_id: str, result: Any):
    """
    Deliver result back to waiting tool.

    Called by WebSocket server when extension sends result.
    """
    print(f"[BrowserTools] Delivering result for {action_id[:8]}...")
    _result_store[action_id] = result
    event = _result_events.get(action_id)
    if event:
        event.set()
    else:
        print(f"[BrowserTools] WARNING: No event found for {action_id[:8]}")


class BrowserTools(Toolkit):
    """
    Tools for browser automation via Chrome extension.

    These tools queue actions that are executed via WebSocket
    when the extension is connected.
    """

    def __init__(self):
        """Initialize browser tools."""
        super().__init__(name="browser")

        # Register tools explicitly
        self.register(self.navigate_to_url)
        self.register(self.get_current_page)
        self.register(self.click_element)
        self.register(self.fill_form_field)
        self.register(self.capture_screenshot)

    @observe_tool
    def navigate_to_url(self, url: str) -> str:
        """
        Navigate the browser to a specific URL.

        Args:
            url: The URL to navigate to (e.g., "https://example.com")

        Returns:
            str: Result of navigation
        """
        if not url:
            return "Error: URL is required"

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        result = queue_browser_action("navigate", url=url)

        if "error" in result:
            return f"Navigation failed: {result['error']}"

        return f"Navigated to: {url}"

    @observe_tool
    def get_current_page(self) -> str:
        """
        Get information about the current page including URL, title, and interactive elements.

        Returns:
            str: Description of the current page state
        """
        result = queue_browser_action("get_page_state")

        if "error" in result:
            return f"Failed to get page state: {result['error']}"

        if not result.get("success"):
            return f"Failed to get page state: {result}"

        # Extract pageState from extension response
        page_state = result.get("pageState", {})
        url = page_state.get("url", "Unknown")
        title = page_state.get("title", "Unknown")
        elements = page_state.get("elements", [])

        output = [f"Current Page: {title}", f"URL: {url}", ""]

        # Categorize elements by type
        inputs = []
        buttons = []
        selects = []

        for el in elements:
            tag = el.get("tag", "")
            el_type = el.get("type", "")
            name = el.get("name", "")
            el_id = el.get("id", "")
            placeholder = el.get("placeholder", "")
            text = el.get("text", "").strip()

            # Build a useful description
            identifier = el_id or name or placeholder or text[:30]
            if not identifier:
                identifier = f"{tag}"

            if tag == "button" or el_type == "submit":
                desc = f"{identifier}" + (f" ({text})" if text and text != identifier else "")
                buttons.append(desc)
            elif tag == "select":
                selects.append(f"{identifier}")
            elif tag in ("input", "textarea"):
                desc = f"{identifier} ({el_type})" if el_type else identifier
                inputs.append(desc)

        if inputs:
            output.append("Input fields:")
            for inp in inputs[:15]:
                output.append(f"  - {inp}")
            output.append("")

        if selects:
            output.append("Dropdown selects:")
            for sel in selects[:10]:
                output.append(f"  - {sel}")
            output.append("")

        if buttons:
            output.append("Buttons:")
            for btn in buttons[:10]:
                output.append(f"  - {btn}")
            output.append("")

        if not inputs and not selects and not buttons:
            output.append("No interactive elements detected on this page.")

        return "\n".join(output)

    @observe_tool
    def click_element(self, selector: str, description: Optional[str] = None) -> str:
        """
        Click an element on the current page.

        Args:
            selector: CSS selector for the element to click (e.g., "#submit-button")
            description: Optional description of what this click does

        Returns:
            str: Result of click action
        """
        if not selector:
            return "Error: CSS selector is required"

        result = queue_browser_action("click", selector=selector)

        if "error" in result:
            return f"Click failed: {result['error']}"

        desc = f" ({description})" if description else ""
        return f"Clicked: {selector}{desc}"

    @observe_tool
    def fill_form_field(
        self,
        selector: str,
        value: str,
        field_name: Optional[str] = None
    ) -> str:
        """
        Fill a form field on the current page.

        Args:
            selector: CSS selector for the input field (e.g., "#email")
            value: The value to enter into the field
            field_name: Optional friendly name for the field

        Returns:
            str: Result of fill action
        """
        if not selector:
            return "Error: CSS selector is required"
        if value is None:
            return "Error: Value is required"

        result = queue_browser_action("fill", selector=selector, value=value)

        if "error" in result:
            return f"Fill failed: {result['error']}"

        name = f" ({field_name})" if field_name else ""
        # Mask sensitive values in response
        display_value = value
        if any(word in selector.lower() for word in ["password", "secret", "token"]):
            display_value = "********"

        return f"Filled {selector}{name} with: {display_value}"

    @observe_tool
    def capture_screenshot(self) -> str:
        """
        Capture a screenshot of the current browser tab.

        Returns:
            str: Confirmation that screenshot was captured
        """
        result = queue_browser_action("screenshot")

        if "error" in result:
            return f"Screenshot failed: {result['error']}"

        # Don't return actual base64 data - too large for chat
        # Just confirm it was captured
        if result.get("success"):
            return "Screenshot captured successfully. The image shows the current browser tab."
        else:
            return f"Screenshot capture returned: {result}"
