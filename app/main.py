"""
Pipeline Orchestrator – Contract Risk Analyzer
================================================
Runs the full agent pipeline in strict order.
Includes mock agents, agentic retry logic, and LLM setup.
"""

import sys, os, logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("pipeline")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.scoring_agent import scoring_agent

# ── LLM Setup (LangChain + Ollama) ─────────────────────────────
try:
    from langchain_ollama import OllamaLLM
    llm = OllamaLLM(model="llama3", temperature=0.0)
    LLM_AVAILABLE = True
    logger.info("LLM (Ollama llama3) initialized.")
except Exception as e:
    llm = None
    LLM_AVAILABLE = False
    logger.warning(f"LLM not available: {e}")

MAX_RETRIES = 2

# ===========================================================================
# MOCK AGENTS – Replace with real imports when available
# ===========================================================================

def ingestion_agent(file) -> str:
    """MOCK – Extract text from uploaded contract."""
    logger.info("[MOCK] ingestion_agent → extracting text")
    return (
        "1. Liability: The vendor shall bear unlimited liability for all damages. "
        "2. Termination: Either party may terminate with 30 days notice. "
        "3. IP: All IP created belongs to the client exclusively. "
        "4. Confidentiality: Info protected for 10 years post-termination. "
        "5. Indemnification: Party B indemnifies Party A without cap. "
        "6. Payment: Invoices paid within 15 days, 5% late fee/month."
    )

def structuring_agent(text: str) -> list[dict]:
    """MOCK – Split text into clause dicts."""
    logger.info("[MOCK] structuring_agent → structuring clauses")
    return [
        {"id": 1, "text": "The vendor shall bear unlimited liability for all damages."},
        {"id": 2, "text": "Either party may terminate with 30 days notice."},
        {"id": 3, "text": "All IP created belongs to the client exclusively."},
        {"id": 4, "text": "Info protected for 10 years post-termination."},
        {"id": 5, "text": "Party B indemnifies Party A without cap."},
        {"id": 6, "text": "Invoices paid within 15 days, 5% late fee/month."},
    ]

def classification_agent(clauses: list[dict]) -> list[dict]:
    """MOCK – Classify clause types with confidence."""
    logger.info("[MOCK] classification_agent → classifying")
    mapping = {1: ("Liability", 0.92), 2: ("Termination", 0.88), 3: ("IP Ownership", 0.75),
               4: ("Confidentiality", 0.65), 5: ("Indemnification", 0.90), 6: ("Payment Terms", 0.60)}
    for c in clauses:
        t, conf = mapping.get(c["id"], ("General", 0.5))
        c["type"], c["confidence"] = t, conf
    return clauses

def risk_agent(clauses: list[dict]) -> list[dict]:
    """MOCK – Assign risk levels and reasons."""
    logger.info("[MOCK] risk_agent → assessing risk")
    mapping = {1: ("High", "Unlimited liability"), 2: ("Low", "Standard termination"),
               3: ("Medium", "Broad IP assignment"), 4: ("Medium", "Long confidentiality period"),
               5: ("High", "Uncapped indemnification"), 6: ("Low", "Standard payment terms")}
    for c in clauses:
        r, reason = mapping.get(c["id"], ("Low", "Standard clause"))
        c["risk"], c["reason"] = r, reason
    return clauses

def suggestion_agent(clauses: list[dict]) -> list[dict]:
    """MOCK – Generate suggestions for risky clauses."""
    logger.info("[MOCK] suggestion_agent → generating suggestions")
    mapping = {1: "Cap liability to contract value.", 2: "No changes needed.",
               3: "Exclude pre-existing IP.", 4: "Reduce to 3-5 years.",
               5: "Add indemnification cap.", 6: "Negotiate to 30-day window."}
    for c in clauses:
        s = mapping.get(c["id"])
        if s:
            c["suggestion"] = s
    return clauses

# ===========================================================================
# AGENTIC BEHAVIOURS
# ===========================================================================

def _retry_low_confidence(clauses):
    """Re-run classification for clauses with confidence < 0.7."""
    low = [c for c in clauses if c.get("confidence", 0) < 0.7]
    if not low:
        return clauses
    logger.warning(f"⚠ {len(low)} clause(s) confidence < 0.7 → re-running classification")
    for attempt in range(1, MAX_RETRIES + 1):
        clauses = classification_agent(clauses)
        if not [c for c in clauses if c.get("confidence", 0) < 0.7]:
            logger.info(f"  ✓ All above threshold after retry {attempt}")
            break
    return clauses

def _retry_missing_risk(clauses):
    """Re-run risk agent for clauses missing risk level."""
    missing = [c for c in clauses if not c.get("risk")]
    if not missing:
        return clauses
    logger.warning(f"⚠ {len(missing)} clause(s) missing risk → re-running risk_agent")
    for attempt in range(1, MAX_RETRIES + 1):
        clauses = risk_agent(clauses)
        if not [c for c in clauses if not c.get("risk")]:
            logger.info(f"  ✓ All have risk after retry {attempt}")
            break
    return clauses

def _self_check(clauses):
    """Self-check: Did I miss any risky clauses?"""
    logger.info("🔍 Self-check: scanning for missed risky clauses...")
    keywords = ["unlimited", "uncapped", "no limitation", "sole discretion",
                 "irrevocable", "perpetual", "waive", "forfeit", "penalt",
                 "indemnif", "without limit", "without cap", "at any time"]
    flagged = 0
    for c in clauses:
        if c.get("risk") == "High":
            continue
        text = c.get("text", "").lower()
        for kw in keywords:
            if kw in text:
                logger.warning(f"  ⚠ Clause {c.get('id')} has '{kw}' but rated '{c.get('risk')}' – review needed")
                flagged += 1
                break
    if flagged == 0:
        logger.info("  ✓ No missed risky clauses detected")
    return clauses

# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_pipeline(file) -> dict[str, Any]:
    """Execute the full Contract Risk Analyzer pipeline."""
    logger.info("=" * 55)
    logger.info("CONTRACT RISK ANALYZER – Pipeline Started")
    logger.info("=" * 55)

    # Step 1: Ingestion
    logger.info("Step 1/6 → Ingestion Agent")
    raw_text = ingestion_agent(file)
    if not raw_text:
        raise ValueError("Ingestion returned empty text.")

    # Step 2: Structuring
    logger.info("Step 2/6 → Structuring Agent")
    clauses = structuring_agent(raw_text)
    if not clauses:
        raise ValueError("Structuring returned no clauses.")

    # Step 3: Classification
    logger.info("Step 3/6 → Classification Agent")
    clauses = classification_agent(clauses)
    clauses = _retry_low_confidence(clauses)

    # Step 4: Risk Assessment
    logger.info("Step 4/6 → Risk Agent")
    clauses = risk_agent(clauses)
    clauses = _retry_missing_risk(clauses)

    # Step 5: Suggestions
    logger.info("Step 5/6 → Suggestion Agent")
    clauses = suggestion_agent(clauses)

    # Agentic self-check
    clauses = _self_check(clauses)

    # Step 6: Scoring
    logger.info("Step 6/6 → Scoring Agent")
    score = scoring_agent(clauses)

    logger.info("=" * 55)
    logger.info(f"Pipeline Complete → Risk Score: {score['overall_score']}/100")
    logger.info("=" * 55)

    return {"clauses": clauses, "score": score}


if __name__ == "__main__":
    import json
    result = run_pipeline("sample_contract.pdf")
    print(json.dumps(result, indent=2, default=str))
