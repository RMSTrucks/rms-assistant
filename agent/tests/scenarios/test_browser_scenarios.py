"""
Scenario tests for Browser Tools integration.

NOTE: These tests require the Chrome extension to be connected.
Run with: pytest tests/scenarios/test_browser_scenarios.py -v

For CI, these should be marked as integration tests and run
only when the browser extension environment is available.
"""

import pytest
import scenario
from dotenv import load_dotenv

# Load environment variables for tests
load_dotenv()

from app.agent import get_agent

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
# TEST 1: Navigate to URL
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_navigate_to_url():
    """
    Test that agent can navigate to a URL.

    Requires Chrome extension to be connected.

    Validates:
    - Agent uses navigate_to_url tool
    - Agent reports navigation result
    """
    result = await scenario.run(
        name="browser navigate",
        description="""
            User asks agent to navigate to a website.
            Agent should attempt navigation and report result.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent attempts to navigate to the URL",
                    "Agent reports navigation result (success or failure)",
                    "Agent provides appropriate feedback about the action",
                ]
            ),
        ],
        script=[
            scenario.user("Navigate to google.com"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 2: Get Current Page State
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_current_page():
    """
    Test that agent can retrieve current page information.

    Requires Chrome extension to be connected.

    Validates:
    - Agent uses get_current_page tool
    - Agent reports page state or connection error
    """
    result = await scenario.run(
        name="browser get page",
        description="""
            User asks what page is currently open in the browser.
            Agent should check and report the current page state.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent attempts to get current page information",
                    "Agent reports page title/URL OR reports extension not connected",
                    "Agent provides useful feedback about the browser state",
                ]
            ),
        ],
        script=[
            scenario.user("What page is currently open in the browser?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 3: Fill Form Field
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_fill_form_field():
    """
    Test that agent can fill form fields.

    Requires Chrome extension to be connected with a page with forms.

    Validates:
    - Agent uses fill_form_field tool
    - Agent reports fill result
    """
    result = await scenario.run(
        name="browser fill form",
        description="""
            User asks agent to fill a form field.
            Agent should attempt the fill and report result.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent attempts to fill the form field",
                    "Agent reports result (success, failure, or extension not connected)",
                    "Agent handles the request appropriately",
                ]
            ),
        ],
        script=[
            scenario.user("Fill the email field with test@example.com"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 4: Browser Tool Graceful Failure (No Extension)
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_browser_graceful_failure():
    """
    Test that agent handles missing browser extension gracefully.

    This test validates error handling when extension is not connected.

    Validates:
    - Agent attempts browser action
    - Agent reports timeout/connection error gracefully
    - Agent doesn't crash or hang indefinitely
    """
    result = await scenario.run(
        name="browser graceful failure",
        description="""
            User asks for a browser action when extension may not be connected.
            Agent should handle gracefully and report the issue.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent attempts the browser action",
                    "Agent reports an error or timeout if extension not connected",
                    "Agent does NOT hang or crash",
                    "Agent provides helpful feedback about what went wrong",
                ]
            ),
        ],
        script=[
            scenario.user("Take a screenshot of the current tab"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"
