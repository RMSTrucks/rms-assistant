"""
Close CRM Tools

Tools for managing leads, contacts, and notes in Close CRM.
Uses the real Close API.
"""

import os
import httpx
from agno.tools.toolkit import Toolkit
from typing import Optional
from datetime import datetime

from app.observability import observe_tool


class CloseCRMTools(Toolkit):
    """Tools for interacting with Close CRM."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Close CRM tools.

        Args:
            api_key: Close API key (optional, uses env var if not provided)
        """
        super().__init__(name="close_crm")

        self.api_key = api_key or os.getenv("CLOSE_API_KEY")
        self.base_url = "https://api.close.com/api/v1"

        # Register tools explicitly
        self.register(self.search_leads)
        self.register(self.get_lead)
        self.register(self.get_lead_by_dot)
        self.register(self.add_note_to_lead)
        self.register(self.create_lead)
        self.register(self.update_lead_status)
        self.register(self.log_call)
        self.register(self.create_opportunity)
        self.register(self.update_custom_field)

    def _make_request(self, method: str, endpoint: str, json_data: dict = None, params: dict = None) -> dict:
        """Make authenticated request to Close API."""
        if not self.api_key:
            return {"error": "Close API key not configured"}

        url = f"{self.base_url}/{endpoint}"
        auth = (self.api_key, "")  # Basic auth: API key as username, empty password

        try:
            with httpx.Client(timeout=30.0) as client:
                if method == "GET":
                    response = client.get(url, auth=auth, params=params)
                elif method == "POST":
                    response = client.post(url, auth=auth, json=json_data)
                elif method == "PUT":
                    response = client.put(url, auth=auth, json=json_data)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code >= 400:
                    return {"error": f"API error {response.status_code}: {response.text[:500]}"}

                return response.json()
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    @observe_tool
    def search_leads(self, query: str, limit: int = 10) -> str:
        """
        Search for leads in Close CRM by name, email, phone, or custom field.

        Args:
            query: Search query (company name, contact name, phone, email, or DOT)
            limit: Maximum number of results (default 10)

        Returns:
            str: List of matching leads with details
        """
        if not query:
            return "Error: search query is required"

        # Use Close's search endpoint
        result = self._make_request("GET", "lead/", params={
            "query": query,
            "_limit": limit
        })

        if "error" in result:
            return f"Error searching leads: {result['error']}"

        leads = result.get("data", [])
        if not leads:
            return f'No leads found matching "{query}"'

        output = [f'Search results for "{query}":\n']
        for i, lead in enumerate(leads, 1):
            lead_id = lead.get("id", "unknown")
            name = lead.get("display_name", "Unknown Company")
            status = lead.get("status_label", "Unknown")

            # Get primary contact info
            contacts = lead.get("contacts", [])
            contact_info = ""
            if contacts:
                contact = contacts[0]
                contact_name = contact.get("name", "")
                phones = contact.get("phones", [])
                emails = contact.get("emails", [])
                phone = phones[0].get("phone", "") if phones else ""
                email = emails[0].get("email", "") if emails else ""
                contact_info = f"\n   Contact: {contact_name}"
                if phone:
                    contact_info += f" | Phone: {phone}"
                if email:
                    contact_info += f" | Email: {email}"

            # Get custom fields (look for DOT)
            custom = lead.get("custom", {})
            dot_field = ""
            for key, value in custom.items():
                if "dot" in key.lower() and value:
                    dot_field = f"\n   DOT: {value}"
                    break

            output.append(f"{i}. {lead_id} - {name}")
            output.append(f"   Status: {status}{contact_info}{dot_field}")
            output.append("")

        output.append(f"Found {len(leads)} lead(s)")
        return "\n".join(output)

    @observe_tool
    def get_lead(self, lead_id: str) -> str:
        """
        Get detailed information about a specific lead.

        Args:
            lead_id: The Close CRM lead ID (e.g., "lead_abc123")

        Returns:
            str: Full lead details including contacts, activities, custom fields
        """
        if not lead_id:
            return "Error: lead_id is required"

        result = self._make_request("GET", f"lead/{lead_id}/")

        if "error" in result:
            return f"Error fetching lead: {result['error']}"

        name = result.get("display_name", "Unknown")
        status = result.get("status_label", "Unknown")
        created = result.get("date_created", "")[:10]
        url = result.get("url", "")

        output = [f"Lead: {name}", f"ID: {lead_id}", f"Status: {status}", f"Created: {created}"]

        if url:
            output.append(f"URL: {url}")

        # Contacts
        contacts = result.get("contacts", [])
        if contacts:
            output.append("\nContacts:")
            for contact in contacts:
                cname = contact.get("name", "Unknown")
                title = contact.get("title", "")
                phones = [p.get("phone") for p in contact.get("phones", [])]
                emails = [e.get("email") for e in contact.get("emails", [])]
                output.append(f"  - {cname}{' (' + title + ')' if title else ''}")
                if phones:
                    output.append(f"    Phones: {', '.join(phones)}")
                if emails:
                    output.append(f"    Emails: {', '.join(emails)}")

        # Custom fields
        custom = result.get("custom", {})
        if custom:
            output.append("\nCustom Fields:")
            for key, value in custom.items():
                if value:
                    # Clean up the field name
                    field_name = key.replace("custom.", "").replace("_", " ").title()
                    output.append(f"  - {field_name}: {value}")

        # Addresses
        addresses = result.get("addresses", [])
        if addresses:
            output.append("\nAddresses:")
            for addr in addresses:
                parts = [addr.get("address_1", ""), addr.get("city", ""), addr.get("state", ""), addr.get("zipcode", "")]
                output.append(f"  - {', '.join(p for p in parts if p)}")

        return "\n".join(output)

    @observe_tool
    def get_lead_by_dot(self, dot_number: str) -> str:
        """
        Find a lead by DOT number.

        Searches custom fields for matching DOT. Faster than general search
        when you already have the DOT.

        Args:
            dot_number: The DOT number to search for

        Returns:
            str: Lead details if found, or "not found" message
        """
        if not dot_number:
            return "Error: DOT number is required"

        dot_number = dot_number.strip()

        # Search using DOT as query - Close searches custom fields
        result = self._make_request("GET", "lead/", params={
            "query": f"DOT:{dot_number} OR DOT {dot_number} OR {dot_number}",
            "_limit": 10
        })

        if "error" in result:
            return f"Error searching leads: {result['error']}"

        leads = result.get("data", [])

        # Filter for exact DOT match in custom fields
        matches = []
        for lead in leads:
            custom = lead.get("custom", {})
            for key, value in custom.items():
                if "dot" in key.lower() and str(value).strip() == dot_number:
                    matches.append(lead)
                    break

        if not matches:
            return f"No lead found with DOT {dot_number} in Close"

        # Return first match with full details
        lead = matches[0]
        lead_id = lead.get("id", "unknown")
        name = lead.get("display_name", "Unknown Company")
        status = lead.get("status_label", "Unknown")
        url = lead.get("url", "")

        output = [f"Lead Found - DOT {dot_number}:", ""]
        output.append(f"Lead ID: {lead_id}")
        output.append(f"Company: {name}")
        output.append(f"Status: {status}")

        # Contact info
        contacts = lead.get("contacts", [])
        if contacts:
            contact = contacts[0]
            cname = contact.get("name", "")
            phones = [p.get("phone") for p in contact.get("phones", [])]
            if cname:
                output.append(f"Contact: {cname}")
            if phones:
                output.append(f"Phone: {phones[0]}")

        if url:
            output.append(f"URL: {url}")

        if len(matches) > 1:
            output.append(f"\n({len(matches)} leads match this DOT)")

        return "\n".join(output)

    @observe_tool
    def create_opportunity(
        self,
        lead_id: str,
        value: float,
        note: Optional[str] = None,
        confidence: int = 50,
    ) -> str:
        """
        Create an opportunity (deal) on a lead.

        Args:
            lead_id: The Close CRM lead ID
            value: Deal value in dollars
            note: Optional note about the opportunity
            confidence: Win probability 0-100 (default 50)

        Returns:
            str: Confirmation with opportunity ID
        """
        if not lead_id:
            return "Error: lead_id is required"
        if value is None or value < 0:
            return "Error: value must be a positive number"

        # Clamp confidence
        if confidence < 0:
            confidence = 0
        if confidence > 100:
            confidence = 100

        opp_data = {
            "lead_id": lead_id,
            "value": int(value * 100),  # Close stores in cents
            "confidence": confidence,
        }

        if note:
            opp_data["note"] = note

        result = self._make_request("POST", "opportunity/", json_data=opp_data)

        if "error" in result:
            return f"Error creating opportunity: {result['error']}"

        opp_id = result.get("id", "unknown")
        status = result.get("status_label", "Active")

        return f"""Opportunity created!

Opportunity ID: {opp_id}
Lead: {lead_id}
Value: ${value:,.2f}
Confidence: {confidence}%
Status: {status}"""

    @observe_tool
    def update_custom_field(
        self,
        lead_id: str,
        field_name: str,
        value: str,
    ) -> str:
        """
        Update a custom field on a lead.

        Common fields: DOT Number, MC Number, Policy Number, etc.

        Args:
            lead_id: The Close CRM lead ID
            field_name: Name of the custom field (e.g., "DOT Number")
            value: Value to set

        Returns:
            str: Confirmation of update
        """
        if not lead_id:
            return "Error: lead_id is required"
        if not field_name:
            return "Error: field_name is required"

        # Close custom fields use the format custom.field_name
        # But we need the actual custom field ID - try common patterns
        custom_data = {field_name: value}

        result = self._make_request("PUT", f"lead/{lead_id}/", json_data={
            "custom": custom_data
        })

        if "error" in result:
            return f"Error updating custom field: {result['error']}"

        return f"""Custom field updated!

Lead: {lead_id}
Field: {field_name}
Value: {value}"""

    @observe_tool
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

        result = self._make_request("POST", "activity/note/", json_data={
            "lead_id": lead_id,
            "note": note
        })

        if "error" in result:
            return f"Error adding note: {result['error']}"

        note_id = result.get("id", "unknown")
        created = result.get("date_created", "")[:19].replace("T", " ")

        return f"""Note added successfully!

Note ID: {note_id}
Lead: {lead_id}
Created: {created}
Content: {note[:200]}{'...' if len(note) > 200 else ''}"""

    @observe_tool
    def create_lead(
        self,
        company_name: str,
        contact_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        dot_number: Optional[str] = None,
        address: Optional[str] = None,
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
            address: Company address (optional)
            notes: Initial notes for the lead (optional)

        Returns:
            str: New lead ID and confirmation
        """
        if not company_name:
            return "Error: company_name is required"

        # Build lead data
        lead_data = {
            "name": company_name,
        }

        # Add contact if provided
        if contact_name or email or phone:
            contact = {}
            if contact_name:
                contact["name"] = contact_name
            if email:
                contact["emails"] = [{"email": email, "type": "office"}]
            if phone:
                contact["phones"] = [{"phone": phone, "type": "office"}]
            lead_data["contacts"] = [contact]

        # Add custom fields (DOT number)
        # Note: This assumes there's a custom field for DOT - may need adjustment
        if dot_number:
            lead_data["custom"] = {"DOT Number": dot_number}

        result = self._make_request("POST", "lead/", json_data=lead_data)

        if "error" in result:
            return f"Error creating lead: {result['error']}"

        lead_id = result.get("id", "unknown")
        url = result.get("url", "")

        output = f"""Lead created successfully!

Lead ID: {lead_id}
Company: {company_name}"""

        if contact_name:
            output += f"\nContact: {contact_name}"
        if phone:
            output += f"\nPhone: {phone}"
        if email:
            output += f"\nEmail: {email}"
        if dot_number:
            output += f"\nDOT: {dot_number}"
        if url:
            output += f"\nURL: {url}"

        # Add initial note if provided
        if notes and lead_id != "unknown":
            note_result = self.add_note_to_lead(lead_id, notes)
            output += f"\n\nInitial note added."

        return output

    @observe_tool
    def update_lead_status(
        self, lead_id: str, status_id: str, reason: Optional[str] = None
    ) -> str:
        """
        Update the status of a lead.

        Args:
            lead_id: The Close CRM lead ID
            status_id: Status ID to set (use search_leads to see current statuses)
            reason: Optional reason for the status change (added as note)

        Returns:
            str: Confirmation of status update
        """
        if not lead_id:
            return "Error: lead_id is required"
        if not status_id:
            return "Error: status_id is required"

        result = self._make_request("PUT", f"lead/{lead_id}/", json_data={
            "status_id": status_id
        })

        if "error" in result:
            return f"Error updating status: {result['error']}"

        new_status = result.get("status_label", "Unknown")

        output = f"""Lead status updated!

Lead ID: {lead_id}
New Status: {new_status}"""

        # Add reason as note if provided
        if reason:
            self.add_note_to_lead(lead_id, f"Status changed to {new_status}: {reason}")
            output += f"\nReason logged: {reason}"

        return output

    @observe_tool
    def log_call(
        self,
        lead_id: str,
        duration_seconds: int = 0,
        direction: str = "outbound",
        note: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> str:
        """
        Log a phone call activity on a lead.

        Args:
            lead_id: The Close CRM lead ID
            duration_seconds: Call duration in seconds
            direction: Call direction - "outbound" or "inbound"
            note: Call notes/summary (optional)
            phone: Phone number called (optional)

        Returns:
            str: Confirmation of call logging
        """
        if not lead_id:
            return "Error: lead_id is required"

        call_data = {
            "lead_id": lead_id,
            "direction": direction,
            "duration": duration_seconds,
            "status": "completed",
        }

        if note:
            call_data["note"] = note
        if phone:
            call_data["phone"] = phone

        result = self._make_request("POST", "activity/call/", json_data=call_data)

        if "error" in result:
            return f"Error logging call: {result['error']}"

        call_id = result.get("id", "unknown")
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60

        return f"""Call logged successfully!

Call ID: {call_id}
Lead: {lead_id}
Direction: {direction.capitalize()}
Duration: {minutes}m {seconds}s
{f'Note: {note[:100]}...' if note and len(note) > 100 else f'Note: {note}' if note else ''}"""
