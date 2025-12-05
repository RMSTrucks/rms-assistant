"""
RMS Insurance Agent

Main agent implementation with LangWatch instrumentation.
Prompts managed via LangWatch Prompt CLI (see prompts.json).
"""

import os
from typing import Optional
from dotenv import load_dotenv

import langwatch
from agno.agent import Agent
from agno.models.anthropic import Claude

from app.tools.dot_lookup import DOTLookupTools
from app.tools.close_crm import CloseCRMTools
from app.tools.nowcerts import NowCertsTools
from app.tools.knowledge import KnowledgeTools
from app.tools.browser import BrowserTools
from app.tools.pdf import PDFTools
from app.tools.workflows import WorkflowTools
from app.tools.notes import NotesTools


# Load environment variables
load_dotenv()

# Initialize LangWatch
langwatch.api_key = os.getenv("LANGWATCH_API_KEY")


# Global agent instance - create once, reuse always
_agent_instance: Optional[Agent] = None


def get_agent() -> Agent:
    """
    Get or create the RMS insurance agent.

    CRITICAL: This function ensures we create the agent only once
    and reuse it for all requests. Never create agents in loops!

    Prompts are fetched from LangWatch registry (managed via CLI).
    See: https://docs.langwatch.ai/prompt-management/cli

    Returns:
        Agent: The RMS insurance agent instance
    """
    global _agent_instance

    if _agent_instance is None:
        # Fetch prompt from LangWatch registry
        # Prompts synced via: npx langwatch prompt sync
        prompt = langwatch.prompts.get("rms-insurance-agent-v2")

        # Extract system message from messages list
        system_message = ""
        for msg in prompt.messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
                break

        # Create the agent with all tools
        _agent_instance = Agent(
            name="RMS Insurance Assistant",
            model=Claude(id=prompt.model or "claude-sonnet-4-20250514"),
            instructions=system_message,
            tools=[
                DOTLookupTools(),
                CloseCRMTools(),
                NowCertsTools(),
                KnowledgeTools(),
                BrowserTools(),
                PDFTools(),
                WorkflowTools(),
                NotesTools(),
            ],
            markdown=True,
        )

    return _agent_instance


@langwatch.trace()
def run_agent(message: str, user_id: Optional[str] = None) -> str:
    """
    Run the RMS agent with a user message.

    Args:
        message: The user's message/task
        user_id: Optional user identifier for tracing

    Returns:
        str: The agent's response
    """
    agent = get_agent()

    # Update trace metadata if we have user_id
    trace = langwatch.get_current_trace()
    if trace and user_id:
        trace.update(user_id=user_id)

    # Run the agent
    response = agent.run(message)

    return response.content


def chat(message: str) -> str:
    """
    Simple chat interface for the agent.

    Args:
        message: User message

    Returns:
        str: Agent response
    """
    return run_agent(message)
