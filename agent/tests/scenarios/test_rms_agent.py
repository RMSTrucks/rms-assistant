"""
Scenario tests for RMS Insurance Agent.

Tests multi-turn conversations and tool usage following LangWatch best practices:
- Use judge criteria instead of regex/word matching
- Use functions for deterministic checks (tool calls, etc.)
- Write as few scenarios as possible covering key paths
- Run single scenarios when debugging
"""

import os
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
    """
    Adapter to connect Scenario testing framework with our Agno-based agent.

    Following Agno best practices: agent is created once and reused.
    """

    def __init__(self):
        # Get the singleton agent instance (NEVER create agents in loops!)
        self.agent = get_agent()

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        """
        Call the agent with the latest user message.

        Args:
            input: Contains messages and conversation state

        Returns:
            str: Agent's response
        """
        # Get the last user message
        last_message = input.messages[-1]["content"] if input.messages else ""

        # Run agent
        response = self.agent.run(last_message)
        return str(response.content)


# ============================================================================
# TEST 1: DOT Number Lookup
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_dot_number_lookup():
    """
    Test that agent can lookup DOT numbers and provide relevant information.

    Validates:
    - Agent understands DOT lookup request
    - Agent uses the DOT lookup tool
    - Agent provides carrier information
    """
    result = await scenario.run(
        name="DOT number lookup",
        description="""
            User asks to look up information for a specific DOT number.
            Agent should use the lookup_dot_number tool and provide
            the carrier information including company name and status.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent provides carrier name and operating status",
                    "Agent includes relevant information like power units or MC number",
                    "Response is professional and helpful",
                ]
            ),
        ],
        script=[
            scenario.user("Look up DOT 1234567 for me"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 2: Adding Notes to Lead
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_add_note_to_lead():
    """
    Test that agent can add notes to leads in Close CRM.

    Validates:
    - Agent uses CRM tool to add note
    - Agent confirms the note was added
    """
    result = await scenario.run(
        name="add note to lead",
        description="""
            User wants to add a note to a specific lead in Close CRM.
            Agent should use the add_note_to_lead tool and confirm success.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent adds the note to the specified lead",
                    "Agent confirms the note was added successfully",
                    "Response includes the lead ID in confirmation",
                ]
            ),
        ],
        script=[
            scenario.user("Add a note to lead_abc123: Customer interested in cargo insurance, needs quote by Friday"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 3: Process Information - Broker Bond
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_broker_bond_process():
    """
    Test that agent can explain the broker bond process.

    Validates:
    - Agent uses knowledge tool
    - Agent provides accurate process information
    """
    result = await scenario.run(
        name="broker bond process explanation",
        description="""
            User asks about the broker bond process.
            Agent should explain the BMC-84 requirements and our process.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent explains what a broker bond (BMC-84) is",
                    "Agent mentions the $75,000 requirement",
                    "Agent provides our process steps",
                    "Information is accurate and helpful",
                ]
            ),
        ],
        script=[
            scenario.user("What's our process for getting a customer a broker bond?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 4: Multi-Turn Workflow
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_multi_turn_customer_workflow():
    """
    Test a multi-turn conversation simulating a real customer workflow.

    Validates:
    - Agent handles multiple related requests
    - Agent maintains context across turns
    - Agent uses multiple tools appropriately
    """
    result = await scenario.run(
        name="customer onboarding workflow",
        description="""
            Agent handles a new customer inquiry:
            1. User asks to look up a DOT number
            2. User then asks to create a lead for this customer
            The agent should handle both requests appropriately.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent successfully looks up the DOT number",
                    "Agent creates the lead with appropriate information",
                    "Agent maintains professional tone throughout",
                    "Agent confirms actions taken at each step",
                ]
            ),
        ],
        script=[
            scenario.user("Look up DOT 7654321"),
            scenario.agent(),
            scenario.user("Great, create a lead for them. Company is Acme Trucking, contact John at john@acme.com"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# TEST 5: Coverage Information
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_coverage_information():
    """
    Test that agent can explain insurance coverage types.

    Validates:
    - Agent uses knowledge tool
    - Agent provides accurate coverage information
    """
    result = await scenario.run(
        name="cargo insurance coverage explanation",
        description="""
            User asks about cargo insurance coverage.
            Agent should explain what cargo insurance covers and typical limits.
        """,
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent explains what cargo insurance covers",
                    "Agent mentions typical coverage limits",
                    "Agent mentions any FMCSA requirements",
                    "Information is accurate for trucking industry",
                ]
            ),
        ],
        script=[
            scenario.user("What does cargo insurance cover and what limits do trucking companies typically need?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"
