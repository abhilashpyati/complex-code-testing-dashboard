"""
Report Service — generates JSON and HTML reports from analysis results.
"""
import os
import json
from datetime import datetime
from typing import Dict


def generate_json_report(result: Dict) -> str:
    """Return a JSON string of the full analysis result."""
    return json.dumps(result, indent=2, default=str)


def generate_html_report(result: Dict) -> str:
    """Generate a self-contained HTML report from analysis result."""
    health = result.get("health_score", 0)
    summary = result.get("summary", {})
    prediction = result.get("defect_prediction", {})
    coverage = result.get("coverage_metrics", {})
    complexity = result.get("complexity", {}).get("overall", {})
    timestamp = result.get("timestamp", datetime.now().isoformat())
    filename = result.get("filename", "user_code.py")
    criteria_map = result.get("criteria", {})

    health_color = "#22c55e" if health >= 70 else "#f59e0b" if health >= 40 else "#ef4444"
    risk_color = {
        "LOW": "#22c55e",
        "MODERATE": "#f59e0b",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
    }.get(prediction.get("category", "LOW"), "#6b7280")

    # Build criteria rows
    criteria_rows = ""
    for tool_key, crit_list in criteria_map.items():
        for c in crit_list:
            status = c["status"]
            status_class = {
                "PASSED": "status-pass",
                "WARNING": "status-warn",
                "FAILED": "status-fail",
                "NOT_EXECUTED": "status-ne",
            }.get(status, "status-ne")
            criteria_rows += f"""
            <tr>
                <td>{c['id']}</td>
                <td>{c['name']}</td>
                <td>{c['tool']}</td>
                <td><span class="badge {status_class}">{status}</span></td>
                <td class="details-cell">{c['details'][:200]}</td>
                <td class="rec-cell">{c.get('recommendation', '')[:150]}</td>
            </tr>"""

    findings_rows = ""
    for tool, findings in result.get("findings", {}).items():
        for f in findings[:20]:
            severity = f.get("severity", f.get("type", ""))
            findings_rows += f"""
            <tr>
                <td>{tool}</td>
                <td>{f.get('code', '')}</td>
                <td>{f.get('line', '')}</td>
                <td>{f.get('message', f.get('message', ''))[:200]}</td>
                <td>{severity}</td>
            </tr>"""

    high_risk = ""
    for fn in prediction.get("high_risk_functions", []):
        high_risk += f"""
        <tr>
            <td><code>{fn['name']}</code></td>
            <td>{fn['type']}</td>
            <td>{fn['line']}</td>
            <td>{fn['complexity']}</td>
            <td><span style="color:{_risk_color(fn['risk'])}">{fn['risk']}</span></td>
            <td>{fn['grade']}</td>
        </tr>"""

    recommendations = ""
    for rec in prediction.get("recommendations", []):
        recommendations += f"<li>{rec}</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Code Analysis Report — {filename}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 2rem; }}
  h1, h2, h3 {{ color: #0f172a; }}
  .header {{ background: linear-gradient(135deg, #1e3a5f, #0ea5e9); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
  .header h1 {{ color: white; margin: 0; }}
  .header p {{ margin: 0.5rem 0 0; opacity: 0.85; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .metric-card {{ background: white; border-radius: 10px; padding: 1.2rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); text-align: center; }}
  .metric-card .value {{ font-size: 2rem; font-weight: 700; }}
  .metric-card .label {{ font-size: 0.8rem; color: #64748b; margin-top: 0.3rem; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 2rem; }}
  th {{ background: #1e3a5f; color: white; padding: 0.7rem 1rem; text-align: left; font-size: 0.85rem; }}
  td {{ padding: 0.6rem 1rem; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8fafc; }}
  .badge {{ padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
  .status-pass {{ background: #dcfce7; color: #16a34a; }}
  .status-warn {{ background: #fef9c3; color: #ca8a04; }}
  .status-fail {{ background: #fee2e2; color: #dc2626; }}
  .status-ne {{ background: #f1f5f9; color: #64748b; }}
  .section {{ background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 2rem; }}
  ul {{ padding-left: 1.5rem; }}
  li {{ margin-bottom: 0.5rem; }}
  .details-cell, .rec-cell {{ max-width: 300px; word-break: break-word; }}
  .methodology {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 1rem 1.5rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem; font-size: 0.85rem; }}
  footer {{ text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 2rem; }}
</style>
</head>
<body>
<div class="header">
  <h1>🔍 Code Analysis Report</h1>
  <p>File: <strong>{filename}</strong> &nbsp;|&nbsp; Generated: {timestamp}</p>
</div>

<div class="metrics">
  <div class="metric-card">
    <div class="value" style="color:{health_color}">{health}</div>
    <div class="label">Health Score / 100</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#22c55e">{summary.get('PASSED', 0)}</div>
    <div class="label">Criteria Passed</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#f59e0b">{summary.get('WARNING', 0)}</div>
    <div class="label">Warnings</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:#ef4444">{summary.get('FAILED', 0)}</div>
    <div class="label">Failed</div>
  </div>
  <div class="metric-card">
    <div class="value">{coverage.get('statement_coverage', 0):.1f}%</div>
    <div class="label">Statement Coverage</div>
  </div>
  <div class="metric-card">
    <div class="value">{coverage.get('branch_coverage', 0):.1f}%</div>
    <div class="label">Branch Coverage</div>
  </div>
  <div class="metric-card">
    <div class="value">{complexity.get('average', 0):.1f}</div>
    <div class="label">Avg Complexity</div>
  </div>
  <div class="metric-card">
    <div class="value" style="color:{risk_color}">{prediction.get('category', 'N/A')}</div>
    <div class="label">Defect Risk (Score: {prediction.get('score', 0):.0f})</div>
  </div>
</div>

<h2>📋 25 Test Criteria</h2>
<table>
  <thead><tr><th>ID</th><th>Criterion</th><th>Tool</th><th>Status</th><th>Details</th><th>Recommendation</th></tr></thead>
  <tbody>{criteria_rows}</tbody>
</table>

<h2>🔍 Static & Security Findings</h2>
<table>
  <thead><tr><th>Tool</th><th>Code</th><th>Line</th><th>Message</th><th>Severity</th></tr></thead>
  <tbody>{findings_rows if findings_rows else '<tr><td colspan="5" style="text-align:center;color:#22c55e">No significant findings</td></tr>'}</tbody>
</table>

<h2>🔀 High-Risk Functions (Complexity)</h2>
<table>
  <thead><tr><th>Name</th><th>Type</th><th>Line</th><th>Complexity</th><th>Risk</th><th>Grade</th></tr></thead>
  <tbody>{high_risk if high_risk else '<tr><td colspan="6" style="text-align:center;color:#22c55e">No high-risk functions detected</td></tr>'}</tbody>
</table>

<div class="section">
  <h2>🤖 Defect Risk Assessment</h2>
  <div class="methodology">{prediction.get('methodology_note', '')}</div>
  <p><strong>Risk Score:</strong> <span style="color:{risk_color};font-size:1.3rem;font-weight:700">{prediction.get('score', 0):.1f} / 100</span>
  &nbsp;|&nbsp; <strong>Category:</strong> <span style="color:{risk_color};font-weight:700">{prediction.get('category', 'N/A')}</span></p>

  <h3>Component Breakdown</h3>
  <ul>
  {''.join(f"<li><strong>{k.replace('_', ' ').title()}</strong>: score {v['score']:.1f} × weight {v['weight']:.0%} = {v['contribution']:.1f} pts</li>" for k, v in prediction.get('components', {}).items())}
  </ul>

  <h3>Recommendations</h3>
  <ul>{recommendations}</ul>
</div>

<footer>
  Generated by Complex Code Testing Dashboard &nbsp;|&nbsp; {timestamp}
</footer>
</body>
</html>"""
    return html


def _risk_color(risk: str) -> str:
    return {
        "LOW": "#22c55e",
        "MODERATE": "#f59e0b",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
    }.get(risk, "#6b7280")
