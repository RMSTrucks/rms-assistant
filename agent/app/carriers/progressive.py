"""
Progressive Commercial Auto Quote Automation

Pure browser-use implementation - opens Playwright browser directly.
No Chrome extension coordination needed.

Flow:
1. Click Progressive in sidepanel
2. browser-use opens Playwright browser to Progressive login
3. User logs in manually (visible browser)
4. browser-use fills ALL wizard tabs automatically
5. STOPS at RATES page
6. Notifies chat that quote is ready for review
"""

import os
from typing import Optional, Callable, Any

from fastapi import WebSocket

from browser_use import Agent, Browser, ChatAnthropic


# Progressive URLs
PROGRESSIVE_LOGIN_URL = "https://www.foragentsonlylogin.progressive.com/Login/"


async def send_progress(websocket: WebSocket, manager, carrier: str, status: str, tab_id: int):
    """Send progress update to sidepanel."""
    await manager.send_json(websocket, {
        "type": "carrier_quote_progress",
        "carrier": carrier,
        "status": status,
        "tabId": tab_id
    })


async def send_chat_message(websocket: WebSocket, manager, message: str):
    """Send a message to appear in the chat."""
    await manager.send_json(websocket, {
        "type": "agent_message",
        "message": message
    })


async def run_progressive_quote(
    websocket: WebSocket,
    manager,
    tab_id: int,
    quote_data: dict,
    config: dict
):
    """
    Run Progressive quote automation using browser-use.

    Opens a visible Playwright browser - user can watch it work.
    """
    login_url = config.get("loginUrl", PROGRESSIVE_LOGIN_URL)

    await send_progress(websocket, manager, "progressive", "Launching browser...", tab_id)
    print("[Progressive] Starting browser-use agent...")

    # Build the task prompt
    task_prompt = _build_task_prompt(quote_data, login_url)

    try:
        # Use Claude Sonnet for cost-effective automation
        llm = ChatAnthropic(model="claude-sonnet-4-0", temperature=0.0)

        # Visible browser so Jake can watch
        browser = Browser(
            headless=False,
            disable_security=True,
        )

        await send_progress(websocket, manager, "progressive", "Browser opened - navigate to login...", tab_id)

        agent = Agent(
            task=task_prompt,
            llm=llm,
            browser=browser,
        )

        await send_progress(websocket, manager, "progressive", "Agent running - filling quote...", tab_id)

        result = await agent.run()

        # Done - notify chat
        await send_chat_message(
            websocket,
            manager,
            "Progressive quote filled! Review the RATES page and click Finish/Buy when ready."
        )
        await send_progress(websocket, manager, "progressive", "Quote ready - at RATES page", tab_id)
        print("[Progressive] SUCCESS: Quote automation complete")

        return {"success": True, "result": str(result)}

    except Exception as e:
        error_msg = f"Progressive automation failed: {str(e)}"
        print(f"[Progressive] ERROR: {error_msg}")
        await send_progress(websocket, manager, "progressive", f"Error: {str(e)}", tab_id)
        await send_chat_message(websocket, manager, error_msg)
        return {"success": False, "error": error_msg}


def _build_task_prompt(quote_data: dict, login_url: str) -> str:
    """Build the task prompt for browser-use agent."""

    # Parse owner name
    owner_name = quote_data.get("ownerName", "")
    parts = owner_name.strip().split() if owner_name else []
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    task = f"""
You are automating a Progressive Commercial Auto insurance quote.

STEP 1 - GO TO LOGIN:
Navigate to: {login_url}
Wait for the user to log in manually. Watch for the URL to change to foragentsonly.com/home or similar.

STEP 2 - START NEW QUOTE:
Once logged in (you see the home page):
1. Find the state dropdown and select: {quote_data.get('state', 'TX')}
2. Click "Select Product(s)" button
3. Click "COMMERCIAL AUTO"
4. Click "ADD PRODUCTS TO QUOTE"

A new window/tab will open with the quote wizard.

STEP 3 - FILL THE QUOTE WIZARD:
Fill these fields across ALL tabs:

START TAB:
- Effective Date: {quote_data.get('effectiveDate', '')}
- USDOT Question: Select "Yes" if DOT provided
- DOT Number: {quote_data.get('dotNumber', '')}
- Business Structure: Corporation or LLC
- Business Type: Search for "Trucking"
- First Name: {first_name}
- Last Name: {last_name}
- Address: {quote_data.get('address', '')}
- City: {quote_data.get('city', '')}
- State: {quote_data.get('state', '')}
- ZIP: {quote_data.get('zip', '')}
- Phone: {quote_data.get('phone', '')}

VEHICLES TAB:
- Add vehicle info if available, otherwise use trucking defaults

DRIVERS TAB:
- Add driver info, use owner as primary driver if needed

Continue through BUSINESS, COVERAGES tabs.

CRITICAL STOP CONDITION:
When you reach the RATES page (shows premium/pricing):
- DO NOT click Finish, Buy, Purchase, Bind, or Submit
- STOP immediately
- Report: "RATES page reached - ready for review"
"""
    return task
