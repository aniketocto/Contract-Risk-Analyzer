from agents.structuring_agent import structuring_agent
import json

# ---------------------------------------------------------------------------
# Test 1 — Mixed "Clause X.Y:" + bare numbered headings (your original mock)
# ---------------------------------------------------------------------------
mock_text_1 = """
Made for Hire." However, the Company shall retain a non-exclusive, perpetual, royalty-free license to use any generic code fragments, algorithms, or methodologies developed during the project for its other clients.

Clause 2.2: Client shall own the final front-end interface, but all backend logic and database schemas remain the property of the Company until full payment is received.

3. Limitation of Liability
Clause 3.1: Notwithstanding anything to the contrary, the Company\u2019s total liability for any claims, losses, or damages arising out of this Agreement shall be unlimited in cases of gross negligence or data breaches.

Clause 3.2: In all other circumstances, the Company\u2019s liability shall not exceed 5x the total fees paid by the Client in the 12 months preceding the claim.

4. Termination
Clause 4.1: Client may terminate this Agreement for convenience by providing 90 days' written notice. If Client terminates for convenience, Client must pay a "Early Termination Fee" equal to 25% of the remaining contract value.

Clause 4.2: Company may terminate this Agreement immediately if the Client fails to pay any invoice within 5 days of the due date.

5. Indemnification
The Client agrees to indemnify, defend, and hold harmless the Company from and against any third-party claims resulting from the Client\u2019s use of the software in a manner not intended by the Company.

6. Governing Law
This Agreement shall be governed by and construed in accordance with the laws of the State of Maharashtra, India. Any disputes shall be settled in the courts of Mumbai.
"""

# ---------------------------------------------------------------------------
# Test 2 — "Article" + "Section" style (common in formal contracts)
# ---------------------------------------------------------------------------
mock_text_2 = """
Article I – Definitions
Section 1.1  "Agreement" means this Master Services Agreement.
Section 1.2  "Confidential Information" includes trade secrets, business plans, and any proprietary data.

Article II – Scope of Work
Section 2.1  The Provider shall deliver the software as described in Exhibit A.
Section 2.2  Any change requests must be documented in a Change Order signed by both parties.
"""

# ---------------------------------------------------------------------------
# Test 3 — Decimal-only numbering (no keywords)
# ---------------------------------------------------------------------------
mock_text_3 = """
1. Intellectual Property
1.1 All deliverables created under this Agreement shall be considered works made for hire.
1.2 The Company retains a license to reuse generic components.

2. Payment Terms
2.1 Client shall pay within 30 days of invoice.
2.2 Late payments accrue interest at 1.5% per month.
"""

# ---------------------------------------------------------------------------
# Test 4 — Lettered sub-items
# ---------------------------------------------------------------------------
mock_text_4 = """
3. Confidentiality Obligations
(a) Neither party shall disclose Confidential Information without prior written consent.
(b) Obligations under this clause survive for 5 years after termination.
(c) The following are excluded from Confidential Information:
(i) information already in the public domain
(ii) information independently developed by the receiving party
"""

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
tests = {
    "Test 1 — Mixed Clause/Numbered": mock_text_1,
    "Test 2 — Article/Section":       mock_text_2,
    "Test 3 — Decimal only":          mock_text_3,
    "Test 4 — Lettered sub-items":    mock_text_4,
}

for name, text in tests.items():
    print("=" * 70)
    print(f"  {name}")
    print("=" * 70)
    result = structuring_agent(text)

    # Recursive tree display
    def print_tree(nodes, indent=0):
        prefix = "  " * indent
        for n in nodes:
            label = n['text'][:90] if n['text'] else n['title'][:90]
            print(f"{prefix}[{n['id']}] {label}")
            if n['children']:
                print_tree(n['children'], indent + 1)

    print_tree(result["sections"])

    print(f"\nFlat clauses count: {len(result['clauses'])}")
    print()