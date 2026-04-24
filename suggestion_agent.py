import json
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

# Initialize the LLM
# We use Llama 3 via Ollama. Make sure Ollama is installed and running locally.
llm = OllamaLLM(model="llama3")

# Fallback suggestions based on clause types to use if LLM generation fails
FALLBACK_SUGGESTIONS = {
    "Liability": "Ensure liability is mutually capped, typically at the total contract value, and excludes indirect or consequential damages.",
    "Intellectual Property": "Clarify that each party retains its pre-existing IP, and specify the exact license or ownership rights for any newly created IP.",
    "Termination": "Include a mutual right to terminate for cause with a reasonable cure period (e.g., 30 days) and clearly define post-termination obligations.",
    "Payment": "Specify clear payment terms (e.g., Net 30), acceptable payment methods, and reasonable late payment penalties (e.g., 1.5% per month).",
    "Confidentiality": "Define confidential information clearly, set a reasonable duration for confidentiality obligations (e.g., 3-5 years), and include standard exceptions.",
    "Dispute Resolution": "Require good-faith negotiations before escalation, specify mediation/arbitration rules, and define the governing law and jurisdiction.",
    "Data Protection": "Ensure compliance with applicable data privacy laws (e.g., GDPR, CCPA) and specify data breach notification timelines and security standards.",
    "Indemnity": "Make indemnification mutual, limit it to third-party claims arising from gross negligence, willful misconduct, or IP infringement, and avoid broad 'all-encompassing' indemnities.",
    "Warranty": "Include standard warranties of authority and non-infringement. Avoid 'as-is' clauses where inappropriate, and disclaim implied warranties like fitness for a particular purpose only if balanced.",
    "Other": "Review this clause carefully to ensure it does not impose unfair obligations or risks on either party."
}

def get_fallback_suggestion(clause_type):
    """
    Returns a rule-based suggestion based on the clause type.
    """
    return FALLBACK_SUGGESTIONS.get(clause_type, FALLBACK_SUGGESTIONS["Other"])

def generate_clause_suggestion(clause):
    """
    Generates a suggestion for a single contract clause using Llama 3 via Ollama.
    If the LLM fails, uses a fallback rule-based suggestion.
    """
    # If the risk is Low, we don't need to change anything
    if clause.get("risk", "Low").lower() == "low":
        clause["suggestion"] = "No major change required."
        return clause

    clause_text = clause.get("text", "")
    clause_type = clause.get("type", "Other")
    risk_level = clause.get("risk", "Medium")
    reason = clause.get("reason", "")

    # Prompt template for the LLM
    prompt_template = """
    You are an expert contract lawyer. 
    Analyze the following contract clause, which has been identified as having a {risk_level} risk.
    The reason for this risk is: {reason}
    
    Clause Text:
    "{clause_text}"
    
    Clause Type: {clause_type}
    
    Task:
    Provide a revised, safer, and more balanced version of this clause or a specific instruction on how to amend it to reduce legal, financial, and business risk.
    
    Rules:
    1. Keep it professional, simple, and contract-friendly.
    2. Do NOT include any legal advice disclaimers.
    3. Output ONLY the suggested text, nothing else. No introductions or formatting.
    """
    
    prompt = PromptTemplate(
        input_variables=["risk_level", "reason", "clause_text", "clause_type"],
        template=prompt_template
    )
    
    try:
        # Chain the prompt and the LLM
        chain = prompt | llm
        
        # Run the LLM
        response = chain.invoke({
            "risk_level": risk_level,
            "reason": reason,
            "clause_text": clause_text,
            "clause_type": clause_type
        })
        
        # Clean up the response just in case the LLM adds extra whitespace
        suggestion = response.strip()
        
        # If the LLM returned empty string or something went wrong, use fallback
        if not suggestion:
            suggestion = get_fallback_suggestion(clause_type)
            
    except Exception as e:
        # If Ollama is not running, or LLM fails for any reason, use the fallback system
        print(f"Warning: LLM failed for clause ID {clause.get('id', 'Unknown')}. Using fallback. Error: {e}")
        suggestion = get_fallback_suggestion(clause_type)

    # Add the suggestion field to the clause
    clause["suggestion"] = suggestion
    
    return clause

def suggestion_agent(clauses):
    """
    Takes a list of enriched contract clauses, processes them, and adds a suggestion field.
    Returns the updated list of clauses.
    """
    updated_clauses = []
    
    for clause in clauses:
        # We create a copy of the dictionary to avoid mutating the original input unexpectedly
        clause_copy = clause.copy()
        updated_clause = generate_clause_suggestion(clause_copy)
        updated_clauses.append(updated_clause)
        
    return updated_clauses

# Example usage (for testing)
if __name__ == "__main__":
    sample_clauses = [
        {
            "id": 1,
            "text": "The company may update these terms at any time.",
            "type": "Other",
            "risk": "Low",
            "reason": "Standard boilerplate."
        },
        {
            "id": 2,
            "text": "Vendor shall not be liable for any damages.",
            "type": "Liability",
            "risk": "High",
            "reason": "Vendor avoids all liability."
        }
    ]
    
    print("Testing suggestion_agent...")
    results = suggestion_agent(sample_clauses)
    print(json.dumps(results, indent=2))
