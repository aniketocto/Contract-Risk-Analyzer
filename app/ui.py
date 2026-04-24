"""
Gradio UI – Contract Risk Analyzer
====================================
Provides a web interface for uploading contracts and viewing
clause-wise risk analysis, scores, and suggestions.
"""

import sys, os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from app.main import run_pipeline

# ── Custom CSS for premium look ─────────────────────────────────
CUSTOM_CSS = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
.gr-button-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    font-weight: 600 !important;
}
.gr-button-primary:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
}
.score-display {
    font-size: 3em;
    font-weight: 700;
    text-align: center;
    padding: 20px;
    border-radius: 12px;
    margin: 10px 0;
}
.risk-high { color: #ef4444; }
.risk-medium { color: #f59e0b; }
.risk-low { color: #10b981; }
"""


def _get_score_color(score: float) -> str:
    """Return color class based on risk score."""
    if score >= 66:
        return "risk-high"
    elif score >= 33:
        return "risk-medium"
    return "risk-low"


def _get_score_label(score: float) -> str:
    """Return human-readable risk label."""
    if score >= 66:
        return "🔴 HIGH RISK"
    elif score >= 33:
        return "🟡 MODERATE RISK"
    return "🟢 LOW RISK"


def analyze_contract(file):
    """
    Called when user uploads a file and clicks Analyze.
    Runs the full pipeline and formats output for the UI.
    """
    if file is None:
        return (
            "<p style='color:#ef4444;font-weight:600;'>⚠️ Please upload a contract file.</p>",
            None,
        )

    try:
        result = run_pipeline(file)
    except Exception as e:
        return (
            f"<p style='color:#ef4444;font-weight:600;'>❌ Pipeline error: {e}</p>",
            None,
        )

    clauses = result["clauses"]
    score_data = result["score"]
    overall = score_data["overall_score"]
    summary = score_data["summary"]
    breakdown = score_data["breakdown"]

    # ── Score HTML ──────────────────────────────────────────────
    color = _get_score_color(overall)
    label = _get_score_label(overall)
    score_html = f"""
    <div style="text-align:center; padding:20px; background:linear-gradient(135deg,#1e1e2e,#2d2d44);
                border-radius:16px; margin:10px 0;">
        <div style="font-size:0.9em; color:#94a3b8; text-transform:uppercase; letter-spacing:2px;">
            Overall Risk Score
        </div>
        <div class="score-display {color}" style="font-size:3.5em; font-weight:800; margin:5px 0;">
            {overall}/100
        </div>
        <div style="font-size:1.2em; font-weight:600; color:#e2e8f0;">
            {label}
        </div>
    </div>
    """

    # ── Summary HTML ────────────────────────────────────────────
    summary_html = f"""
    <div style="display:flex; gap:15px; justify-content:center; margin:15px 0;">
        <div style="background:#fecaca; color:#991b1b; padding:12px 24px; border-radius:10px;
                    font-weight:700; text-align:center; min-width:100px;">
            🔴 High<br><span style="font-size:1.8em;">{summary['high']}</span>
        </div>
        <div style="background:#fef3c7; color:#92400e; padding:12px 24px; border-radius:10px;
                    font-weight:700; text-align:center; min-width:100px;">
            🟡 Medium<br><span style="font-size:1.8em;">{summary['medium']}</span>
        </div>
        <div style="background:#d1fae5; color:#065f46; padding:12px 24px; border-radius:10px;
                    font-weight:700; text-align:center; min-width:100px;">
            🟢 Low<br><span style="font-size:1.8em;">{summary['low']}</span>
        </div>
    </div>
    """

    # ── Breakdown HTML ──────────────────────────────────────────
    breakdown_rows = ""
    risk_colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
    for ctype, risk in breakdown.items():
        color_hex = risk_colors.get(risk, "#94a3b8")
        breakdown_rows += f"""
        <tr>
            <td style="padding:8px 12px; border-bottom:1px solid #334155;">{ctype}</td>
            <td style="padding:8px 12px; border-bottom:1px solid #334155;">
                <span style="color:{color_hex}; font-weight:700;">● {risk}</span>
            </td>
        </tr>"""

    breakdown_html = f"""
    <div style="margin:10px 0;">
        <h4 style="color:#e2e8f0; margin-bottom:8px;">📊 Risk Breakdown by Clause Type</h4>
        <table style="width:100%; border-collapse:collapse; background:#1e1e2e; border-radius:8px;">
            <thead>
                <tr style="background:#334155;">
                    <th style="padding:10px 12px; text-align:left; color:#94a3b8;">Clause Type</th>
                    <th style="padding:10px 12px; text-align:left; color:#94a3b8;">Risk Level</th>
                </tr>
            </thead>
            <tbody>{breakdown_rows}</tbody>
        </table>
    </div>
    """

    info_html = score_html + summary_html + breakdown_html

    # ── Clause table data ───────────────────────────────────────
    table_data = []
    for c in clauses:
        risk_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(c.get("risk", ""), "⚪")
        table_data.append([
            c.get("id", ""),
            c.get("type", "Unknown"),
            c.get("text", "")[:80] + ("..." if len(c.get("text", "")) > 80 else ""),
            f"{risk_emoji} {c.get('risk', 'N/A')}",
            c.get("reason", "N/A"),
            c.get("suggestion", "No suggestion"),
        ])

    return info_html, table_data


# ===========================================================================
# BUILD GRADIO UI
# ===========================================================================

def create_ui():
    """Build and return the Gradio Blocks interface."""
    with gr.Blocks(
        title="Contract Risk Analyzer",
    ) as app:
        # Header
        gr.HTML("""
        <div style="text-align:center; padding:20px 0 10px 0;">
            <h1 style="font-size:2.2em; font-weight:800;
                       background:linear-gradient(135deg,#667eea,#764ba2);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                       margin:0;">
                📄 Contract Risk Analyzer
            </h1>
            <p style="color:#94a3b8; font-size:1em; margin-top:5px;">
                AI-powered multi-agent system for contract clause analysis
            </p>
        </div>
        """)

        with gr.Row():
            # Left column – Upload
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="📎 Upload Contract",
                    file_types=[".pdf", ".docx", ".txt"],
                    type="filepath",
                )
                analyze_btn = gr.Button("🚀 Analyze Contract", variant="primary", size="lg")

            # Right column – Score & Summary
            with gr.Column(scale=2):
                score_output = gr.HTML(label="Risk Score & Summary")

        # Clause table
        gr.HTML("<h3 style='margin-top:20px; color:#e2e8f0;'>📋 Clause-wise Analysis</h3>")
        clause_table = gr.Dataframe(
            headers=["ID", "Type", "Clause Text", "Risk", "Reason", "Suggestion"],
            datatype=["number", "str", "str", "str", "str", "str"],
            label="Clause Details",
            wrap=True,
            interactive=False,
        )

        # Connect button to pipeline
        analyze_btn.click(
            fn=analyze_contract,
            inputs=[file_input],
            outputs=[score_output, clause_table],
        )

    return app


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="purple"),
        css=CUSTOM_CSS,
    )
