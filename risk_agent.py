def evaluate_risk(text: str, clause_type: str) -> tuple[str, str]:
    text_lower = text.lower()

    if "unlimited liability" in text_lower:
        return "High", "Unlimited liability exposure"
    if "indemnification" in text_lower or "indemnify" in text_lower:
        return "High", "Indemnification obligation increases exposure"
    if "without limitation" in text_lower:
        return "High", "Unlimited liability exposure"
    if "perpetual" in text_lower:
        return "High", "Perpetual obligations increase exposure"
    if "irrevocable" in text_lower:
        return "High", "Irrevocable terms restrict flexibility"

    if "auto-renewal" in text_lower:
        return "Medium", "Auto-renewal clause may create unintended commitment"
    if "termination notice" in text_lower:
        return "Medium", "Potential contractual restriction or obligation"
    if "penalty" in text_lower:
        return "Medium", "Potential contractual restriction or obligation"
    if "exclusive" in text_lower:
        return "Medium", "Potential contractual restriction or obligation"

    if clause_type in ("Liability", "Indemnity"):
        return "Medium", "Inherent risk based on clause type"

    return "Low", "No significant risk detected"


def risk_agent(clauses: list[dict]) -> list[dict]:
    enriched_clauses = []
    
    for clause in clauses:
        enriched_clause = clause.copy()
        
        text = clause.get("text", "")
        clause_type = clause.get("type", "")
        
        risk, reason = evaluate_risk(text, clause_type)
        
        enriched_clause["risk"] = risk
        enriched_clause["reason"] = reason
        
        enriched_clauses.append(enriched_clause)
        
    return enriched_clauses
