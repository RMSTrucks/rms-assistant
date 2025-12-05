"""
Browser-Use Agent for Carrier Quote Automation

LLM-driven form filling using browser-use library.
The agent sees the page and figures out how to fill it -
no hardcoded CSS selectors needed.

This approach is:
- Resilient to UI changes
- Works across carriers with minimal changes
- Debuggable (can watch the browser fill forms)
"""

import os
from typing import Optional, Callable, Any

from browser_use import Agent, Browser, ChatAnthropic


async def fill_quote_form(
    carrier: str,
    quote_data: dict,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> dict:
    """
    Fill a carrier quote form using LLM-driven browser automation.

    Args:
        carrier: Carrier name (e.g., "Progressive", "BHHC")
        quote_data: Dict with quote data (companyName, dotNumber, etc.)
        browser_config: Optional browser configuration
        on_progress: Optional callback for progress updates

    Returns:
        dict with success status and any messages
    """
    # Use Claude Sonnet for cost-effective automation
    llm = ChatAnthropic(model="claude-sonnet-4-0", temperature=0.0)

    # Configure browser - headless=False so Jake can watch
    browser = Browser(
        headless=False,
        disable_security=True,  # Needed for some insurance sites
    )

    # Build the task prompt with quote data
    task_prompt = _build_task_prompt(carrier, quote_data)

    if on_progress:
        await on_progress(f"Starting {carrier} quote automation...")

    try:
        agent = Agent(
            task=task_prompt,
            llm=llm,
            browser=browser,
        )

        result = await agent.run()

        if on_progress:
            await on_progress(f"{carrier} quote ready - at RATES page for review")

        return {
            "success": True,
            "carrier": carrier,
            "message": f"{carrier} quote filled successfully. Review the RATES page.",
            "result": str(result),
        }

    except Exception as e:
        error_msg = f"Quote automation error: {str(e)}"
        print(f"[BrowserAgent] ERROR: {error_msg}")

        if on_progress:
            await on_progress(f"Error: {error_msg}")

        return {
            "success": False,
            "carrier": carrier,
            "error": error_msg,
        }

    finally:
        # Don't close browser - leave it open for Jake to review
        pass


def _build_task_prompt(carrier: str, quote_data: dict) -> str:
    """
    Build the task prompt for the browser-use agent.

    The prompt tells the LLM:
    1. What data to fill
    2. How to navigate the wizard
    3. When to STOP (RATES page)
    """
    # Extract quote data with defaults
    company = quote_data.get("companyName", "")
    dot_number = quote_data.get("dotNumber", "")
    mc_number = quote_data.get("mcNumber", "")
    owner_name = quote_data.get("ownerName", "")
    address = quote_data.get("address", "")
    city = quote_data.get("city", "")
    state = quote_data.get("state", "")
    zip_code = quote_data.get("zip", "")
    phone = quote_data.get("phone", "")
    email = quote_data.get("email", "")
    effective_date = quote_data.get("effectiveDate", "")

    # Vehicle info if available
    vehicles = quote_data.get("vehicles", [])
    vehicle_info = ""
    if vehicles:
        vehicle_info = "\nVehicles:\n"
        for i, v in enumerate(vehicles, 1):
            vehicle_info += f"  Vehicle {i}: {v.get('year', '')} {v.get('make', '')} {v.get('model', '')}\n"
            vehicle_info += f"    VIN: {v.get('vin', 'N/A')}\n"

    # Driver info if available
    drivers = quote_data.get("drivers", [])
    driver_info = ""
    if drivers:
        driver_info = "\nDrivers:\n"
        for i, d in enumerate(drivers, 1):
            driver_info += f"  Driver {i}: {d.get('name', '')}\n"
            driver_info += f"    DOB: {d.get('dob', 'N/A')}, License: {d.get('license', 'N/A')}\n"

    prompt = f"""
You are filling out a {carrier} commercial auto insurance quote wizard.

QUOTE DATA TO FILL:
- Company Name: {company}
- DOT Number: {dot_number}
- MC Number: {mc_number}
- Owner/Contact: {owner_name}
- Address: {address}
- City: {city}
- State: {state}
- ZIP: {zip_code}
- Phone: {phone}
- Email: {email}
- Effective Date: {effective_date}
{vehicle_info}
{driver_info}

INSTRUCTIONS:
1. Navigate through ALL wizard tabs (START, VEHICLES, DRIVERS, BUSINESS, COVERAGES, etc.)
2. Fill each field you can find with the data above
3. For fields without data, use reasonable defaults or skip if optional
4. Click "Next", "Continue", or similar buttons to advance between tabs
5. For business type, search for "Trucking" or "Motor Carrier"
6. For vehicles, if specific data not available, use sensible trucking defaults

CRITICAL - STOP CONDITION:
When you reach the RATES page (shows premium amounts, coverage options):
- DO NOT click "Finish", "Buy", "Purchase", "Bind", or "Submit"
- DO NOT proceed past the rates display
- STOP and report that you've reached the RATES page

Report when done: "RATES page reached - ready for review"
"""
    return prompt


async def fill_progressive_quote(
    quote_data: dict,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> dict:
    """
    Convenience wrapper for Progressive quotes.
    """
    return await fill_quote_form(
        carrier="Progressive",
        quote_data=quote_data,
        on_progress=on_progress,
    )


async def fill_bhhc_quote(
    quote_data: dict,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> dict:
    """
    Convenience wrapper for BHHC (Berkshire Hathaway) quotes.
    """
    return await fill_quote_form(
        carrier="BHHC",
        quote_data=quote_data,
        on_progress=on_progress,
    )


async def fill_geico_quote(
    quote_data: dict,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> dict:
    """
    Convenience wrapper for Geico quotes.
    """
    return await fill_quote_form(
        carrier="Geico",
        quote_data=quote_data,
        on_progress=on_progress,
    )
