"""
Pytest configuration for RMS Agent tests.
"""

import os
import sys
import pytest
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "agent_test: marks tests as agent scenario tests"
    )


@pytest.fixture(scope="session", autouse=True)
def verify_environment():
    """Verify required environment variables are set."""
    required_vars = ["ANTHROPIC_API_KEY"]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}")
