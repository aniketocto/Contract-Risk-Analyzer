import ollama
import json
import re
from agents.rag_agent import retrieve_similar


# ── Valid risk levels ────────────────────────────────────────────
VALID_RISKS = {"High", "Medium", "Low"}


# ── Rule-Based Risk Patterns ────────────────────────────────────
# Each rule: (risk_level, keyword_pattern, reason_template)
# Ordered: High first, then Medium.  First match wins.
_RISK_RULES = [
    # ━━━ HIGH RISK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ("High", r"unlimited\s+(liability|damages)",
     "Unlimited liability exposure — uncapped financial risk"),
    ("High", r"without\s+limitation",
     "No cap on liability — could result in disproportionate damages"),
    ("High", r"\bindemnif\w*",
     "Indemnification clause increases financial exposure"),
    ("High", r"\bperpetual\b",
     "Perpetual obligation — no natural end to commitment"),
    ("High", r"\birrevocable\b",
     "Irrevocable terms — cannot be undone once triggered"),
    ("High", r"\bforfeit\w*",
     "Forfeiture of payments/rights — potential loss of earned value"),
    ("High", r"\bwaive\w*\s+(all\s+)?rights?\b",
     "Waiver of rights — gives up legal protections"),
    ("High", r"sole\s+discretion",
     "Unilateral decision power — no negotiation or oversight"),
    ("High", r"24\s*hours?\W+notice",
     "Extremely short termination notice period"),
    ("High", r"no\s+interest\b.*\bdelayed\b|\bdelayed\b.*\bno\s+interest\b",
     "No penalty for late payments — imbalanced financial terms"),
    ("High", r"regardless\s+of\s+(whether|fault|negligence|cause)",
     "Risk shifted regardless of fault — unfair allocation"),

    # ━━━ MEDIUM RISK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ("Medium", r"auto[\-\s]?renewal",
     "Auto-renewal may create unintended long-term commitment"),
    ("Medium", r"\bpenalty\b",
     "Penalty clause increases financial burden"),
    ("Medium", r"\bexclusive\b",
     "Exclusivity restricts ability to work with others"),
    ("Medium", r"\bliquidated\s+damages\b",
     "Pre-set damages amount — may be disproportionate"),
    ("Medium", r"(90|120|180)\s*days?\b.*\b(payment|invoice|receipt)",
     "Extended payment timeline — cash flow risk"),
    ("Medium", r"sub[\-\s]?licens(e|able)",
     "Sub-licensing rights — loss of control over IP usage"),
    ("Medium", r"change\s+(the\s+)?scope.*without",
     "Scope can be changed unilaterally — unpredictable workload"),
    ("Medium", r"not\s+yet\s+.{0,20}(accepted|approved)",
     "Conditional acceptance — work may not be recognized"),
]


def evaluate_risk(text: str, clause_type: str) -> tuple[str, str]:
    """
    Rule-based risk evaluation.  Returns (risk_level, reason).
    """
    text_lower = text.lower()

    # Pattern matching
    for risk, pattern, reason in _RISK_RULES:
        if re.search(pattern, text_lower):
            return risk, reason

    # Type-based fallback
    if clause_type in ("Liability", "Indemnification"):
        return "Medium", "Clause category carries inherent risk"

    return "Low", "No significant risk indicators detected"


# ── Safe JSON Extraction ─────────────────────────────────────────
def extract_json(text: str) -> dict:
    """Extract first JSON object from LLM output."""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


def _normalize_risk(value: str) -> str:
    """Normalize LLM risk output to exactly High/Medium/Low."""
    if not isinstance(value, str):
        return ""
    v = value.strip().lower()
    if "high" in v:
        return "High"
    if "medium" in v or "moderate" in v:
        return "Medium"
    if "low" in v or "minimal" in v:
        return "Low"
    return ""


# ── LLM Risk Analysis ───────────────────────────────────────────
def llm_risk_analysis(text: str, user_role: str) -> dict:
    """
    Call LLM to analyze risk from the user's perspective.
    Returns {"risk": "High|Medium|Low", "reason": "..."} or {}.
    """
    # RAG Injection: Retrieve past knowledge
    past_context = retrieve_similar(text, user_role, top_k=1)
    
    rag_str = ""
    if past_context:
        past = past_context[0]
        
        # 🚀 MASSIVE SPEEDUP: Semantic Caching
        # If we have seen a very similar clause before, skip the LLM completely to save time!
        if past.get("_sim_score", 0) > 0.85:
            return {
                "risk": past["risk"],
                "reason": f"[RAG CACHE] {past['reason']}"
            }
            
        rag_str = f"\n\n[LOCAL MEMORY: In the past, a similar clause was rated '{past['risk']}' because: {past['reason']}. Consider this precedent if applicable.]\n"

    prompt = f"""You are a legal contract risk analyzer.

Analyze this clause from the perspective of the **{user_role}** (the party you are protecting).

Consider:
- Is this clause fair or one-sided?
- Does it expose the {user_role} to financial, legal, or operational risk?
- Are there any red flags like unlimited liability, short notice periods, or forfeiture?{rag_str}

Return ONLY valid JSON (no markdown, no explanation):
{{"risk": "High" or "Medium" or "Low", "reason": "One sentence explanation from {user_role}'s perspective"}}

Clause:
\"\"\"{text}\"\"\"
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response["message"]["content"]
        parsed = extract_json(raw_output)

        # Normalize the risk field
        if parsed and "risk" in parsed:
            parsed["risk"] = _normalize_risk(parsed["risk"])
            if parsed["risk"] not in VALID_RISKS:
                return {}

        return parsed if parsed else {}

    except Exception as e:
        print(f"LLM risk error: {e}")
        return {}


# ── Main Risk Agent ──────────────────────────────────────────────
def risk_agent(data: dict, user_role: str = "Contractor") -> dict:
    """
    Analyze risk for each clause from the user's perspective.
    ...
    """
    clauses = data.get("clauses", [])
    enriched_clauses = []

    for clause_in in clauses:
        enriched = clause_in.copy()
        text = enriched.get("text", "")
        clause_type = enriched.get("type", "")

        # Skip junk
        if len(text.split()) < 6:
            enriched.update({
                "risk": "Low",
                "reason": "Not a substantive clause",
                "rule_risk": "Low",
                "user_role": user_role,
                "confidence": "low",
            })
            enriched_clauses.append(enriched)
            continue

        # Step 1: Rule-based (fast, reliable)
        rule_risk, rule_reason = evaluate_risk(text, clause_type)

        # Step 2: LLM-based (user perspective, nuanced)
        llm_result = llm_risk_analysis(text, user_role)
        llm_risk = llm_result.get("risk", "")
        llm_reason = llm_result.get("reason", "")

        # Step 3: Merge — rules OVERRIDE when they detect High risk
        if "[RAG CACHE]" in llm_reason:
            # Prevent recursive formatting on cache hits
            final_risk = llm_risk or rule_risk
            final_reason = llm_reason
        elif rule_risk == "High":
            # Rules caught a critical pattern — trust rules
            final_risk = "High"
            final_reason = rule_reason
            if llm_reason:
                final_reason += f" | LLM ({user_role}): {llm_reason}"
        elif llm_risk in VALID_RISKS:
            # LLM gave a valid answer, and rules didn't flag High
            final_risk = llm_risk
            final_reason = llm_reason or rule_reason
        else:
            # LLM failed — fall back to rules
            final_risk = rule_risk
            final_reason = rule_reason

        enriched.update({
            "risk": final_risk,
            "reason": final_reason,
            "rule_risk": rule_risk,
            "user_role": user_role,
            "confidence": "high" if final_risk in ("High", "Medium") else "medium",
        })
        enriched_clauses.append(enriched)

    # Preserve sections tree for the frontend
    result = {"clauses": enriched_clauses}
    if "sections" in data:
        result["sections"] = data["sections"]

    return result