"""End-to-end test: structuring_agent → classification_agent pipeline."""
from agents.structuring_agent import structuring_agent
from agents.classification_agent import classification_agent
import json

# Full contract text (same as structuring test)
contract = """
SOFTWARE DEVELOPMENT & MAINTENANCE AGREEMENT
THIS AGREEMENT made on this 24th day of April 2026 BETWEEN Canara Bank, a body corporate constituted under the Banking & Companies Act, 1970, having its Head Office at Bangalore (hereinafter referred to as "the Bank") of the ONE PART;

AND

M/s. CloudSync Tech Solutions, a proprietorship firm represented by its Proprietor Aniket, aged 22 years, residing at Mumbai, Maharashtra (hereinafter called "the Contractor") of the OTHER PART.

WHEREAS the Bank is desirous of undertaking the Modernization of Core Banking UI and has accepted the tender submitted by the Contractor.

NOW THIS AGREEMENT WITNESSETH AS FOLLOWS:

1. Scope of Services
The Contractor shall provide full-stack development and maintenance. The Bank reserves the right to change the scope at any time without a corresponding increase in fees.

2. Liability and Indemnification (TEST DATA: HIGH RISK)
Clause 2.1: The Contractor shall be liable for unlimited damages arising from any service interruption, regardless of whether such interruption was caused by the Contractor’s negligence or third-party infrastructure failure.

Clause 2.2: The Contractor agrees to indemnify the Bank against all third-party claims, including those arising from the Bank's own negligence in handling the software.

3. Intellectual Property Rights (TEST DATA: AMBIGUOUS)
Clause 3.1: While the Bank shall own the final deliverables, the Contractor grants the Bank a perpetual, sub-licensable license to all of the Contractor's pre-existing proprietary code used in the project, without any additional royalty payments.

4. Termination (TEST DATA: UNFAIR CLAUSE)
Clause 4.1: The Bank may terminate this agreement at any time with 24 hours' notice without specifying any reason.

Clause 4.2: In the event of termination by the Bank, the Contractor shall forfeit all pending payments for work already completed but not yet "Accepted" by the Bank’s internal audit team.

5. Payment Terms
Clause 5.1: Payments shall be processed within 120 days of invoice receipt, provided the Bank's quarterly budget has been approved by the board. No interest shall be paid on delayed payments.
"""

# Step 1: Structure
structured = structuring_agent(contract)
print(f"Structured: {len(structured['clauses'])} clauses found\n")

# Step 2: Classify
classified = classification_agent(structured)

# Show results
for clause in classified["clauses"]:
    print(f"[{clause['id']}] {clause['type']:<20} | {clause['text'][:70]}")
