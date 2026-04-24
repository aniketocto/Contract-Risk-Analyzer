import ollama
import json
import re


# 🔹 Safe JSON extractor
def extract_json(text: str) -> dict:
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {}


# 🔹 Suggestion Generator (LLM)
def generate_suggestion(text: str, user_role: str, context: str = "") -> dict:
    prompt = f"""
You are a legal contract assistant.

Rewrite the following clause to make it SAFER for the {user_role}.

User Context:
{context}

Goals:
- Reduce legal and financial risk
- Make clause more balanced
- Keep it realistic and professional

Return STRICT JSON exactly in this schema:
{{
  "issue": "A clear explanation of what is wrong.",
  "suggestion": "ONLY plain English rewritten clause. DO NOT output a dictionary like {{'text':...}}. Just raw text."
}}

Clause:
\"\"\"{text}\"\"\"
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            format="json"
        )

        raw_output = response["message"]["content"]
        parsed = extract_json(raw_output)
        
        # Cleanup hallucinated dictionary wrapping if LLM disobeys prompt
        if parsed and "suggestion" in parsed:
            sug = str(parsed["suggestion"]).strip()
            if sug.startswith("{") and sug.endswith("}") and "'text':" in sug:
                try:
                    import ast
                    inner = ast.literal_eval(sug)
                    if isinstance(inner, dict) and "text" in inner:
                        parsed["suggestion"] = inner["text"]
                except:
                    pass

        return parsed if parsed else {
            "issue": "JSON format parsing failed but here is the raw output:",
            "suggestion": raw_output.strip()
        }

    except Exception as e:
        print("LLM Error:", e)
        return {
            "issue": "Error occurred",
            "suggestion": "Fallback suggestion not available"
        }


# 🔹 Main Suggestion Agent (ON-DEMAND)
def suggestion_agent(clause: dict, user_role: str = "Vendor", context: str = "") -> dict:
    text = clause.get("text", "")

    result = generate_suggestion(text, user_role, context)

    return {
        "id": clause.get("id"),
        "type": clause.get("type"),
        "original": text,
        "user_role": user_role,
        "issue": result.get("issue"),
        "suggested_clause": result.get("suggestion")
    }