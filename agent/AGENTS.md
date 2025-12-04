# RMS Trucks Insurance Agent - Development Guidelines

## Project Overview

**Goal:** AI assistant for RMS Trucks insurance agency that lives in a Chrome browser side panel. Delegate tasks during phone calls or while working - "this customer needs a broker bond", "look up DOT 1234567", "add a note to this lead", "what's our process for cargo claims?". The agent has tools to control the browser, access Close CRM and NowCerts, and execute known workflows. It handles tasks in the background while you continue working.

**Framework:** Agno
**Language:** Python
**Testing:** LangWatch Scenario

This project follows LangWatch best practices for building production-ready AI agents.

---

## Current Implementation

### Available Tools

The agent has access to these tool categories:

1. **DOT Lookup Tools** (`app/tools/dot_lookup.py`)
   - `lookup_dot_number(dot_number)` - Look up carrier info from FMCSA
   - `search_carriers(company_name, state)` - Search for carriers by name
   - `check_safety_rating(dot_number)` - Get safety rating and BASIC scores

2. **Close CRM Tools** (`app/tools/close_crm.py`)
   - `add_note_to_lead(lead_id, note)` - Add notes to leads
   - `create_lead(company_name, contact_name, email, phone, dot_number, notes)` - Create new leads
   - `search_leads(query, status)` - Search for existing leads
   - `update_lead_status(lead_id, status, reason)` - Update lead status
   - `log_call(lead_id, duration_minutes, direction, summary, outcome)` - Log call activities

3. **NowCerts Tools** (`app/tools/nowcerts.py`)
   - `search_insured(query, search_type)` - Search for insureds
   - `get_policy_details(policy_number)` - Get policy details
   - `list_certificates(insured_id, active_only)` - List certificates of insurance
   - `check_policy_status(dot_number)` - Check policy status by DOT
   - `get_claims_history(insured_id, years)` - Get claims history

4. **Knowledge Tools** (`app/tools/knowledge.py`)
   - `get_process_info(topic)` - Get process documentation (broker bonds, cargo claims, etc.)
   - `get_coverage_info(coverage_type)` - Get coverage explanations
   - `get_compliance_requirements(requirement_type)` - Get FMCSA compliance info

### Project Structure

```
rms-agent-v3/
├── app/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── agent.py             # Agent implementation with LangWatch
│   └── tools/
│       ├── __init__.py
│       ├── dot_lookup.py    # FMCSA/DOT lookup tools
│       ├── close_crm.py     # Close CRM integration
│       ├── nowcerts.py      # NowCerts AMS integration
│       └── knowledge.py     # Insurance knowledge base
├── prompts/
│   └── rms-insurance-agent.yaml  # Main agent prompt
├── tests/
│   ├── conftest.py
│   ├── scenarios/           # Scenario tests
│   │   └── test_rms_agent.py
│   └── evaluations/         # Evaluation notebooks
├── prompts.json             # Prompt registry
├── pyproject.toml           # Project dependencies
└── .env                     # Environment variables
```

---

## Core Principles

### 1. Scenario Agent Testing

Scenario allows for end-to-end validation of multi-turn conversations. Most agent functionality should be tested with Scenario tests.

**CRITICAL**: Every new agent feature MUST be tested with Scenario tests before considering it complete.

Best practices:
- NEVER check for regex or word matches in agent responses - use judge criteria instead
- Use functions for deterministic checks (tool calls, database entries, etc.)
- Write as few scenarios as possible while covering key paths
- Run single scenarios when debugging: `pytest tests/scenarios/test_file.py::test_name -v`
- ALWAYS consult the Scenario docs through the LangWatch MCP

Example test pattern:
```python
@pytest.mark.asyncio
async def test_dot_lookup():
    result = await scenario.run(
        name="DOT lookup",
        description="User asks to look up a DOT number",
        agents=[
            RMSAgentAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(criteria=[
                "Agent provides carrier name and operating status",
                "Response is professional and helpful",
            ]),
        ],
        script=[
            scenario.user("Look up DOT 1234567"),
            scenario.agent(),
            scenario.succeed(),
        ],
    )
    assert result.success
```

### 2. Prompt Management

Prompts are stored in `prompts/` as YAML files and registered in `prompts.json`.

Never hardcode prompts in code. Load them from files:
```python
prompt_config = load_prompt_from_file("rms-insurance-agent")
agent = Agent(
    model=OpenAIChat(id=prompt_config["model"]),
    instructions=prompt_config["instructions"],
)
```

### 3. Agent Reuse

**CRITICAL**: Never create agents in loops. Create once, reuse always:

```python
# WRONG
for query in queries:
    agent = Agent(...)  # DON'T DO THIS

# CORRECT
agent = Agent(...)
for query in queries:
    agent.run(query)
```

The agent uses a singleton pattern in `app/agent.py`:
```python
_agent_instance = None

def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = Agent(...)
    return _agent_instance
```

---

## Development Workflow

### Adding a New Tool

1. Create the tool in `app/tools/`:
```python
from agno.tools import Toolkit

class MyNewTools(Toolkit):
    def __init__(self, **kwargs):
        tools = [self.my_tool_function]
        super().__init__(name="my_tools", tools=tools, **kwargs)

    def my_tool_function(self, param: str) -> str:
        """Tool description for the LLM."""
        return "result"
```

2. Add to agent in `app/agent.py`:
```python
from app.tools.my_new_tools import MyNewTools

_agent_instance = Agent(
    tools=[
        DOTLookupTools(),
        MyNewTools(),  # Add here
    ],
)
```

3. Write Scenario test in `tests/scenarios/`:
```python
@pytest.mark.asyncio
async def test_my_new_feature():
    result = await scenario.run(
        name="my feature test",
        description="Test description",
        agents=[RMSAgentAdapter(), ...],
        ...
    )
    assert result.success
```

4. Run the test:
```bash
uv run pytest tests/scenarios/test_file.py::test_my_new_feature -v
```

### Running the Agent

**CLI Interactive Mode:**
```bash
uv run python -m app.main
```

**Single Task:**
```bash
uv run python -m app.main "Look up DOT 1234567"
```

**Running Tests:**
```bash
# All tests
uv run pytest tests/scenarios/ -v

# Single test
uv run pytest tests/scenarios/test_rms_agent.py::test_dot_number_lookup -v
```

---

## Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=sk-...          # Required for agent
LANGWATCH_API_KEY=...          # Required for tracing
CLOSE_API_KEY=...              # For CRM integration
NOWCERTS_API_KEY=...           # For NowCerts integration
FMCSA_API_KEY=...              # For DOT lookups (optional)
```

---

## Resources

- **Agno Documentation**: https://docs.agno.com/
- **Scenario Documentation**: https://scenario.langwatch.ai/
- **LangWatch Dashboard**: https://app.langwatch.ai/
- **FMCSA API**: https://mobile.fmcsa.dot.gov/QCDevsite/

---

## Guidelines Summary

### Always:
- Use Scenario tests for agent features
- Store prompts in YAML files
- Reuse agent instances
- Use judge criteria (not regex) for test assertions
- Load environment variables with dotenv

### Never:
- Hardcode prompts in code
- Create agents in loops
- Check for exact word matches in tests
- Commit API keys or `.env` file
- Skip testing new features
