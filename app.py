"""
Contract Risk Analyzer — Flask Backend
Pipeline: ingestion → structuring → classification → risk analysis
"""
import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify

from agents.ingestion_agent import ingestion_agent
from agents.structuring_agent import structuring_agent
from agents.classification_agent import classification_agent
from agents.risk_agent import risk_agent

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Accept a contract file, run the full pipeline, return JSON results.
    """
    # ── Handle file upload ───────────────────────────────────────
    if "file" not in request.files:
        return jsonify({"status": "error", "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "error": "Empty filename"}), 400

    # Save to temp location
    filename = file.filename
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    try:
        # ── Step 1: Ingest ───────────────────────────────────────
        ingested = ingestion_agent(save_path)

        if ingested["status"] != "success":
            return jsonify({
                "status": "error",
                "error": ingested.get("error", "Failed to read file"),
            }), 400

        raw_text = ingested["raw_text"]

        # ── Step 2: Structure ────────────────────────────────────
        structured = structuring_agent(raw_text)

        # ── Step 3: Classify ─────────────────────────────────────
        classified = classification_agent(structured)

        # ── Step 4: Risk Analysis ────────────────────────────────
        user_role = request.form.get("user_role", "Contractor")
        risk_result = risk_agent(classified, user_role=user_role)

        # ── Build response ───────────────────────────────────────
        categories = {}
        risk_breakdown = {"High": 0, "Medium": 0, "Low": 0}
        for clause in risk_result["clauses"]:
            cat = clause.get("type", "Other")
            categories[cat] = categories.get(cat, 0) + 1
            risk_lvl = clause.get("risk", "Low")
            if risk_lvl in risk_breakdown:
                risk_breakdown[risk_lvl] += 1

        sections_data = []
        for sec in risk_result.get("sections", []):
            sections_data.append(_serialize_section(sec))

        return jsonify({
            "status": "success",
            "filename": filename,
            "user_role": user_role,
            "raw_text_length": len(raw_text),
            "total_sections": len(risk_result.get("sections", [])),
            "total_clauses": len(risk_result["clauses"]),
            "category_breakdown": categories,
            "risk_breakdown": risk_breakdown,
            "sections": sections_data,
            "clauses": risk_result["clauses"],
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

    finally:
        # Clean up uploaded file (ignore PermissionError on Windows)
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except PermissionError:
            pass


def _serialize_section(sec):
    """Recursively serialize a section node for JSON."""
    return {
        "id": sec["id"],
        "title": sec.get("title", ""),
        "text": sec.get("text", ""),
        "level": sec.get("level", 0),
        "type": sec.get("type", ""),
        "confidence": sec.get("confidence", ""),
        "children": [_serialize_section(c) for c in sec.get("children", [])],
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
