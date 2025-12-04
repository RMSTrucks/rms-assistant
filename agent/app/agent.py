"""
RMS Insurance Agent

Main agent implementation with LangWatch instrumentation.
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


# Load environment variables
load_dotenv()

# Initialize LangWatch
langwatch.api_key = os.getenv("LANGWATCH_API_KEY")


def load_prompt_from_file(prompt_name: str) -> dict:
    """
    Load a prompt from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)

    Returns:
        dict: Prompt configuration including system message
    """
    import yaml

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        f"{prompt_name}.yaml"
    )

    with open(prompt_path, "r") as f:
        prompt_data = yaml.safe_load(f)

    # Extract system message from messages list
    system_message = ""
    for msg in prompt_data.get("messages", []):
        if msg.get("role") == "system":
            system_message = msg.get("content", "")
            break

    return {
        "model": prompt_data.get("model", "claude-sonnet-4-20250514"),
        "temperature": prompt_data.get("temperature", 0.7),
        "instructions": system_message,
    }


# Global agent instance - create once, reuse always
_agent_instance: Optional[Agent] = None


def get_agent() -> Agent:
    """
    Get or create the RMS insurance agent.

    CRITICAL: This function ensures we create the agent only once
    and reuse it for all requests. Never create agents in loops!

    Returns:
        Agent: The RMS insurance agent instance
    """
    global _agent_instance

    if _agent_instance is None:
        # Load prompt configuration
        prompt_config = load_prompt_from_file("rms-insurance-agent")

        # Create the agent with all tools
        _agent_instance = Agent(
            name="RMS Insurance Assistant",
            model=Claude(id="claude-sonnet-4-20250514"),
            instructions=prompt_config["instructions"],
            tools=[
                DOTLookupTools(),
                CloseCRMTools(),
                NowCertsTools(),
                KnowledgeTools(),
                BrowserTools(),
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
