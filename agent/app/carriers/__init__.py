"""
Carrier Quote Automation Modules

Each carrier has its own module that handles the specific automation flow
for their quote wizard.

v2: Uses browser-use for LLM-driven form filling (no hardcoded selectors).
"""

from .progressive import run_progressive_quote
from .browser_agent import (
    fill_quote_form,
    fill_progressive_quote,
    fill_bhhc_quote,
    fill_geico_quote,
)

__all__ = [
    "run_progressive_quote",
    "fill_quote_form",
    "fill_progressive_quote",
    "fill_bhhc_quote",
    "fill_geico_quote",
]
