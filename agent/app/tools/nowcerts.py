"""
NowCerts Tools

Tools for managing insurance policies and certificates in NowCerts AMS.
"""

import os
from agno.tools import Toolkit
from typing import Optional
from datetime import datetime, timedelta


class NowCertsTools(Toolkit):
    """Tools for interacting with NowCerts Agency Management System."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize NowCerts tools.

        Args:
            api_key: NowCerts API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("NOWCERTS_API_KEY")

        tools = [
            self.search_insured,
            self.get_policy_details,
            self.list_certificates,
            self.check_policy_status,
            self.get_claims_history,
        ]
        super().__init__(name="nowcerts", tools=tools, **kwargs)

    def search_insured(
        self, query: str, search_type: str = "name"
    ) -> str:
        """
        Search for an insured in NowCerts.

        Args:
            query: Search term (name, DOT number, policy number, etc.)
            search_type: Type of search - "name", "dot", "policy", "phone"

        Returns:
            str: List of matching insureds with basic policy info
        """
        if not query:
            return "Error: search query is required"

        valid_types = ["name", "dot", "policy", "phone"]
        if search_type not in valid_types:
            return f"Error: Invalid search_type. Valid options: {', '.join(valid_types)}"

        # Mock search results
        return f"""NowCerts Search Results ({search_type}: "{query}"):

1. Insured ID: INS-001234
   Name: Sample Trucking Company LLC
   DOT: 1234567 | MC: MC-1234567
   Status: Active
   Policies: 3 active (AL, Cargo, GL)
   Agent: RMS Trucks

2. Insured ID: INS-005678
   Name: {query} Transport Inc
   DOT: 2345678 | MC: MC-2345678
   Status: Active
   Policies: 2 active (AL, Cargo)
   Agent: RMS Trucks

Found 2 insureds matching your search."""

    def get_policy_details(self, policy_number: str) -> str:
        """
        Get detailed information about a specific policy.

        Args:
            policy_number: The policy number to look up

        Returns:
            str: Full policy details including coverage, limits, and dates
        """
        if not policy_number:
            return "Error: policy_number is required"

        today = datetime.now()
        eff_date = (today - timedelta(days=180)).strftime("%Y-%m-%d")
        exp_date = (today + timedelta(days=185)).strftime("%Y-%m-%d")

        # Mock policy details
        return f"""Policy Details: {policy_number}

Insured: Sample Trucking Company LLC
DOT: 1234567

Policy Type: Commercial Auto Liability
Carrier: National Indemnity Company
Status: In Force

Effective Date: {eff_date}
Expiration Date: {exp_date}
Premium: $45,000

Coverage:
- Combined Single Limit: $1,000,000
- Underinsured Motorist: $1,000,000
- Medical Payments: $5,000

Vehicles Covered: 15 power units
Drivers Listed: 18

Filing Status:
- BMC-91 Filed: Yes
- BMC-91X Filed: Yes
- State Filings: TX, OK, AR, LA

Documents:
- Certificate of Insurance
- Policy Declarations
- Driver Schedule
- Vehicle Schedule"""

    def list_certificates(
        self, insured_id: str, active_only: bool = True
    ) -> str:
        """
        List certificates of insurance for an insured.

        Args:
            insured_id: The NowCerts insured ID
            active_only: Only show active certificates (default: True)

        Returns:
            str: List of certificates with holder information
        """
        if not insured_id:
            return "Error: insured_id is required"

        filter_text = "Active" if active_only else "All"
        today = datetime.now()
        exp_date = (today + timedelta(days=185)).strftime("%Y-%m-%d")

        # Mock certificate list
        return f"""{filter_text} Certificates for {insured_id}:

1. CERT-2024-001
   Holder: ABC Freight Brokers LLC
   Type: Standard COI
   Issued: 2024-01-15
   Expires: {exp_date}
   Coverages: AL ($1M), Cargo ($100K)

2. CERT-2024-002
   Holder: XYZ Logistics Inc
   Type: Standard COI + Additional Insured
   Issued: 2024-01-20
   Expires: {exp_date}
   Coverages: AL ($1M), Cargo ($100K), GL ($1M)

3. CERT-2024-003
   Holder: Delta Shippers Corp
   Type: Standard COI
   Issued: 2024-02-01
   Expires: {exp_date}
   Coverages: AL ($1M)

Total: 3 {filter_text.lower()} certificates on file."""

    def check_policy_status(self, dot_number: str) -> str:
        """
        Check the current policy status for a carrier by DOT number.

        Args:
            dot_number: The carrier's DOT number

        Returns:
            str: Summary of all active policies and their status
        """
        if not dot_number:
            return "Error: dot_number is required"

        today = datetime.now()
        exp_date = (today + timedelta(days=185)).strftime("%Y-%m-%d")

        # Mock policy status
        return f"""Policy Status for DOT {dot_number}:

Insured: Sample Trucking Company LLC
Account Status: Active - Good Standing

Active Policies:
✓ Auto Liability (POL-AL-001)
  - Carrier: National Indemnity
  - Limit: $1,000,000 CSL
  - Expires: {exp_date}
  - Premium Paid: Yes

✓ Cargo Insurance (POL-CARGO-001)
  - Carrier: Great West Casualty
  - Limit: $100,000
  - Expires: {exp_date}
  - Premium Paid: Yes

✓ General Liability (POL-GL-001)
  - Carrier: Zurich
  - Limit: $1,000,000 per occurrence
  - Expires: {exp_date}
  - Premium Paid: Yes

Compliance:
✓ All FMCSA filings current
✓ No lapses in coverage
✓ No pending cancellations"""

    def get_claims_history(
        self, insured_id: str, years: int = 3
    ) -> str:
        """
        Get claims history for an insured.

        Args:
            insured_id: The NowCerts insured ID
            years: Number of years of history to retrieve (default: 3)

        Returns:
            str: Summary of claims history
        """
        if not insured_id:
            return "Error: insured_id is required"

        # Mock claims history
        return f"""Claims History for {insured_id} (Past {years} Years):

Summary:
- Total Claims: 2
- Open Claims: 0
- Total Paid: $35,000
- Total Reserved: $0

Claims Detail:

1. Claim #CLM-2023-001
   Date of Loss: 2023-06-15
   Type: Cargo
   Description: Water damage to freight
   Status: Closed - Paid
   Amount Paid: $15,000
   Subrogation: None

2. Claim #CLM-2022-003
   Date of Loss: 2022-09-22
   Type: Auto Liability
   Description: Minor collision - parking lot
   Status: Closed - Paid
   Amount Paid: $20,000
   Subrogation: $8,000 recovered

Loss Ratio: 0.35 (Favorable)
Renewal Impact: Neutral - good claims history"""
