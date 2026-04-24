import json
import os
import re

# Local flat-file database to store past knowledge
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "rag_db.json")

def _get_word_set(text: str) -> set:
    """Extract a set of words for basic similarity matching."""
    # Limit text length to ensure fast tokenization during prototype
    words = re.findall(r'\w+', text.lower()[:1000])
    return set(words)

def store_clauses(clauses: list):
    """
    Store analyzed clauses into the local JSON DB.
    This builds the 'Knowledge Base' over time.
    """
    existing_db = []
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r") as f:
                existing_db = json.load(f)
        except Exception:
            pass

    new_data = []
    for c in clauses:
        text = c.get("text", "")
        # Only store meaningful clauses
        if c.get("risk") and len(text.split()) > 10:
            new_data.append({
                "text": text,
                "risk": c["risk"],
                "reason": c.get("reason", ""),
                "type": c.get("type", "Unknown"),
                "user_role": c.get("user_role", "Unknown")
            })
            
    existing_db.extend(new_data)
    
    # Deduplicate based on text and user_role to prevent database bloat
    unique = {f"{c['text']}_{c['user_role']}": c for c in existing_db}
    
    with open(DB_PATH, "w") as f:
        json.dump(list(unique.values()), f, indent=2)


def retrieve_similar(query_text: str, user_role: str, top_k: int = 1) -> list:
    """
    Retrieve past clauses that are similar to the query.
    Uses basic Jaccard similarity for the prototype.
    """
    if not os.path.exists(DB_PATH):
        return []
        
    try:
        with open(DB_PATH, "r") as f:
            db = json.load(f)
    except Exception:
        return []
        
    # Filter by role to ensure the context is strictly relevant to the perspective
    context_db = [c for c in db if c.get("user_role") == user_role]
    if not context_db:
        return []
        
    query_words = _get_word_set(query_text)
    
    scored = []
    for past_item in context_db:
        past_words = _get_word_set(past_item["text"])
        
        # Jaccard similarity calculation
        intersection = len(query_words.intersection(past_words))
        union = len(query_words.union(past_words))
        similarity = intersection / union if union > 0 else 0
        
        # Inject the similarity score so the caller can use it for caching logic
        past_item_copy = past_item.copy()
        past_item_copy["_sim_score"] = similarity
        
        scored.append((similarity, past_item_copy))
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Only return items with a meaningful overlap (e.g. >10%)
    best_matches = [item for score, item in scored if score > 0.10]
    
    return best_matches[:top_k]
