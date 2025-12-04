"""
Knowledge Tools

Tools for answering questions about insurance processes and procedures.
"""

from agno.tools import Toolkit


class KnowledgeTools(Toolkit):
    """Tools for answering insurance knowledge questions."""

    def __init__(self, **kwargs):
        """Initialize knowledge tools."""
        tools = [
            self.get_process_info,
            self.get_coverage_info,
            self.get_compliance_requirements,
        ]
        super().__init__(name="knowledge", tools=tools, **kwargs)

    def get_process_info(self, topic: str) -> str:
        """
        Get information about an insurance process or procedure.

        Args:
            topic: The process or topic to get information about
                   (e.g., "broker bond", "cargo claim", "new policy", "certificate request")

        Returns:
            str: Detailed process information and steps
        """
        topic_lower = topic.lower()

        processes = {
            "broker bond": """Broker Bond (BMC-84) Process:

A broker bond (BMC-84) is required for freight brokers operating under FMCSA authority.

Requirements:
- Valid FMCSA broker authority (MC number)
- $75,000 surety bond or trust fund
- Must be filed with FMCSA before operating

Our Process:
1. Verify customer has MC authority (or pending application)
2. Collect application and financials
3. Submit to surety company for approval
4. Once approved, file BMC-84 with FMCSA
5. Provide proof of filing to customer

Timeline: 2-5 business days typically
Cost: Premium typically 1-10% of bond amount based on credit

Documents Needed:
- Broker authority letter or MC number
- Business financials (last 2 years)
- Personal financial statement
- Completed broker bond application""",

            "cargo claim": """Cargo Claims Process:

When a cargo claim is reported:

Immediate Steps:
1. Document the claim (date, load details, nature of damage/loss)
2. Get photos of damage if available
3. Obtain Bill of Lading and delivery receipt
4. Report to carrier within 24 hours if possible

Filing Process:
1. Complete carrier's claim form
2. Attach supporting documentation:
   - Bill of Lading
   - Delivery receipt with noted exceptions
   - Photos of damage
   - Invoice showing cargo value
   - Repair estimates if applicable
3. Submit to carrier within policy timeframe
4. Follow up regularly until resolved

Time Limits:
- Report to carrier: ASAP, within 9 months max
- File formal claim: Within 9 months of delivery
- Lawsuit if needed: Within 2 years

RMS Role:
- Assist with documentation
- Submit to insurance carrier
- Track and follow up on claim
- Advocate for customer""",

            "new policy": """New Policy Process:

Steps to Quote and Bind:

1. Gather Information:
   - DOT/MC number
   - Years in business
   - Driver list with MVRs
   - Vehicle schedule
   - Loss history (3-5 years)
   - Current coverage (if any)

2. Risk Assessment:
   - Run FMCSA safety report
   - Review BASIC scores
   - Analyze commodities hauled
   - Check operating radius

3. Submit to Markets:
   - Prepare submission package
   - Send to appropriate carriers
   - Follow up on quotes

4. Quote Presentation:
   - Review options with customer
   - Explain coverages and limits
   - Answer questions

5. Bind Coverage:
   - Collect signed applications
   - Obtain payment (deposit or full)
   - Request binder from carrier
   - File FMCSA filings if needed
   - Issue certificates as requested

Timeline: 3-7 business days for quotes""",

            "certificate request": """Certificate of Insurance Request Process:

Standard COI:
1. Verify policy is active
2. Generate certificate in NowCerts
3. Email or fax to requestor
4. File copy in system

Additional Insured Request:
1. Verify policy allows additional insureds
2. Review contract requirements
3. Check if AI endorsement is needed
4. Process endorsement if required
5. Generate certificate with AI status
6. Send to requestor

Turnaround:
- Standard COI: Same day
- With endorsement: 1-2 business days

Common Certificate Holders:
- Freight brokers
- Shippers
- Facilities/warehouses
- Lenders""",
        }

        # Try to find matching process
        for key, info in processes.items():
            if key in topic_lower:
                return info

        # Generic response if no match
        return f"""I don't have specific process documentation for "{topic}".

Common processes I can help with:
- Broker bond (BMC-84)
- Cargo claims
- New policy
- Certificate request

Please ask about one of these topics or provide more details about what you need."""

    def get_coverage_info(self, coverage_type: str) -> str:
        """
        Get information about a specific type of insurance coverage.

        Args:
            coverage_type: Type of coverage (e.g., "cargo", "auto liability", "physical damage")

        Returns:
            str: Coverage details, typical limits, and requirements
        """
        coverage_lower = coverage_type.lower()

        coverages = {
            "cargo": """Cargo Insurance Coverage:

What It Covers:
- Damage to freight being transported
- Theft of cargo
- Loss during loading/unloading

Standard Limits:
- $100,000 per occurrence (typical minimum)
- Some shippers require higher limits
- Reefer breakdown usually included

Exclusions:
- Normal shrinkage
- Inherent vice
- Nuclear hazard
- War/terrorism
- Intentional acts

FMCSA Requirements:
- Carriers of household goods: Required
- Other for-hire carriers: Not federally required but usually contractually required

Premium Factors:
- Commodities hauled
- Radius of operation
- Claims history
- Deductible chosen""",

            "auto liability": """Auto Liability (AL) Coverage:

What It Covers:
- Bodily injury to others
- Property damage to others
- Defense costs

FMCSA Minimum Limits:
- General freight: $750,000
- Hazmat: $1,000,000 - $5,000,000
- Passenger carriers: $1.5M - $5M

Common Limits We Write:
- $1,000,000 CSL (Combined Single Limit)
- Split limits available but less common

Filing Requirements:
- BMC-91 (surety bond) or BMC-91X (trust fund)
- Filed with FMCSA
- Must maintain continuous coverage

Premium Factors:
- Number of power units
- Number of drivers
- Driver experience/MVRs
- Radius of operation
- Safety scores
- Claims history""",

            "physical damage": """Physical Damage Coverage:

What It Covers:
- Comprehensive: Fire, theft, vandalism, weather, etc.
- Collision: Damage from accidents

Coverage Options:
- Stated value
- Actual Cash Value (ACV)
- Replacement cost (rare)

Typical Deductibles:
- $1,000 - $2,500 comprehensive
- $1,000 - $5,000 collision
- Higher deductibles = lower premium

What It Doesn't Cover:
- Mechanical breakdown
- Wear and tear
- Intentional damage
- Items inside vehicle (separate coverage needed)

Premium Factors:
- Vehicle value
- Vehicle age
- Garaging location
- Loss history
- Deductible chosen""",

            "general liability": """General Liability (GL) Coverage:

What It Covers:
- Third-party bodily injury (off-road)
- Third-party property damage (off-road)
- Personal injury (libel, slander)
- Advertising injury
- Medical payments

Common Limits:
- $1,000,000 per occurrence
- $2,000,000 general aggregate
- $1,000,000 products-completed ops

What It Doesn't Cover:
- Auto-related claims (covered by AL)
- Professional services (need E&O)
- Employee injuries (need WC)
- Intentional acts

Who Needs It:
- Anyone with an office or terminal
- If you hire subcontractors
- If contracts require it

Premium Factors:
- Payroll
- Revenue
- Location
- Operations type""",
        }

        for key, info in coverages.items():
            if key in coverage_lower:
                return info

        return f"""I don't have specific information for "{coverage_type}" coverage.

Common coverage types I can explain:
- Cargo insurance
- Auto liability
- Physical damage
- General liability

Please ask about one of these or specify what coverage you need information about."""

    def get_compliance_requirements(self, requirement_type: str) -> str:
        """
        Get information about FMCSA compliance requirements.

        Args:
            requirement_type: Type of requirement (e.g., "new authority", "insurance filing", "MCS-150")

        Returns:
            str: Compliance requirements and process
        """
        req_lower = requirement_type.lower()

        requirements = {
            "authority": """New FMCSA Authority Requirements:

To operate as a for-hire motor carrier:

1. USDOT Number:
   - Required for all interstate carriers
   - Free to obtain through FMCSA
   - Needed before MC authority

2. MC Authority (if for-hire):
   - Operating Authority to haul freight
   - Apply through FMCSA
   - $300 filing fee
   - 10-day protest period after approval

3. Insurance Requirements (before operating):
   - BMC-91 or 91X filing (liability)
   - BMC-34 filing (cargo) if household goods
   - Must be filed by insurance company

4. Process Agent (BOC-3):
   - Designate agents in each state you operate
   - Required before authority activates
   - Many services offer this for ~$50

5. UCR (Unified Carrier Registration):
   - Annual registration
   - Fee based on fleet size
   - Must be current to operate

Timeline: 3-6 weeks typically""",

            "insurance filing": """FMCSA Insurance Filing Requirements:

Required Filings:

BMC-91 or BMC-91X (Liability):
- Required for all for-hire carriers
- Must meet minimum limits for your operation
- Filed electronically by insurance carrier
- Must remain active - lapse = authority revocation

BMC-34 (Cargo):
- Required for household goods carriers only
- $5,000 minimum per vehicle
- $10,000 aggregate minimum

BMC-84 (Broker Bond):
- Required for freight brokers
- $75,000 minimum
- Must be surety bond or trust fund

Filing Process:
1. Bind coverage with FMCSA-authorized insurer
2. Insurer files electronically with FMCSA
3. Allow 24-48 hours for processing
4. Verify filing on FMCSA website

Cancellation:
- 30-day notice required
- Must maintain coverage or cease operations
- Lapse can result in authority revocation""",

            "mcs-150": """MCS-150 Biennial Update Requirements:

What Is It:
- Motor Carrier Identification Report
- Must be updated every 2 years
- Based on USDOT number (odd/even)

When to Update:
- Every 24 months based on USDOT number
- Odd numbers: Odd years
- Even numbers: Even years
- Also after any significant changes

Information Required:
- Company name and address
- Contact information
- Type of operation
- Cargo types
- Number of power units
- Number of drivers
- Vehicle miles traveled

How to File:
- Online through FMCSA portal (free)
- Paper form available
- Third-party services available

Penalties for Non-Compliance:
- Up to $1,000 per day fine
- Can affect safety rating
- May impact insurance rates""",
        }

        for key, info in requirements.items():
            if key in req_lower or (key == "authority" and "new" in req_lower):
                return info

        return f"""I don't have specific compliance information for "{requirement_type}".

Common compliance topics:
- New authority requirements
- Insurance filing requirements
- MCS-150 biennial update

Please specify which compliance topic you need information about."""
