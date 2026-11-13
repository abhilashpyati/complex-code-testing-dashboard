"""
Report Service — generates JSON and HTML reports from analysis results.
White-themed, comprehensive reporting without coverage dependencies.
"""
import os
import json
import html as html_lib
from datetime import datetime
from typing import Dict


def generate_json_report(result: Dict) -> str:
    """Return a JSON string of the full analysis result."""
    return json.dumps(result, indent=2, default=str)


def generate_html_report(result: Dict) -> str:
    """Generate a self-contained professional white-themed HTML report from analysis result."""
    health = result.get("health_score", 0)
    summary = result.get("summary", {})
    prediction = result.get("defect_prediction", {})
    complexity = result.get("complexity", {}).get("overall", {})
    timestamp = result.get("timestamp", datetime.now().isoformat())
    filename = html_lib.escape(result.get("filename", "user_code.py"))
    criteria_map = result.get("criteria", {})
    pylint_score = result.get("pylint_score", -1)

    health_color = "#16a34a" if health >= 70 else "#d97706" if health >= 40 else "#dc2626"
    risk_category = prediction.get("category", "LOW")
    risk_color = {
        "LOW": "#16a34a",
        "MODERATE": "#d97706",
        "HIGH": "#ea580c",
        "CRITICAL": "#dc2626",
    }.get(risk_category, "#64748b")

    avg_complexity_val = complexity.get("average")
    avg_complexity_str = f"{avg_complexity_val:.1f}" if avg_complexity_val is not None else "N/A"

    pylint_score_str = f"{pylint_score:.1f}/10" if pylint_score >= 0 else "N/A"

    pred_score_val = prediction.get("score", 0)
    pred_score_str = f"{pred_score_val:.0f}/100" if pred_score_val is not None else "N/A"

    total_findings_count = sum(len(f) for f in result.get("findings", {}).values())

    # Build criteria rows with safe HTML escaping
    criteria_rows = ""
    for tool_key, crit_list in criteria_map.items():
        for c in crit_list:
            status = c.get("status", "NOT_EXECUTED")
            status_class = {
                "PASSED": "status-pass",
                "WARNING": "status-warn",
                "FAILED": "status-fail",
                "NOT_EXECUTED": "status-ne",
                "NOT_APPLICABLE": "status-na",
            }.get(status, "status-ne")
            c_id = html_lib.escape(str(c.get("id", "")))
            c_name = html_lib.escape(str(c.get("name", "")))
            c_tool = html_lib.escape(str(c.get("tool", "")))
            c_details = html_lib.escape(str(c.get("details", ""))[:300])
            c_rec = html_lib.escape(str(c.get("recommendation", ""))[:200])

            display_status = "N/A" if status == "NOT_APPLICABLE" else status
            criteria_rows += f"""
            <tr>
                <td style="font-family:monospace;font-weight:600;color:#2563eb;">{c_id}</td>
                <td><strong>{c_name}</strong></td>
                <td>{c_tool}</td>
                <td><span class="badge {status_class}">{display_status}</span></td>
                <td class="details-cell">{c_details}</td>
                <td class="rec-cell">{c_rec}</td>
            </tr>"""

    findings_rows = ""
    for tool, findings in result.get("findings", {}).items():
        for f in findings[:35]:
            f_tool = html_lib.escape(str(tool).capitalize())
            f_code = html_lib.escape(str(f.get("code", "")))
            f_line = html_lib.escape(str(f.get("line", "")))
            f_msg = html_lib.escape(str(f.get("message", ""))[:300])
            severity = html_lib.escape(str(f.get("severity", f.get("type", ""))))
            findings_rows += f"""
            <tr>
                <td><strong>{f_tool}</strong></td>
                <td><code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:0.85em;">{f_code}</code></td>
                <td>L{f_line}</td>
                <td>{f_msg}</td>
                <td><span class="sev-tag sev-{severity.upper()}">{severity}</span></td>
            </tr>"""

    high_risk = ""
    for fn in prediction.get("high_risk_functions", []):
        fn_name = html_lib.escape(str(fn.get("name", "")))
        fn_type = html_lib.escape(str(fn.get("type", "")))
        fn_line = html_lib.escape(str(fn.get("line", "")))
        fn_cx = html_lib.escape(str(fn.get("complexity", "")))
        fn_risk = html_lib.escape(str(fn.get("risk", "")))
        fn_grade = html_lib.escape(str(fn.get("grade", "")))
        high_risk += f"""
        <tr>
            <td><code>{fn_name}</code></td>
            <td>{fn_type}</td>
            <td>L{fn_line}</td>
            <td><strong>{fn_cx}</strong></td>
            <td><span style="color:{_risk_color(fn_risk)};font-weight:600;">{fn_risk}</span></td>
            <td><strong>{fn_grade}</strong></td>
        </tr>"""

    recommendations = ""
    for rec in prediction.get("recommendations", []):
        recommendations += f"<li>{html_lib.escape(str(rec))}</li>"

    component_items = []
    for k, v in prediction.get("components", {}).items():
        name = html_lib.escape(str(k.replace("_", " ").title()))
        sc = v.get("score")
        wt = v.get("weight", 0)
        contrib = v.get("contribution", 0)
        eff_wt = v.get("effective_weight", wt)
        if sc is not None:
            component_items.append(
                f"<li><strong>{name}</strong>: score {sc:.1f} &times; weight {wt:.1%} "
                f"(effective {eff_wt:.1%}) = <strong>{contrib:.1f} pts</strong></li>"
            )
        else:
            component_items.append(
                f"<li><strong>{name}</strong>: <em>Not Available (omitted from weighted aggregate)</em></li>"
            )
    component_breakdown_html = "".join(component_items)

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code Analysis Report — {filename}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: #f8fafc;
    color: #0f172a;
    margin: 0;
    padding: 2.5rem;
    line-height: 1.5;
  }}
  h1, h2, h3 {{ color: #0f172a; font-weight: 700; margin-top: 0; }}
  h2 {{ margin-top: 2.5rem; font-size: 1.25rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }}
  .header {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-top: 4px solid #2563eb;
    color: #0f172a;
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .header h1 {{ margin: 0; font-size: 1.75rem; color: #1e3a8a; }}
  .header p {{ margin: 0.5rem 0 0; color: #64748b; font-size: 0.95rem; }}
  .metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .metric-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    text-align: center;
  }}
  .metric-card .value {{ font-size: 2rem; font-weight: 800; line-height: 1.2; }}
  .metric-card .label {{ font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.4rem; }}
  table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    margin-bottom: 2rem;
  }}
  th {{
    background: #f1f5f9;
    color: #334155;
    padding: 0.75rem 1rem;
    text-align: left;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #e2e8f0;
  }}
  td {{
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.875rem;
    vertical-align: top;
    color: #334155;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8fafc; }}
  .badge {{
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}
  .status-pass {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
  .status-warn {{ background: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }}
  .status-fail {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}
  .status-ne {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}
  .status-na {{ background: #f8fafc; color: #64748b; border: 1px solid #cbd5e1; }}
  .sev-tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
  .sev-HIGH {{ background: #fee2e2; color: #b91c1c; }}
  .sev-MEDIUM {{ background: #fef3c7; color: #b45309; }}
  .sev-LOW {{ background: #dcfce7; color: #15803d; }}
  .section {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    margin-bottom: 2rem;
  }}
  ul {{ padding-left: 1.5rem; margin-top: 0.5rem; }}
  li {{ margin-bottom: 0.5rem; color: #334155; }}
  .details-cell, .rec-cell {{ max-width: 320px; word-break: break-word; }}
  .methodology {{
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    padding: 1rem 1.25rem;
    border-radius: 0 6px 6px 0;
    margin-bottom: 1.25rem;
    font-size: 0.85rem;
    color: #1e3a8a;
  }}
  footer {{
    text-align: center;
    color: #64748b;
    font-size: 0.8rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e2e8f0;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>Code Analysis Report</h1>
  <p>Source file: <strong>{filename}</strong> &nbsp;|&nbsp; Generated on: {timestamp}</p>
</div>

<div class="metrics">
  <div class="metric-card">
    <div class="value" style="color:{health_color}">{health}</div>
    <div class="label">Health Score / 100</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#16a34a">{summary.get('PASSED', 0)}</div>
    <div class="label">Criteria Passed</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#d97706">{summary.get('WARNING', 0)}</div>
    <div class="label">Warnings</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#dc2626">{summary.get('FAILED', 0)}</div>
    <div class="label">Failed</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#2563eb">{pylint_score_str}</div>
    <div class="label">Pylint Score</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#0284c7">{total_findings_count}</div>
    <div class="label">Total Findings</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#7c3aed">{avg_complexity_str}</div>
    <div class="label">Avg Complexity</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:{risk_color}">{risk_category}</div>
    <div class="label">Defect Risk ({pred_score_str})</div>
  </div>
</div>

<h2>25 Core Test Criteria Evaluation</h2>
<table>
  <thead><tr><th>ID</th><th>Criterion</th><th>Tool</th><th>Status</th><th>Details</th><th>Recommendation</th></tr></thead>
  <tbody>{criteria_rows}</tbody>
</table>

<h2>Static & Security Findings</h2>
<table>
  <thead><tr><th>Tool</th><th>Code</th><th>Line</th><th>Message</th><th>Severity</th></tr></thead>
  <tbody>{findings_rows if findings_rows else '<tr><td colspan="5" style="text-align:center;color:#16a34a;padding:1.5rem;">No static or security issues found</td></tr>'}</tbody>
</table>

<h2>Cyclomatic Complexity & Functions (Radon)</h2>
<table>
  <thead><tr><th>Name</th><th>Type</th><th>Line</th><th>Complexity</th><th>Risk</th><th>Grade</th></tr></thead>
  <tbody>{high_risk if high_risk else '<tr><td colspan="6" style="text-align:center;color:#16a34a;padding:1.5rem;">No high-risk functions detected</td></tr>'}</tbody>
</table>

<div class="section">
  <h2>Defect Risk Assessment (Heuristic)</h2>
  <div class="methodology">{html_lib.escape(str(prediction.get('methodology_note', '')))}</div>
  <p><strong>Overall Risk Score:</strong> <span style="color:{risk_color};font-size:1.4rem;font-weight:800">{prediction.get('score', 0):.1f} / 100</span>
  &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Category:</strong> <span style="color:{risk_color};font-weight:700">{risk_category}</span></p>

  <h3 style="font-size:1rem;margin-top:1.25rem;">Component Breakdown</h3>
  <ul>
  {component_breakdown_html}
  </ul>

  <h3 style="font-size:1rem;margin-top:1.25rem;">Recommendations</h3>
  <ul>{recommendations if recommendations else '<li>Code quality is in good standing.</li>'}</ul>
</div>

<footer>
  Complex Code Testing Dashboard &nbsp;|&nbsp; 7th Semester Software Testing Project &nbsp;|&nbsp; {timestamp}
</footer>
</body>
</html>"""
    return html_out


def _risk_color(risk: str) -> str:
    return {
        "LOW": "#16a34a",
        "MODERATE": "#d97706",
        "HIGH": "#ea580c",
        "CRITICAL": "#dc2626",
    }.get(risk, "#64748b")
