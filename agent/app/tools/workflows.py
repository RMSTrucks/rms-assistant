"""
Workflow Tools

Cross-system workflows that combine DOT, Close, and NowCerts data.
These are the power tools - one command, multiple systems.
"""

import os
from agno.tools.toolkit import Toolkit
from typing import Optional

from app.observability import observe_tool
from app.tools.dot_lookup import DOTLookupTools
from app.tools.close_crm import CloseCRMTools
from app.tools.nowcerts import NowCertsTools


class WorkflowTools(Toolkit):
    """Cross-system workflow tools for RMS operations."""

    def __init__(self):
        """Initialize workflow tools with access to all systems."""
        super().__init__(name="workflows")

        # Initialize sub-tools
        self.dot = DOTLookupTools()
        self.close = CloseCRMTools()
        self.nowcerts = NowCertsTools()

        # Register workflows
        self.register(self.carrier_snapshot)
        self.register(self.new_prospect)
        self.register(self.renewal_check)

    @observe_tool
    def carrier_snapshot(self, dot_number: str) -> str:
        """
        Get a complete snapshot of a carrier across all systems.

        Pulls data from FMCSA, Close CRM, and NowCerts in one call.
        This is your go-to tool for carrier research.

        Args:
            dot_number: The DOT number to look up

        Returns:
            str: Unified view with DOT info, CRM status, and policy status
        """
        if not dot_number:
            return "Error: DOT number is required"

        dot_number = dot_number.strip()
        output = [f"=== CARRIER SNAPSHOT: DOT {dot_number} ===", ""]

        # 1. FMCSA/DOT Data
        output.append("--- FMCSA DATA ---")
        dot_info = self.dot.lookup_dot_number(dot_number)
        if "Error" in dot_info or "Invalid" in dot_info:
            output.append(f"Not found in FMCSA: {dot_info}")
        else:
            output.append(dot_info)
        output.append("")

        # 2. Close CRM Status
        output.append("--- CLOSE CRM ---")
        close_info = self.close.get_lead_by_dot(dot_number)
        if "No lead found" in close_info:
            output.append("Not in Close CRM (new prospect)")
        else:
            output.append(close_info)
        output.append("")

        # 3. NowCerts Policy Status
        output.append("--- NOWCERTS ---")
        nowcerts_info = self.nowcerts.search_by_dot(dot_number)
        if "No insured found" in nowcerts_info:
            output.append("Not in NowCerts (no policies)")
        else:
            output.append(nowcerts_info)
        output.append("")

        # Summary
        output.append("--- SUMMARY ---")
        in_close = "No lead found" not in close_info
        in_nowcerts = "No insured found" not in nowcerts_info
        in_fmcsa = "Error" not in dot_info and "Invalid" not in dot_info and "No carrier" not in dot_info

        if in_fmcsa:
            output.append("FMCSA: Found")
        else:
            output.append("FMCSA: Not found")

        if in_close:
            output.append("Close: Existing lead")
        else:
            output.append("Close: New prospect")

        if in_nowcerts:
            output.append("NowCerts: Has policies")
        else:
            output.append("NowCerts: No policies")

        return "\n".join(output)

    @observe_tool
    def new_prospect(
        self,
        dot_number: str,
        notes: Optional[str] = None,
    ) -> str:
        """
        Create a new prospect from a DOT number.

        Looks up carrier info from FMCSA and creates a lead in Close.
        Checks NowCerts to see if they're already a customer.

        Args:
            dot_number: The DOT number for the prospect
            notes: Optional notes to add to the lead

        Returns:
            str: Summary of what was created and found
        """
        if not dot_number:
            return "Error: DOT number is required"

        dot_number = dot_number.strip()
        output = [f"=== NEW PROSPECT: DOT {dot_number} ===", ""]

        # 1. Check if already in Close
        close_check = self.close.get_lead_by_dot(dot_number)
        if "No lead found" not in close_check:
            output.append("ALREADY IN CLOSE:")
            output.append(close_check)
            output.append("")
            output.append("Lead already exists - no new lead created.")
            return "\n".join(output)

        # 2. Get DOT info from FMCSA
        dot_info = self.dot.lookup_dot_number(dot_number)
        if "Error" in dot_info or "Invalid" in dot_info or "No carrier" in dot_info:
            return f"Cannot create prospect: {dot_info}"

        # Parse DOT info for lead creation
        lines = dot_info.split("\n")
        company_name = ""
        phone = ""
        address = ""

        for line in lines:
            if line.startswith("Legal Name:"):
                company_name = line.replace("Legal Name:", "").strip()
            elif line.startswith("Phone:"):
                phone = line.replace("Phone:", "").strip()
            elif line.startswith("Physical Address:"):
                address = line.replace("Physical Address:", "").strip()

        if not company_name:
            return "Error: Could not parse company name from DOT data"

        # 3. Check NowCerts for existing customer
        nowcerts_check = self.nowcerts.search_by_dot(dot_number)
        existing_customer = "No insured found" not in nowcerts_check

        # 4. Create lead in Close
        prospect_notes = f"DOT Lookup:\n{dot_info}"
        if existing_customer:
            prospect_notes += "\n\n** EXISTING CUSTOMER IN NOWCERTS **"
        if notes:
            prospect_notes += f"\n\nAdditional Notes:\n{notes}"

        create_result = self.close.create_lead(
            company_name=company_name,
            phone=phone if phone else None,
            dot_number=dot_number,
            notes=prospect_notes,
        )

        output.append("FMCSA INFO:")
        output.append(dot_info)
        output.append("")

        if existing_customer:
            output.append("NOWCERTS STATUS:")
            output.append("** EXISTING CUSTOMER - Has policies **")
            output.append("")

        output.append("CLOSE CRM:")
        output.append(create_result)

        return "\n".join(output)

    @observe_tool
    def renewal_check(self, days_out: int = 30) -> str:
        """
        Check for upcoming renewals and cross-reference with Close.

        Gets expiring policies from NowCerts and shows Close lead status.
        Perfect for renewal pipeline management.

        Args:
            days_out: Days to look ahead (default 30, max 90)

        Returns:
            str: Renewal pipeline with CRM status
        """
        if days_out < 1:
            days_out = 30
        if days_out > 90:
            days_out = 90

        output = [f"=== RENEWAL CHECK: Next {days_out} Days ===", ""]

        # Get expiring policies
        expiring = self.nowcerts.get_expiring_policies(days_out)

        if "No policies expiring" in expiring:
            output.append("No policies expiring in this timeframe.")
            return "\n".join(output)

        output.append(expiring)
        output.append("")
        output.append("Use carrier_snapshot(dot) for full details on any carrier.")

        return "\n".join(output)
