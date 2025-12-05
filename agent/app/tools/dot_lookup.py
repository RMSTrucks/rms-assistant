"""
DOT Lookup Tools

Tools for looking up carrier information from FMCSA database.
"""

import os
import httpx
from agno.tools.toolkit import Toolkit
from pydantic import BaseModel
from typing import Optional

from app.observability import observe_tool


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

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DOT lookup tools.

        Args:
            api_key: FMCSA API key (optional, uses env var if not provided)
        """
        super().__init__(name="dot_lookup")

        self.api_key = api_key or os.getenv("FMCSA_API_KEY")
        self.base_url = "https://mobile.fmcsa.dot.gov/qc/services"

        # Register tools explicitly
        self.register(self.lookup_dot_number)
        self.register(self.search_carriers)
        self.register(self.check_safety_rating)

    @observe_tool
    def lookup_dot_number(self, dot_number: str) -> str:
        """
        Look up carrier information by DOT number from FMCSA database.

        Args:
            dot_number: The DOT number to look up (e.g., "1234567")

        Returns:
            str: Carrier information including name, address, operating status,
                 MC number, power units, and drivers
        """
        if not dot_number or not dot_number.strip().isdigit():
            return f"Invalid DOT number format: {dot_number}. DOT numbers should be numeric."

        dot_number = dot_number.strip()

        if not self.api_key:
            return "Error: FMCSA_API_KEY not configured. Set it in .env file."

        url = f"{self.base_url}/carriers/{dot_number}"
        params = {"webKey": self.api_key}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 404:
                    return f"No carrier found with DOT number: {dot_number}"

                if response.status_code != 200:
                    return f"FMCSA API error (status {response.status_code}): {response.text[:200]}"

                data = response.json()

        except httpx.TimeoutException:
            return "Error: FMCSA API request timed out. Try again."
        except Exception as e:
            return f"Error calling FMCSA API: {str(e)}"

        # Parse the response - FMCSA returns nested structure
        content = data.get("content", {})
        carrier = content.get("carrier", {})

        if not carrier:
            return f"No carrier data returned for DOT {dot_number}"

        # Extract carrier info
        legal_name = carrier.get("legalName", "Unknown")
        dba_name = carrier.get("dbaName", "")
        entity_type = carrier.get("carrierOperation", {}).get("carrierOperationDesc", "Unknown")
        oos_flag = carrier.get("oosFlag", "N")
        oos_status = "YES - OUT OF SERVICE" if oos_flag == "Y" else "No"

        # Address
        phy_street = carrier.get("phyStreet", "")
        phy_city = carrier.get("phyCity", "")
        phy_state = carrier.get("phyState", "")
        phy_zip = carrier.get("phyZipcode", "")
        address = f"{phy_street}, {phy_city}, {phy_state} {phy_zip}".strip(", ")

        phone = carrier.get("telephone", "")

        # MC/MX numbers from docket numbers
        docket_numbers = carrier.get("docketNumbers", [])
        mc_number = ""
        for docket in docket_numbers:
            prefix = docket.get("prefix", "")
            number = docket.get("docketNumber", "")
            if prefix in ("MC", "FF", "MX"):
                mc_number = f"{prefix}-{number}"
                break

        # Fleet info
        power_units = carrier.get("totalPowerUnits", 0) or 0
        drivers = carrier.get("totalDrivers", 0) or 0
        mcs150_date = carrier.get("mcs150FormDate", "Unknown")

        # Operating status from allowedToOperate
        allowed = carrier.get("allowedToOperate", "")
        if allowed == "Y":
            op_status = "AUTHORIZED"
        elif allowed == "N":
            op_status = "NOT AUTHORIZED"
        else:
            op_status = carrier.get("statusCode", "Unknown")

        # Build output
        output = [f"DOT Number: {dot_number}"]
        output.append(f"Legal Name: {legal_name}")
        if dba_name:
            output.append(f"DBA: {dba_name}")
        output.append(f"Entity Type: {entity_type}")
        output.append(f"Operating Status: {op_status}")
        output.append(f"Physical Address: {address}")
        if phone:
            output.append(f"Phone: {phone}")
        if mc_number:
            output.append(f"MC/MX Number: {mc_number}")
        output.append(f"Power Units: {power_units}")
        output.append(f"Drivers: {drivers}")
        output.append(f"MCS-150 Date: {mcs150_date}")
        output.append(f"Out of Service: {oos_status}")

        return "\n".join(output)

    @observe_tool
    def search_carriers(self, company_name: str, state: Optional[str] = None) -> str:
        """
        Search for carriers by company name.

        Args:
            company_name: Name or partial name of the company to search
            state: Optional state abbreviation to filter results (e.g., "TX")

        Returns:
            str: List of matching carriers with DOT numbers
        """
        if not company_name or len(company_name.strip()) < 2:
            return "Error: Company name must be at least 2 characters."

        if not self.api_key:
            return "Error: FMCSA_API_KEY not configured."

        # URL encode the company name for the API
        import urllib.parse
        encoded_name = urllib.parse.quote(company_name.strip())
        url = f"{self.base_url}/carriers/name/{encoded_name}"
        params = {"webKey": self.api_key}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)

                if response.status_code != 200:
                    return f"FMCSA API error (status {response.status_code})"

                data = response.json()

        except httpx.TimeoutException:
            return "Error: FMCSA API request timed out."
        except Exception as e:
            return f"Error calling FMCSA API: {str(e)}"

        content = data.get("content", [])
        if not content:
            return f'No carriers found matching "{company_name}"'

        # Filter by state if provided
        if state:
            state = state.upper().strip()
            content = [c for c in content if c.get("phyState", "").upper() == state]
            if not content:
                return f'No carriers found matching "{company_name}" in {state}'

        # Limit results
        content = content[:10]

        output = [f'Search results for "{company_name}"' + (f" in {state}" if state else "") + ":"]
        output.append("")

        for i, carrier in enumerate(content, 1):
            dot = carrier.get("dotNumber", "?")
            name = carrier.get("legalName", "Unknown")
            city = carrier.get("phyCity", "")
            st = carrier.get("phyState", "")
            allowed = carrier.get("allowedToOperate", "")
            status = "AUTHORIZED" if allowed == "Y" else "NOT AUTHORIZED" if allowed == "N" else "?"

            location = f"({city}, {st})" if city else ""
            output.append(f"{i}. DOT: {dot} - {name} {location} - {status}")

        output.append("")
        output.append(f"Found {len(content)} carrier(s). Use lookup_dot_number for details.")
        return "\n".join(output)

    @observe_tool
    def check_safety_rating(self, dot_number: str) -> str:
        """
        Check the safety rating and inspection history for a carrier.

        Args:
            dot_number: The DOT number to check

        Returns:
            str: Safety rating, BASIC scores, and recent inspection summary
        """
        if not dot_number or not dot_number.strip().isdigit():
            return f"Invalid DOT number format: {dot_number}"

        dot_number = dot_number.strip()

        if not self.api_key:
            return "Error: FMCSA_API_KEY not configured."

        # Get BASIC scores
        url = f"{self.base_url}/carriers/{dot_number}/basics"
        params = {"webKey": self.api_key}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)

                if response.status_code == 404:
                    return f"No safety data found for DOT {dot_number}"

                if response.status_code != 200:
                    return f"FMCSA API error (status {response.status_code})"

                data = response.json()

        except httpx.TimeoutException:
            return "Error: FMCSA API request timed out."
        except Exception as e:
            return f"Error calling FMCSA API: {str(e)}"

        content = data.get("content", {})

        # Handle empty content (small carriers without BASIC data)
        if not content or content == []:
            return f"""Safety Information for DOT {dot_number}:

No BASIC scores available.
This carrier likely has insufficient inspection data (common for small fleets).

Check FMCSA SAFER for more details: https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string={dot_number}"""

        carrier = content.get("carrier", {})
        basics = content.get("basicsResult", [])

        output = [f"Safety Information for DOT {dot_number}:"]
        output.append("")

        # Safety rating from carrier info
        safety_rating = carrier.get("safetyRating", "Not Rated")
        rating_date = carrier.get("safetyRatingDate", "")
        oos_flag = carrier.get("oosFlag", "N")

        output.append(f"Safety Rating: {safety_rating if safety_rating else 'Not Rated'}")
        if rating_date:
            output.append(f"Rating Date: {rating_date}")

        if oos_flag == "Y":
            output.append("*** OUT OF SERVICE ***")

        # BASIC scores
        if basics:
            output.append("")
            output.append("BASIC Scores (percentile):")

            basic_names = {
                "Unsafe Driving": "unsafeDriving",
                "Hours-of-Service": "hos",
                "Driver Fitness": "driverFitness",
                "Controlled Substances": "controlledSubstance",
                "Vehicle Maintenance": "vehicleMaintenance",
                "Hazmat Compliance": "hazmat",
                "Crash Indicator": "crashIndicator"
            }

            for display_name, key in basic_names.items():
                for basic in basics:
                    if basic.get("basicsType", "").lower().replace(" ", "").replace("-", "") == key.lower():
                        percentile = basic.get("basicsPercentile", "N/A")
                        if percentile != "N/A":
                            output.append(f"- {display_name}: {percentile}%")
                        else:
                            output.append(f"- {display_name}: N/A")
                        break
                else:
                    output.append(f"- {display_name}: N/A")

        # Inspection summary
        vehicle_insp = carrier.get("vehicleInspections", 0) or 0
        driver_insp = carrier.get("driverInspections", 0) or 0
        vehicle_oos = carrier.get("vehicleOosInsp", 0) or 0
        driver_oos = carrier.get("driverOosInsp", 0) or 0

        if vehicle_insp or driver_insp:
            output.append("")
            output.append("Inspection Summary (24 months):")
            output.append(f"- Vehicle Inspections: {vehicle_insp}")
            if vehicle_insp > 0:
                vehicle_oos_rate = (vehicle_oos / vehicle_insp) * 100
                output.append(f"- Vehicle OOS Rate: {vehicle_oos_rate:.1f}%")
            output.append(f"- Driver Inspections: {driver_insp}")
            if driver_insp > 0:
                driver_oos_rate = (driver_oos / driver_insp) * 100
                output.append(f"- Driver OOS Rate: {driver_oos_rate:.1f}%")

        return "\n".join(output)
