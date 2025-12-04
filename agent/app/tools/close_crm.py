"""
Close CRM Tools

Tools for managing leads, contacts, and notes in Close CRM.
"""

import os
from agno.tools import Toolkit
from typing import Optional
from datetime import datetime


class CloseCRMTools(Toolkit):
    """Tools for interacting with Close CRM."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Close CRM tools.

        Args:
            api_key: Close API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("CLOSE_API_KEY")
        self.base_url = "https://api.close.com/api/v1"

        tools = [
            self.add_note_to_lead,
            self.create_lead,
            self.search_leads,
            self.update_lead_status,
            self.log_call,
        ]
        super().__init__(name="close_crm", tools=tools, **kwargs)

    def add_note_to_lead(self, lead_id: str, note: str) -> str:
        """
        Add a note to an existing lead in Close CRM.

        Args:
            lead_id: The Close CRM lead ID (e.g., "lead_abc123")
            note: The note content to add

        Returns:
            str: Confirmation of note creation
        """
        if not lead_id:
            return "Error: lead_id is required"
        if not note:
            return "Error: note content is required"

        # Mock API call - in production, use Close API
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""Note added successfully to {lead_id}

Note ID: note_{lead_id[-6:]}_001
Created: {timestamp}
Content: {note[:100]}{'...' if len(note) > 100 else ''}

The lead has been updated."""

    def create_lead(
        self,
        company_name: str,
        contact_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        dot_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """
        Create a new lead in Close CRM.

        Args:
            company_name: Name of the company
            contact_name: Primary contact name (optional)
            email: Contact email address (optional)
            phone: Contact phone number (optional)
            dot_number: DOT number if applicable (optional)
            notes: Initial notes for the lead (optional)

        Returns:
            str: New lead ID and confirmation
        """
        if not company_name:
            return "Error: company_name is required"

        # Mock lead creation
        lead_id = f"lead_{company_name[:3].lower()}{hash(company_name) % 10000:04d}"

        details = [f"Company: {company_name}"]
        if contact_name:
            details.append(f"Contact: {contact_name}")
        if email:
            details.append(f"Email: {email}")
        if phone:
            details.append(f"Phone: {phone}")
        if dot_number:
            details.append(f"DOT: {dot_number}")

        return f"""Lead created successfully!

Lead ID: {lead_id}
{chr(10).join(details)}
Status: New Lead
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{f"Initial note added: {notes[:50]}..." if notes else "No initial notes."}"""

    def search_leads(self, query: str, status: Optional[str] = None) -> str:
        """
        Search for leads in Close CRM.

        Args:
            query: Search query (company name, contact name, phone, email, or DOT)
            status: Optional status filter (e.g., "New Lead", "Qualified", "Quoted")

        Returns:
            str: List of matching leads
        """
        if not query:
            return "Error: search query is required"

        status_filter = f" (Status: {status})" if status else ""

        # Mock search results
        return f"""Search results for "{query}"{status_filter}:

1. lead_sam1234 - Sample Trucking Co
   Contact: John Smith | Phone: (555) 123-4567
   Status: Qualified | DOT: 1234567
   Last Activity: 2024-01-15

2. lead_sam5678 - {query} Transport LLC
   Contact: Jane Doe | Phone: (555) 987-6543
   Status: New Lead | DOT: 2345678
   Last Activity: 2024-01-20

3. lead_sam9012 - {query} Logistics Inc
   Contact: Bob Wilson | Phone: (555) 456-7890
   Status: Quoted | DOT: 3456789
   Last Activity: 2024-01-18

Found 3 leads matching your search."""

    def update_lead_status(
        self, lead_id: str, status: str, reason: Optional[str] = None
    ) -> str:
        """
        Update the status of a lead.

        Args:
            lead_id: The Close CRM lead ID
            status: New status (e.g., "Qualified", "Quoted", "Won", "Lost")
            reason: Optional reason for the status change

        Returns:
            str: Confirmation of status update
        """
        if not lead_id:
            return "Error: lead_id is required"
        if not status:
            return "Error: status is required"

        valid_statuses = ["New Lead", "Qualified", "Quoted", "Won", "Lost", "Nurture"]
        if status not in valid_statuses:
            return f"Error: Invalid status. Valid options: {', '.join(valid_statuses)}"

        return f"""Lead status updated successfully!

Lead ID: {lead_id}
New Status: {status}
Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{f"Reason: {reason}" if reason else ""}

Status change has been logged."""

    def log_call(
        self,
        lead_id: str,
        duration_minutes: int,
        direction: str = "outbound",
        summary: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> str:
        """
        Log a phone call activity on a lead.

        Args:
            lead_id: The Close CRM lead ID
            duration_minutes: Call duration in minutes
            direction: Call direction - "outbound" or "inbound"
            summary: Brief summary of the call (optional)
            outcome: Call outcome (optional, e.g., "interested", "callback", "not interested")

        Returns:
            str: Confirmation of call logging
        """
        if not lead_id:
            return "Error: lead_id is required"
        if duration_minutes < 0:
            return "Error: duration must be positive"

        return f"""Call logged successfully!

Lead ID: {lead_id}
Direction: {direction.capitalize()}
Duration: {duration_minutes} minutes
Logged: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{f"Summary: {summary}" if summary else ""}
{f"Outcome: {outcome}" if outcome else ""}

Call activity has been added to the lead timeline."""
