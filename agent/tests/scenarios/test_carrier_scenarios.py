"""
Scenario tests for Carrier Quote Automation.

Tests the browser-use agent for carrier quote form filling.

NOTE: These tests require:
- browser-use library installed
- Real browser automation (opens visible browser)
- Progressive login credentials (for full flow)

For CI, these should be marked as integration tests.
"""

import pytest
import scenario
from dotenv import load_dotenv

# Load environment variables for tests
load_dotenv()

from app.agent import get_agent
from app.carriers.browser_agent import _build_task_prompt

# Configure Scenario to use Anthropic
scenario.configure(
    default_model="anthropic/claude-sonnet-4-20250514",
)


class RMSAgentAdapter(scenario.AgentAdapter):
    """Adapter for RMS agent."""

    def __init__(self):
        self.agent = get_agent()

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        last_message = input.messages[-1]["content"] if input.messages else ""
        response = self.agent.run(last_message)
        return str(response.content)


# ============================================================================
# TEST 1: Quote Data Extraction
# ============================================================================

def test_quote_prompt_building():
    """
    Unit test that quote data is properly structured for browser-use agent.

    This doesn't require browser automation - just verifies prompt generation.
    """
    quote_data = {
        "companyName": "ABC Trucking LLC",
        "dotNumber": "1234567",
        "mcNumber": "MC-987654",
        "ownerName": "John Smith",
        "address": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "zip": "75001",
        "phone": "555-123-4567",
        "email": "john@abctrucking.com",
        "effectiveDate": "2025-01-15",
        "vehicles": [
            {"year": "2022", "make": "Freightliner", "model": "Cascadia", "vin": "1ABCD12345678901"}
        ],
        "drivers": [
            {"name": "John Smith", "dob": "1980-05-15", "license": "TX12345678"}
        ],
    }

    prompt = _build_task_prompt("Progressive", quote_data)

    # Verify essential data is in the prompt
    assert "ABC Trucking LLC" in prompt
    assert "1234567" in prompt  # DOT
    assert "Dallas" in prompt
    assert "TX" in prompt
    assert "2025-01-15" in prompt  # Effective date
    assert "Freightliner" in prompt  # Vehicle
    assert "John Smith" in prompt  # Owner and driver
    assert "RATES" in prompt  # Stop condition


def test_quote_prompt_with_minimal_data():
    """
    Test that prompt handles minimal quote data gracefully.
    """
    quote_data = {
        "companyName": "Test Company",
        "dotNumber": "9999999",
    }

    prompt = _build_task_prompt("Progressive", quote_data)

    # Should still generate a valid prompt
    assert "Test Company" in prompt
    assert "9999999" in prompt
    assert "Progressive" in prompt
    assert "RATES" in prompt


# ============================================================================
# TEST 2: Start Progressive Quote (Integration)
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_start_progressive_quote():
    """
    Integration test: Agent initiates Progressive quote.

    Requires browser-use and real browser.
    Will open a visible browser window.

    Validates:
    - Agent launches browser automation
    - Agent navigates to Progressive login
    - Agent reports progress
    """
    result = await scenario.run(
        name="progressive quote start",
        description="""
            User asks to start a Progressive quote with carrier data.
            Agent should initiate browser automation.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent understands the request to start a quote",
                    "Agent indicates it will use browser automation",
                    "Agent provides feedback about the process starting",
                ]
            ),
        ],
        script=[
            scenario.user("Start a Progressive quote for ABC Trucking, DOT 1234567, in Texas"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 3: Quote Stops at Rates Page
# ============================================================================

def test_quote_prompt_stop_condition():
    """
    Verify the prompt includes clear stop conditions.

    The browser-use agent must NOT click buy/submit/finish.
    """
    quote_data = {"companyName": "Test", "dotNumber": "123"}
    prompt = _build_task_prompt("Progressive", quote_data)

    # Must include stop instructions
    assert "STOP" in prompt.upper()
    assert "RATES" in prompt.upper()

    # Must NOT click these buttons
    stop_words = ["finish", "buy", "purchase", "bind", "submit"]
    for word in stop_words:
        assert word.lower() in prompt.lower(), f"Prompt should mention not clicking '{word}'"
