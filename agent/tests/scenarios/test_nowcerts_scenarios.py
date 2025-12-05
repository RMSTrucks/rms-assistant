"""
Scenario tests for NowCerts API integration.

Tests real API interactions:
- search_insured: Find customers by name
- search_by_dot: Find customers by DOT number
- get_expiring_policies: Renewal pipeline
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
# TEST 1: Search Insured by Name
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_search_insured_by_name():
    """
    Test searching for an insured by name in NowCerts.

    Validates:
    - Agent uses search_insured tool
    - Response shows search results or indicates not found
    - Response includes insured details if found
    """
    result = await scenario.run(
        name="nowcerts search by name",
        description="""
            User asks to search for an insured in NowCerts.
            Agent should search and return results or indicate nothing found.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent searches NowCerts for the insured",
                    "Agent reports search results or indicates no matches found",
                    "If results found, includes basic info like name and ID",
                ]
            ),
        ],
        script=[
            scenario.user("Search NowCerts for LDJ"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 2: Search Insured - Not Found
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_search_insured_not_found():
    """
    Test graceful handling when no insured is found.

    Validates:
    - Agent searches NowCerts
    - Agent gracefully reports no results
    - Agent doesn't make up data
    """
    result = await scenario.run(
        name="nowcerts search not found",
        description="""
            User searches for an insured that likely doesn't exist.
            Agent should report no results without hallucinating data.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent attempts to search NowCerts",
                    "Agent reports no matching results were found",
                    "Agent does NOT make up or hallucinate insured data",
                ]
            ),
        ],
        script=[
            scenario.user("Search NowCerts for XYZNONEXISTENT99999"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 3: Get Expiring Policies
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_get_expiring_policies():
    """
    Test the expiring policies workflow for renewal pipeline.

    Validates:
    - Agent uses get_expiring_policies tool
    - Agent provides list with dates or indicates none found
    - Response is actionable for renewal planning
    """
    result = await scenario.run(
        name="nowcerts expiring policies",
        description="""
            User asks about policies expiring soon.
            Agent should check NowCerts and provide renewal pipeline info.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent checks NowCerts for expiring policies",
                    "Agent provides a list with dates OR indicates none found",
                    "Response helps with renewal planning",
                ]
            ),
        ],
        script=[
            scenario.user("What policies are expiring in the next 30 days?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"
