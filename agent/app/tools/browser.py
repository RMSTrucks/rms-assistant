"""
Browser Tools

Tools for interacting with the browser via the Chrome extension.
These tools send requests to the extension via WebSocket.
"""

from agno.tools import Toolkit
from typing import Optional


class BrowserTools(Toolkit):
    """
    Tools for browser automation via Chrome extension.

    Note: These tools return descriptions of what they would do.
    Actual execution happens via the WebSocket server when the
    extension is connected.
    """

    def __init__(self, **kwargs):
        """Initialize browser tools."""
        tools = [
            self.navigate_to_url,
            self.get_current_page,
            self.click_element,
            self.fill_form_field,
            self.capture_screenshot,
        ]
        super().__init__(name="browser", tools=tools, **kwargs)

    def navigate_to_url(self, url: str) -> str:
        """
        Navigate the browser to a specific URL.

        Args:
            url: The URL to navigate to (e.g., "https://example.com")

        Returns:
            str: Confirmation of navigation request
        """
        if not url:
            return "Error: URL is required"

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        return f"Navigating to: {url}\n\nThe browser will open this URL in the current tab."

    def get_current_page(self) -> str:
        """
        Get information about the current page including forms and interactive elements.

        Returns:
            str: Description of the current page state
        """
        return """Requesting current page state from browser...

This will return:
- Current URL and page title
- Form fields (inputs, selects, textareas)
- Buttons and clickable elements
- Any relevant page content

The extension will provide this information when connected."""

    def click_element(self, selector: str, description: Optional[str] = None) -> str:
        """
        Click an element on the current page.

        Args:
            selector: CSS selector for the element to click (e.g., "#submit-button", ".login-btn")
            description: Optional description of what this click does

        Returns:
            str: Confirmation of click request
        """
        if not selector:
            return "Error: CSS selector is required"

        desc = f" ({description})" if description else ""
        return f"Clicking element: {selector}{desc}\n\nThis action will be executed in the browser."

    def fill_form_field(
        self,
        selector: str,
        value: str,
        field_name: Optional[str] = None
    ) -> str:
        """
        Fill a form field on the current page.

        Args:
            selector: CSS selector for the input field (e.g., "#email", "input[name='username']")
            value: The value to enter into the field
            field_name: Optional friendly name for the field

        Returns:
            str: Confirmation of fill request
        """
        if not selector:
            return "Error: CSS selector is required"
        if value is None:
            return "Error: Value is required"

        name = f" ({field_name})" if field_name else ""
        # Mask sensitive values
        display_value = value
        if any(word in selector.lower() for word in ["password", "secret", "token"]):
            display_value = "********"

        return f"Filling field {selector}{name} with: {display_value}\n\nThis action will be executed in the browser."

    def capture_screenshot(self) -> str:
        """
        Capture a screenshot of the current browser tab.

        Returns:
            str: Confirmation of screenshot request
        """
        return """Capturing screenshot of current tab...

The screenshot will be captured and can be used to:
- Verify the current page state
- Document what's visible
- Help troubleshoot issues

The extension will provide the screenshot when connected."""
