from agents.classification_agent import classification_agent
import json

mock_data = {
    "clauses": [
        {
            "id": "3.1",
            "text": "The Company’s total liability shall be unlimited..."
        },
        {
            "id": "4.1",
            "text": "Client may terminate this agreement with 30 days notice"
        },
        {
            "id": "6",
            "text": "This Agreement shall be governed by laws of Maharashtra"
        }
    ]
}

result = classification_agent(mock_data)

print(json.dumps(result, indent=2))