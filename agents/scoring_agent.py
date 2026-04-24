"""
Scoring Agent for Contract Risk Analyzer
=========================================
Analyzes classified and risk-assessed clauses to produce an overall
risk score (0-100) along with a per-clause-type breakdown.

Input:  List of clause dicts with keys: id, text, type, confidence, risk, reason, suggestion (optional)
Output: Dict with overall_score, summary counts, and breakdown by clause type.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Weight configuration – adjust these if the business rules change
# ---------------------------------------------------------------------------
RISK_WEIGHTS: dict[str, int] = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

# Maximum weight per clause (used for normalization)
MAX_WEIGHT: int = max(RISK_WEIGHTS.values())


def _validate_clauses(clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Validate and sanitize incoming clause data.
    Clauses missing required fields are flagged but not dropped so the
    pipeline stays transparent about data-quality issues.
    """
    required_keys = {"id", "text", "type", "risk"}
    validated: list[dict[str, Any]] = []

    for clause in clauses:
        # Ensure it's a dict
        if not isinstance(clause, dict):
            continue

        # Fill missing optional fields with safe defaults
        clause.setdefault("confidence", 0.0)
        clause.setdefault("reason", "No reason provided")
        clause.setdefault("suggestion", "No suggestion available")

        # Check for required keys
        missing = required_keys - clause.keys()
        if missing:
            # Attach a warning but keep the clause
            clause["_warnings"] = f"Missing fields: {', '.join(missing)}"

        validated.append(clause)

    return validated


def _count_risks(clauses: list[dict[str, Any]]) -> dict[str, int]:
    """Return counts of High, Medium, and Low risk clauses."""
    counts = {"high": 0, "medium": 0, "low": 0}
    for clause in clauses:
        risk_level = clause.get("risk", "").capitalize()
        if risk_level == "High":
            counts["high"] += 1
        elif risk_level == "Medium":
            counts["medium"] += 1
        elif risk_level == "Low":
            counts["low"] += 1
    return counts


def _compute_normalized_score(clauses: list[dict[str, Any]]) -> float:
    """
    Compute a normalized risk score between 0 and 100.

    Formula:
        weighted_sum  = Σ weight(risk_i)
        max_possible  = num_clauses × MAX_WEIGHT
        score         = (weighted_sum / max_possible) × 100

    A score of 100 means every clause is High-risk.
    A score of 0 means there are no clauses or no recognized risk levels.
    """
    if not clauses:
        return 0.0

    weighted_sum = sum(
        RISK_WEIGHTS.get(c.get("risk", "").capitalize(), 0) for c in clauses
    )
    max_possible = len(clauses) * MAX_WEIGHT

    if max_possible == 0:
        return 0.0

    return round((weighted_sum / max_possible) * 100, 2)


def _build_breakdown(clauses: list[dict[str, Any]]) -> dict[str, str]:
    """
    Build a per-clause-type risk breakdown.
    For each clause type, report the *highest* risk level found.
    """
    type_risks: dict[str, str] = {}
    priority = {"High": 3, "Medium": 2, "Low": 1}

    for clause in clauses:
        clause_type = clause.get("type", "Unknown")
        risk_level = clause.get("risk", "Low").capitalize()

        current = type_risks.get(clause_type)
        if current is None or priority.get(risk_level, 0) > priority.get(current, 0):
            type_risks[clause_type] = risk_level

    return type_risks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scoring_agent(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Main entry point for the Scoring Agent.

    Parameters
    ----------
    clauses : list[dict]
        A list of clause dictionaries produced by the upstream agents
        (classification → risk → suggestion).

    Returns
    -------
    dict
        {
            "overall_score": float (0-100),
            "summary": {"high": int, "medium": int, "low": int},
            "breakdown": {"Liability": "High", "Termination": "Medium", ...}
        }
    """
    try:
        # Step 1: Validate & sanitize
        validated = _validate_clauses(clauses)

        # Step 2: Count risk levels
        summary = _count_risks(validated)

        # Step 3: Compute normalized score
        overall_score = _compute_normalized_score(validated)

        # Step 4: Build per-type breakdown
        breakdown = _build_breakdown(validated)

        return {
            "overall_score": overall_score,
            "summary": summary,
            "breakdown": breakdown,
        }

    except Exception as e:
        # Graceful degradation – return a safe default so the pipeline
        # doesn't crash if scoring encounters unexpected data.
        return {
            "overall_score": 0.0,
            "summary": {"high": 0, "medium": 0, "low": 0},
            "breakdown": {},
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_clauses = [
        {
            "id": 1,
            "text": "The vendor shall bear unlimited liability for all damages.",
            "type": "Liability",
            "confidence": 0.92,
            "risk": "High",
            "reason": "Unlimited liability exposure",
            "suggestion": "Cap liability to total contract value",
        },
        {
            "id": 2,
            "text": "Either party may terminate with 30 days written notice.",
            "type": "Termination",
            "confidence": 0.88,
            "risk": "Low",
            "reason": "Standard termination clause",
            "suggestion": "No changes needed",
        },
        {
            "id": 3,
            "text": "All intellectual property created during engagement belongs to the client.",
            "type": "IP Ownership",
            "confidence": 0.75,
            "risk": "Medium",
            "reason": "Broad IP assignment without exceptions",
            "suggestion": "Exclude pre-existing IP from assignment",
        },
        {
            "id": 4,
            "text": "Confidentiality obligations survive for 10 years post-termination.",
            "type": "Confidentiality",
            "confidence": 0.65,
            "risk": "Medium",
            "reason": "Unusually long confidentiality period",
        },
    ]

    result = scoring_agent(sample_clauses)
    print("=" * 50)
    print("SCORING AGENT – Self-Test Results")
    print("=" * 50)
    print(f"Overall Score : {result['overall_score']}/100")
    print(f"Summary       : {result['summary']}")
    print(f"Breakdown     : {result['breakdown']}")
