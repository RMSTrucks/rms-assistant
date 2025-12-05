"""
Scenario tests for RMS Insurance Agent v2.

Tests the enhanced capabilities:
- Cross-system workflows (carrier_snapshot, new_prospect)
- Memory/notes persistence
- Structured reasoning
- Risk assessment heuristics
"""

import os
import shutil
import pytest
import scenario
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables for tests
load_dotenv()

from app.agent import get_agent

# Configure Scenario to use Anthropic
scenario.configure(
    default_model="anthropic/claude-sonnet-4-20250514",
)


class RMSAgentV2Adapter(scenario.AgentAdapter):
    """
    Adapter for v2 agent with memory support.
    """

    def __init__(self):
        self.agent = get_agent()

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        last_message = input.messages[-1]["content"] if input.messages else ""
        response = self.agent.run(last_message)
        return str(response.content)


# ============================================================================
# V2 TEST 1: Carrier Snapshot Workflow
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_carrier_snapshot_workflow():
    """
    Test the cross-system carrier snapshot workflow.

    Validates:
    - Agent uses carrier_snapshot or equivalent multi-tool approach
    - Response includes FMCSA data
    - Response mentions Close CRM status
    - Response mentions NowCerts status
    """
    result = await scenario.run(
        name="carrier snapshot workflow",
        description="""
            User asks for a complete view of a carrier.
            Agent should check DOT database, Close CRM, and NowCerts,
            providing a unified view of the carrier.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent provides FMCSA/DOT information (carrier name, status)",
                    "Agent checks or mentions Close CRM status",
                    "Agent checks or mentions NowCerts/policy status",
                    "Response provides a unified view across systems",
                ]
            ),
        ],
        script=[
            scenario.user("Give me a full carrier snapshot for DOT 2865619"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# V2 TEST 2: Prospect Qualification with Risk Assessment
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_prospect_qualification():
    """
    Test structured risk assessment for prospect qualification.

    Validates:
    - Agent gathers relevant data (DOT, safety)
    - Agent applies risk heuristics
    - Agent provides QUALIFIED/REVIEW/DECLINE recommendation
    - Agent explains reasoning
    """
    result = await scenario.run(
        name="prospect qualification",
        description="""
            User asks to qualify a carrier as a prospect.
            Agent should look up their DOT and safety data,
            apply risk assessment heuristics, and provide a
            clear recommendation with reasoning.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent looks up DOT and/or safety information",
                    "Agent considers safety metrics in assessment",
                    "Agent provides a clear recommendation (qualified, review, or decline)",
                    "Agent explains the reasoning behind the recommendation",
                ]
            ),
        ],
        script=[
            scenario.user("Is DOT 2865619 a good prospect for us? Should we quote them?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# V2 TEST 3: Memory - Remember and Recall
# ============================================================================

@pytest.fixture
def clean_notes_dir():
    """Clean up notes directory before and after test."""
    notes_dir = Path(__file__).parent.parent.parent / "notes"

    # Clean before
    if notes_dir.exists():
        shutil.rmtree(notes_dir)

    yield notes_dir

    # Clean after (optional - keep for debugging)
    # if notes_dir.exists():
    #     shutil.rmtree(notes_dir)


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_memory_remember(clean_notes_dir):
    """
    Test that agent can remember information.

    Validates:
    - Agent uses remember tool
    - Agent confirms what was stored
    """
    result = await scenario.run(
        name="memory remember",
        description="""
            User asks agent to remember something about a carrier.
            Agent should store the information and confirm.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent acknowledges the information to remember",
                    "Agent confirms the information was stored",
                    "Response indicates the memory was saved",
                ]
            ),
        ],
        script=[
            scenario.user("Remember that DOT 9999999 had a claim last month and we should follow up"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"

    # Verify the file was created
    notes_file = clean_notes_dir / "carriers" / "9999999.md"
    assert notes_file.exists(), "Notes file was not created"


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_memory_recall(clean_notes_dir):
    """
    Test that agent can recall previously stored information.

    Validates:
    - Agent remembers, then recalls
    - Recalled information matches what was stored
    """
    # First, store something
    adapter = RMSAgentV2Adapter()
    await adapter.call(scenario.AgentInput(
        messages=[{"role": "user", "content": "Remember that DOT 8888888 prefers email contact only"}]
    ))

    # Now test recall
    result = await scenario.run(
        name="memory recall",
        description="""
            Agent should recall previously stored information.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent retrieves the stored information",
                    "Response mentions email contact preference",
                    "Agent provides the relevant context",
                ]
            ),
        ],
        script=[
            scenario.user("What do you know about DOT 8888888?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# V2 TEST 4: Expiring Policies Workflow
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_expiring_policies():
    """
    Test the expiring policies workflow.

    Validates:
    - Agent uses get_expiring_policies tool
    - Agent provides list with dates
    - Agent shows days remaining
    """
    result = await scenario.run(
        name="expiring policies check",
        description="""
            User asks about policies expiring soon.
            Agent should check NowCerts and provide a list.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent checks for expiring policies",
                    "Agent provides a list or indicates none found",
                    "If policies found, shows expiration dates",
                    "Response is actionable for renewal planning",
                ]
            ),
        ],
        script=[
            scenario.user("Show me policies expiring in the next 30 days"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# V2 TEST 5: Structured Reasoning
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_structured_reasoning():
    """
    Test that agent uses structured reasoning for complex tasks.

    Validates:
    - Agent demonstrates structured approach
    - Agent gathers necessary information
    - Agent synthesizes findings
    - Agent provides actionable output
    """
    result = await scenario.run(
        name="structured reasoning",
        description="""
            User asks a complex question requiring multiple steps.
            Agent should demonstrate structured thinking.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent approaches the task systematically",
                    "Agent gathers relevant information",
                    "Agent synthesizes findings into a clear answer",
                    "Response shows logical reasoning process",
                ]
            ),
        ],
        script=[
            scenario.user("I need to call DOT 2865619 tomorrow. What should I know about them before the call?"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"


# ============================================================================
# V2 TEST 6: New Prospect Workflow
# ============================================================================

@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_new_prospect_workflow():
    """
    Test the new_prospect workflow that combines DOT lookup with lead creation.

    Validates:
    - Agent looks up DOT information
    - Agent creates or attempts to create lead
    - Agent checks for existing relationship
    """
    result = await scenario.run(
        name="new prospect workflow",
        description="""
            User wants to create a new prospect from a DOT number.
            Agent should look up the carrier, check if they exist,
            and create a lead if appropriate.
        """,
        agents=[
            RMSAgentV2Adapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "Agent looks up the DOT information",
                    "Agent checks if lead already exists in CRM",
                    "Agent creates lead or explains why not",
                    "Agent provides summary of actions taken",
                ]
            ),
        ],
        script=[
            scenario.user("Create a new prospect from DOT 2865619"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )

    assert result.success, f"Test failed: {result.reasoning}"
