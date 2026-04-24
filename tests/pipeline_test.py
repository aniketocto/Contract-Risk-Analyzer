"""Test: ingestion_agent with a .txt contract file → structuring → classification."""
import os
import json
import tempfile

from agents.ingestion_agent import ingestion_agent
from agents.structuring_agent import structuring_agent
from agents.classification_agent import classification_agent

# ── Create a temp contract file to simulate real file upload ──
CONTRACT_TEXT = """SOFTWARE DEVELOPMENT & MAINTENANCE AGREEMENT
THIS AGREEMENT made on this 24th day of April 2026 BETWEEN Canara Bank (hereinafter referred to as "the Bank") AND M/s. CloudSync Tech Solutions (hereinafter called "the Contractor").

1. Scope of Services
The Contractor shall provide full-stack development and maintenance. The Bank reserves the right to change the scope at any time without a corresponding increase in fees.

2. Liability and Indemnification
Clause 2.1: The Contractor shall be liable for unlimited damages arising from any service interruption, regardless of whether such interruption was caused by the Contractor's negligence or third-party infrastructure failure.

Clause 2.2: The Contractor agrees to indemnify the Bank against all third-party claims, including those arising from the Bank's own negligence in handling the software.

3. Intellectual Property Rights
Clause 3.1: While the Bank shall own the final deliverables, the Contractor grants the Bank a perpetual, sub-licensable license to all of the Contractor's pre-existing proprietary code used in the project, without any additional royalty payments.

4. Termination
Clause 4.1: The Bank may terminate this agreement at any time with 24 hours' notice without specifying any reason.

Clause 4.2: In the event of termination by the Bank, the Contractor shall forfeit all pending payments for work already completed but not yet "Accepted" by the Bank's internal audit team.

5. Payment Terms
Clause 5.1: Payments shall be processed within 120 days of invoice receipt, provided the Bank's quarterly budget has been approved by the board. No interest shall be paid on delayed payments.
"""

# Write to temp .txt file
test_dir = os.path.join(os.path.dirname(__file__), "..", "test_data")
os.makedirs(test_dir, exist_ok=True)
test_file = os.path.join(test_dir, "sample_contract.txt")
with open(test_file, "w", encoding="utf-8") as f:
    f.write(CONTRACT_TEXT)

print("=" * 70)
print("  FULL PIPELINE: Ingestion -> Structuring -> Classification")
print("=" * 70)

# Step 1: Ingest
print("\n[Step 1] Ingestion Agent")
ingested = ingestion_agent(test_file)  # Pass as string path
print(f"  Status : {ingested['status']}")
print(f"  File   : {ingested['filename']}")
print(f"  Length : {len(ingested['raw_text'])} chars")

if ingested["status"] != "success":
    print(f"  ERROR  : {ingested.get('error')}")
    exit(1)

# Verify newlines are preserved (critical!)
newline_count = ingested["raw_text"].count("\n")
print(f"  Newlines preserved: {newline_count}")
assert newline_count > 10, "CRITICAL: Newlines were destroyed! Structuring will fail."

# Step 2: Structure
print("\n[Step 2] Structuring Agent")
structured = structuring_agent(ingested["raw_text"])
print(f"  Sections: {len(structured['sections'])}")
print(f"  Clauses : {len(structured['clauses'])}")

# Step 3: Classify
print("\n[Step 3] Classification Agent")
classified = classification_agent(structured)

print("\n" + "-" * 70)
print(f"{'ID':<8} {'Category':<25} {'Conf.':<8} Text")
print("-" * 70)
for c in classified["clauses"]:
    text_preview = c["text"].replace("\n", " ")[:55]
    print(f"{c['id']:<8} {c.get('type', '?'):<25} {c.get('confidence', '?'):<8} {text_preview}")
print("-" * 70)
