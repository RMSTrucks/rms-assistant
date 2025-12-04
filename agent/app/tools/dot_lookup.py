"""
DOT Lookup Tools

Tools for looking up carrier information from FMCSA database.
"""

import os
import httpx
from agno.tools import Toolkit
from pydantic import BaseModel
from typing import Optional


class CarrierInfo(BaseModel):
    """Carrier information from FMCSA"""
    dot_number: str
    legal_name: str
    dba_name: Optional[str] = None
    entity_type: str
    operating_status: str
    physical_address: str
    phone: Optional[str] = None
    mc_number: Optional[str] = None
    power_units: int = 0
    drivers: int = 0
    mcs150_date: Optional[str] = None
    out_of_service: bool = False


class DOTLookupTools(Toolkit):
    """Tools for looking up DOT/FMCSA carrier information."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize DOT lookup tools.

        Args:
            api_key: FMCSA API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("FMCSA_API_KEY")
        self.base_url = "https://mobile.fmcsa.dot.gov/qc/services"

        tools = [
            self.lookup_dot_number,
            self.search_carriers,
            self.check_safety_rating,
        ]
        super().__init__(name="dot_lookup", tools=tools, **kwargs)

    def lookup_dot_number(self, dot_number: str) -> str:
        """
        Look up carrier information by DOT number from FMCSA database.

        Args:
            dot_number: The DOT number to look up (e.g., "1234567")

        Returns:
            str: Carrier information including name, address, operating status,
                 MC number, power units, and drivers
        """
        # In production, this would call the FMCSA API
        # For now, return mock data for testing
        if not dot_number or not dot_number.isdigit():
            return f"Invalid DOT number format: {dot_number}. DOT numbers should be numeric."

        # Mock API call - in production, use:
        # url = f"{self.base_url}/carriers/{dot_number}"
        # params = {"webKey": self.api_key} if self.api_key else {}
        # response = httpx.get(url, params=params)

        # Mock response for development/testing
        return f"""DOT Number: {dot_number}
Legal Name: Sample Trucking Company LLC
DBA: Sample Trucking
Entity Type: CARRIER
Operating Status: AUTHORIZED FOR HHG
Physical Address: 123 Main St, Dallas, TX 75001
Phone: (555) 123-4567
MC Number: MC-{int(dot_number) + 100000}
Power Units: 15
Drivers: 18
MCS-150 Date: 2024-03-15
Out of Service: No

Insurance on file:
- BIPD Liability: $1,000,000 (Required: $750,000) ✓
- Cargo Insurance: $100,000 ✓
- Bond/Trust: BMC-84 on file ✓"""

    def search_carriers(self, company_name: str, state: Optional[str] = None) -> str:
        """
        Search for carriers by company name.

        Args:
            company_name: Name or partial name of the company to search
            state: Optional state abbreviation to filter results (e.g., "TX")

        Returns:
            str: List of matching carriers with DOT numbers
        """
        state_filter = f" in {state}" if state else ""

        # Mock response
        return f"""Search results for "{company_name}"{state_filter}:

1. DOT: 1234567 - Sample Trucking Company LLC (Dallas, TX) - AUTHORIZED
2. DOT: 2345678 - {company_name} Transport Inc (Houston, TX) - AUTHORIZED
3. DOT: 3456789 - {company_name} Logistics (Austin, TX) - NOT AUTHORIZED

Found 3 carriers matching your search. Use lookup_dot_number for detailed information."""

    def check_safety_rating(self, dot_number: str) -> str:
        """
        Check the safety rating and inspection history for a carrier.

        Args:
            dot_number: The DOT number to check

        Returns:
            str: Safety rating, BASIC scores, and recent inspection summary
        """
        if not dot_number or not dot_number.isdigit():
            return f"Invalid DOT number format: {dot_number}"

        # Mock response
        return f"""Safety Information for DOT {dot_number}:

Safety Rating: SATISFACTORY
Rating Date: 2023-08-15

BASIC Scores (percentile):
- Unsafe Driving: 45%
- Hours-of-Service: 32%
- Driver Fitness: 28%
- Controlled Substances: 0%
- Vehicle Maintenance: 55%
- Hazmat Compliance: N/A
- Crash Indicator: 22%

Recent Inspections (last 24 months):
- Total Inspections: 12
- Vehicle OOS Rate: 8.3% (National Avg: 20.7%)
- Driver OOS Rate: 4.2% (National Avg: 5.5%)

No active Out-of-Service orders."""
