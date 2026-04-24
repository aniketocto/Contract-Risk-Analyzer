import re
import ollama

# ✅ Allowed categories (STRICT)
CATEGORIES = [
    "Liability",
    "Intellectual Property",
    "Termination",
    "Payment",
    "Confidentiality",
    "Indemnification",
    "Governing Law",
    "Other"
]


def classify_with_llm(clause_text: str) -> str:
    prompt = f"""
You are a legal contract classifier.

Classify the following clause into EXACTLY ONE category from this list:

- Liability
- Intellectual Property
- Termination
- Payment
- Confidentiality
- Indemnification
- Governing Law
- Other

IMPORTANT:
- Return ONLY the category name
- Do NOT explain
- Do NOT add extra text

Clause:
\"\"\"{clause_text}\"\"\"
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )

        output = response["message"]["content"].strip()

        # Clean output
        output = output.split("\n")[0].strip()

        # Normalize (important)
        for cat in CATEGORIES:
            if cat.lower() in output.lower():
                return cat

        return "Other"

    except Exception as e:
        print("LLM Error:", e)
        return "Other"


# 🔥 Fallback logic (very important)
# Each rule: (category, list_of_keyword_patterns)
_FALLBACK_RULES = [
    ("Liability",              [r"liab\w*", r"liable"]),
    ("Termination",            [r"terminat\w*", r"cancel\w*"]),
    ("Intellectual Property",  [r"intellectual\s+property", r"\bip\b", r"copyright", r"patent", r"trademark"]),
    ("Payment",                [r"payment", r"invoice", r"fee\b", r"cost\b", r"compensat\w*"]),
    ("Confidentiality",        [r"confidential\w*", r"non-disclosure", r"\bnda\b"]),
    ("Indemnification",        [r"indemnif\w*", r"hold\s+harmless"]),
    ("Governing Law",          [r"govern\w*\s+law", r"jurisdiction", r"\bcourt\b", r"dispute", r"governing"]),
]


def fallback_classification(text: str) -> str:
    text_lower = text.lower()
    for category, patterns in _FALLBACK_RULES:
        for pat in patterns:
            if re.search(pat, text_lower):
                return category
    return "Other"


def classification_agent(data: dict) -> dict:
    clauses = data.get("clauses", [])

    for clause in clauses:
        text = clause.get("text", "")
        clause_id = clause.get("id", "")

        # 🚫 Skip junk / headers
        if clause_id.startswith("P") or len(text.split()) < 5:
            clause["type"] = "Other"
            clause["confidence"] = "low"
            continue

        # Step 1: LLM
        category = classify_with_llm(text)

        # Step 2: fallback
        if category == "Other":
            category = fallback_classification(text)

        clause["type"] = category
        clause["confidence"] = "high" if category != "Other" else "low"

    return data