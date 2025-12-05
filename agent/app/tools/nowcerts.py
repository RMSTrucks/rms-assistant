"""
NowCerts Tools

Tools for managing insurance policies and certificates in NowCerts AMS.
Uses real NowCerts API with bearer token authentication.
"""

import os
import time
import httpx
from agno.tools.toolkit import Toolkit
from typing import Optional
from datetime import datetime, timedelta

from app.observability import observe_tool


class NowCertsTools(Toolkit):
    """Tools for interacting with NowCerts Agency Management System."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize NowCerts tools.

        Args:
            username: NowCerts username (uses NOWCERTS_USERNAME env var if not provided)
            password: NowCerts password (uses NOWCERTS_PASSWORD env var if not provided)
            access_token: Pre-existing access token (uses NOWCERTS_ACCESS_TOKEN if not provided)
            refresh_token: Pre-existing refresh token (uses NOWCERTS_REFRESH_TOKEN if not provided)
        """
        super().__init__(name="nowcerts")

        self.username = username or os.getenv("NOWCERTS_USERNAME")
        self.password = password or os.getenv("NOWCERTS_PASSWORD")
        self.access_token = access_token or os.getenv("NOWCERTS_ACCESS_TOKEN")
        self.refresh_token = refresh_token or os.getenv("NOWCERTS_REFRESH_TOKEN")
        self.token_expires_at = 0
        self.base_url = "https://api.nowcerts.com"
        self.identity_url = "https://identity.nowcerts.com"

        # Register tools explicitly
        self.register(self.search_insured)
        self.register(self.search_by_dot)
        self.register(self.get_insured_details)
        self.register(self.list_policies)
        self.register(self.get_policy_details)
        self.register(self.list_certificates)
        self.register(self.get_expiring_policies)

    def _get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if needed."""
        # If we have a token and haven't tracked expiry yet, try it first
        if self.access_token and self.token_expires_at == 0:
            # First use - assume token is valid, set expiry to 1 hour from now
            self.token_expires_at = time.time() + 3600
            return self.access_token

        # If we have a valid token (not expired), use it
        if self.access_token and self.token_expires_at > time.time() + 300:
            return self.access_token

        # Try to refresh token
        if self.refresh_token:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{self.identity_url}/connect/token",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        data={
                            "grant_type": "refresh_token",
                            "refresh_token": self.refresh_token,
                            "client_id": "nowcerts_public_api",
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        self.access_token = data.get("access_token")
                        self.refresh_token = data.get("refresh_token", self.refresh_token)
                        expires_in = data.get("expires_in", 3600)
                        self.token_expires_at = time.time() + expires_in
                        return self.access_token
            except Exception as e:
                print(f"[NowCerts] Token refresh failed: {e}")

        # Try username/password auth
        if self.username and self.password:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{self.identity_url}/connect/token",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        data={
                            "grant_type": "password",
                            "username": self.username,
                            "password": self.password,
                            "client_id": "nowcerts_public_api",
                            "scope": "public_api offline_access",
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        self.access_token = data.get("access_token")
                        self.refresh_token = data.get("refresh_token")
                        expires_in = data.get("expires_in", 3600)
                        self.token_expires_at = time.time() + expires_in
                        return self.access_token
            except Exception as e:
                print(f"[NowCerts] Password auth failed: {e}")

        return None

    def _make_request(
        self, method: str, endpoint: str, params: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> dict:
        """Make authenticated request to NowCerts API."""
        token = self._get_valid_token()
        if not token:
            return {"error": "NowCerts authentication failed. Check credentials."}

        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                if method == "GET":
                    response = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = client.post(url, headers=headers, json=json_data)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code >= 400:
                    return {"error": f"NowCerts API error {response.status_code}: {response.text[:500]}"}

                return response.json()
        except httpx.TimeoutException:
            return {"error": "NowCerts request timed out"}
        except Exception as e:
            return {"error": f"NowCerts request failed: {str(e)}"}

    @observe_tool
    def search_insured(self, query: str, search_type: str = "name") -> str:
        """
        Search for an insured in NowCerts.

        Args:
            query: Search term (name, DOT number, phone, etc.)
            search_type: Type of search - "name", "dot", "phone", "email"

        Returns:
            str: List of matching insureds with basic info
        """
        if not query:
            return "Error: search query is required"

        # NowCerts requires $top, $skip, $orderby for InsuredList
        # Use client-side filtering for flexibility
        params = {
            "$top": "500",
            "$skip": "0",
            "$orderby": "commercialName",
        }

        result = self._make_request("GET", "/api/InsuredList()", params=params)

        # Client-side filter since OData contains() may not work
        if "value" in result:
            query_lower = query.lower()
            filtered = []
            for ins in result.get("value", []):
                name = (ins.get("commercialName") or f"{ins.get('firstName', '')} {ins.get('lastName', '')}").lower()
                phone = (ins.get("phone") or "").lower()
                email = (ins.get("email") or "").lower()
                if query_lower in name or query_lower in phone or query_lower in email:
                    filtered.append(ins)
            result["value"] = filtered[:20]  # Limit to 20 results

        if "error" in result:
            return f"Error searching NowCerts: {result['error']}"

        insureds = result.get("value", [])
        if not insureds:
            return f'No insureds found matching "{query}" ({search_type})'

        output = [f'NowCerts Search Results ({search_type}: "{query}"):\n']

        for i, insured in enumerate(insureds, 1):
            insured_id = insured.get("id", "unknown")
            name = insured.get("commercialName") or f"{insured.get('firstName', '')} {insured.get('lastName', '')}".strip()
            email = insured.get("email", "")
            phone = insured.get("phone", "")
            location = f"{insured.get('city', '')}, {insured.get('state', '')}".strip(", ")

            output.append(f"{i}. Insured ID: {insured_id}")
            output.append(f"   Name: {name or 'Unknown'}")
            if phone:
                output.append(f"   Phone: {phone}")
            if email:
                output.append(f"   Email: {email}")
            if location:
                output.append(f"   Location: {location}")
            output.append("")

        output.append(f"Found {len(insureds)} insured(s) matching your search.")
        return "\n".join(output)

    @observe_tool
    def search_by_dot(self, dot_number: str) -> str:
        """
        Search for an insured by DOT number in NowCerts.

        This is the fastest way to find a carrier when you have their DOT.

        Args:
            dot_number: The DOT number to search for

        Returns:
            str: Matching insured(s) with policy summary
        """
        if not dot_number:
            return "Error: DOT number is required"

        dot_number = dot_number.strip()

        # Fetch all insureds and filter client-side for DOT
        params = {
            "$top": "500",
            "$skip": "0",
            "$orderby": "commercialName",
        }

        result = self._make_request("GET", "/api/InsuredList()", params=params)

        if "error" in result:
            return f"Error searching NowCerts: {result['error']}"

        # Filter for DOT match in commercial name or custom fields
        insureds = result.get("value", [])
        matches = []

        for ins in insureds:
            # Check if DOT appears in name (common pattern: "Company Name - DOT 123456")
            name = ins.get("commercialName", "") or ""
            if dot_number in name:
                matches.append(ins)
                continue

            # Check custom fields for DOT
            # NowCerts may store DOT in different custom field names
            for key, value in ins.items():
                if "dot" in key.lower() and str(value) == dot_number:
                    matches.append(ins)
                    break

        if not matches:
            return f"No insured found with DOT {dot_number} in NowCerts"

        output = [f"NowCerts Search - DOT {dot_number}:\n"]

        for i, insured in enumerate(matches, 1):
            insured_id = insured.get("id", "unknown")
            name = insured.get("commercialName") or f"{insured.get('firstName', '')} {insured.get('lastName', '')}".strip()
            email = insured.get("email", "")
            phone = insured.get("phone", "")
            location = f"{insured.get('city', '')}, {insured.get('state', '')}".strip(", ")

            output.append(f"{i}. Insured ID: {insured_id}")
            output.append(f"   Name: {name or 'Unknown'}")
            if phone:
                output.append(f"   Phone: {phone}")
            if email:
                output.append(f"   Email: {email}")
            if location:
                output.append(f"   Location: {location}")
            output.append("")

        output.append(f"Found {len(matches)} insured(s) with DOT {dot_number}")
        output.append("Use list_policies(insured_id) for policy details.")
        return "\n".join(output)

    @observe_tool
    def get_expiring_policies(self, days_out: int = 30) -> str:
        """
        Get policies expiring within the specified number of days.

        Perfect for renewal pipeline management.

        Args:
            days_out: Number of days to look ahead (default 30)

        Returns:
            str: List of expiring policies with insured info and dates
        """
        if days_out < 1:
            days_out = 30
        if days_out > 90:
            days_out = 90  # Cap at 90 days

        # Calculate date range
        today = datetime.now()
        future_date = today + timedelta(days=days_out)

        # Fetch policies (OData filter may not work, use client-side)
        params = {
            "$top": "500",
            "$orderby": "expirationDate asc",
        }

        result = self._make_request("GET", "/api/PolicyList()", params=params)

        if "error" in result:
            return f"Error fetching policies: {result['error']}"

        policies = result.get("value", [])

        # Filter client-side for expiration date within range
        expiring = []
        for policy in policies:
            exp_str = policy.get("expirationDate", "")
            if not exp_str:
                continue

            try:
                # Parse ISO date
                exp_date = datetime.fromisoformat(exp_str.replace("Z", "+00:00").split("+")[0])
                if today <= exp_date <= future_date:
                    policy["_exp_date"] = exp_date
                    expiring.append(policy)
            except (ValueError, TypeError):
                continue

        if not expiring:
            return f"No policies expiring in the next {days_out} days"

        # Sort by expiration date
        expiring.sort(key=lambda p: p.get("_exp_date", today))

        output = [f"Policies Expiring in Next {days_out} Days:\n"]

        for i, policy in enumerate(expiring[:25], 1):  # Limit to 25
            policy_num = policy.get("policyNumber", "Unknown")
            policy_type = policy.get("policyType", "Unknown")
            insured_name = policy.get("insuredName", "Unknown")
            exp_date = policy.get("expirationDate", "")[:10]
            premium = policy.get("premium", 0)
            days_left = (policy.get("_exp_date") - today).days

            output.append(f"{i}. {policy_num} - {policy_type}")
            output.append(f"   Insured: {insured_name}")
            output.append(f"   Expires: {exp_date} ({days_left} days)")
            if premium:
                output.append(f"   Premium: ${premium:,.2f}")
            output.append("")

        total = len(expiring)
        output.append(f"Total: {total} policy(ies) expiring in next {days_out} days")
        if total > 25:
            output.append(f"(Showing first 25 of {total})")

        return "\n".join(output)

    @observe_tool
    def get_insured_details(self, insured_id: str) -> str:
        """
        Get detailed information about an insured.

        Args:
            insured_id: The NowCerts insured ID (GUID)

        Returns:
            str: Full insured details including contact info and policies
        """
        if not insured_id:
            return "Error: insured_id is required"

        result = self._make_request("GET", f"/api/InsuredList({insured_id})")

        if "error" in result:
            return f"Error fetching insured: {result['error']}"

        name = result.get("commercialName") or f"{result.get('firstName', '')} {result.get('lastName', '')}".strip()

        output = [f"Insured Details: {name}", f"ID: {insured_id}", ""]

        # Contact info
        if result.get("email"):
            output.append(f"Email: {result['email']}")
        if result.get("phone"):
            output.append(f"Phone: {result['phone']}")

        # Address
        addr_parts = [
            result.get("addressLine1", ""),
            result.get("city", ""),
            result.get("state", ""),
            result.get("zipCode", ""),
        ]
        addr = ", ".join(p for p in addr_parts if p)
        if addr:
            output.append(f"Address: {addr}")

        # Additional details
        if result.get("dateOfBirth"):
            output.append(f"DOB: {result['dateOfBirth'][:10]}")
        if result.get("licenseNumber"):
            output.append(f"License: {result['licenseNumber']}")

        return "\n".join(output)

    @observe_tool
    def list_policies(self, insured_id: str) -> str:
        """
        List policies for an insured.

        Args:
            insured_id: The NowCerts insured ID

        Returns:
            str: List of policies with status and coverage info
        """
        if not insured_id:
            return "Error: insured_id is required"

        # Get policies for this insured
        params = {
            "$filter": f"insuredId eq '{insured_id}'",
            "$select": "id,policyNumber,policyType,effectiveDate,expirationDate,status,premium",
            "$top": "50",
            "$orderby": "expirationDate desc",
        }

        result = self._make_request("GET", "/api/PolicyList()", params=params)

        if "error" in result:
            return f"Error fetching policies: {result['error']}"

        policies = result.get("value", [])
        if not policies:
            return f"No policies found for insured {insured_id}"

        output = [f"Policies for Insured {insured_id}:\n"]

        for i, policy in enumerate(policies, 1):
            policy_num = policy.get("policyNumber", "Unknown")
            policy_type = policy.get("policyType", "Unknown")
            status = policy.get("status", "Unknown")
            eff_date = policy.get("effectiveDate", "")[:10] if policy.get("effectiveDate") else "N/A"
            exp_date = policy.get("expirationDate", "")[:10] if policy.get("expirationDate") else "N/A"
            premium = policy.get("premium", 0)

            output.append(f"{i}. {policy_num} - {policy_type}")
            output.append(f"   Status: {status}")
            output.append(f"   Effective: {eff_date} to {exp_date}")
            if premium:
                output.append(f"   Premium: ${premium:,.2f}")
            output.append("")

        output.append(f"Total: {len(policies)} policy(ies)")
        return "\n".join(output)

    @observe_tool
    def get_policy_details(self, policy_id: str) -> str:
        """
        Get detailed information about a specific policy.

        Args:
            policy_id: The NowCerts policy ID

        Returns:
            str: Full policy details including coverage, limits, and dates
        """
        if not policy_id:
            return "Error: policy_id is required"

        result = self._make_request("GET", f"/api/PolicyList({policy_id})")

        if "error" in result:
            return f"Error fetching policy: {result['error']}"

        policy_num = result.get("policyNumber", "Unknown")
        policy_type = result.get("policyType", "Unknown")
        status = result.get("status", "Unknown")
        carrier = result.get("carrierName", "Unknown")
        eff_date = result.get("effectiveDate", "")[:10] if result.get("effectiveDate") else "N/A"
        exp_date = result.get("expirationDate", "")[:10] if result.get("expirationDate") else "N/A"
        premium = result.get("premium", 0)

        output = [
            f"Policy Details: {policy_num}",
            f"ID: {policy_id}",
            "",
            f"Type: {policy_type}",
            f"Carrier: {carrier}",
            f"Status: {status}",
            "",
            f"Effective Date: {eff_date}",
            f"Expiration Date: {exp_date}",
        ]

        if premium:
            output.append(f"Premium: ${premium:,.2f}")

        # Add coverage limits if available
        if result.get("limits"):
            output.append("\nCoverage Limits:")
            for limit in result.get("limits", []):
                output.append(f"  - {limit.get('description', 'Unknown')}: {limit.get('amount', 'N/A')}")

        return "\n".join(output)

    @observe_tool
    def list_certificates(self, insured_id: str, active_only: bool = True) -> str:
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

        params = {
            "$filter": f"insuredId eq '{insured_id}'",
            "$select": "id,certificateNumber,holderName,issueDate,expirationDate,status",
            "$top": "50",
            "$orderby": "issueDate desc",
        }

        if active_only:
            params["$filter"] += " and status eq 'Active'"

        result = self._make_request("GET", "/api/CertificateList()", params=params)

        if "error" in result:
            return f"Error fetching certificates: {result['error']}"

        certs = result.get("value", [])
        filter_text = "Active" if active_only else "All"

        if not certs:
            return f"No {filter_text.lower()} certificates found for insured {insured_id}"

        output = [f"{filter_text} Certificates for {insured_id}:\n"]

        for i, cert in enumerate(certs, 1):
            cert_id = cert.get("id", "unknown")
            cert_num = cert.get("certificateNumber", "N/A")
            holder = cert.get("holderName", "Unknown")
            issue_date = cert.get("issueDate", "")[:10] if cert.get("issueDate") else "N/A"
            exp_date = cert.get("expirationDate", "")[:10] if cert.get("expirationDate") else "N/A"
            status = cert.get("status", "Unknown")

            output.append(f"{i}. {cert_num}")
            output.append(f"   Holder: {holder}")
            output.append(f"   Issued: {issue_date}")
            output.append(f"   Expires: {exp_date}")
            output.append(f"   Status: {status}")
            output.append("")

        output.append(f"Total: {len(certs)} {filter_text.lower()} certificate(s)")
        return "\n".join(output)
