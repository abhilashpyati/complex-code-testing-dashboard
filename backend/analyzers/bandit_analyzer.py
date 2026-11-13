"""
Bandit Security Analyzer — Module 5: Security Analysis.

Five criteria:
1. No Use of eval() / exec() (B307/B102)
2. No Weak Cryptographic Algorithms (B303/B304/B305/B324)
3. No Hardcoded Credentials (B105/B106/B107)
4. No Insecure Subprocess / Shell Injection (B602/B603/B604/B605)
5. No Other High-Severity Security Findings
"""
import os
import json
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Bandit"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run Bandit security analysis and return five criteria."""
    python = get_python_executable()
    report_path = os.path.join(workspace_dir, "bandit_report.json")
    cmd = [
        python, "-m", "bandit",
        "-f", "json",
        "-o", report_path,
        code_path,
    ]
    result = run_tool(cmd, workspace_dir)

    # Bandit exits with 1 if issues found — not an error
    findings = []
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            findings = _extract_findings(report)
        except Exception:
            pass

    if not findings and result.get("stdout"):
        # Try stdout JSON
        try:
            report = json.loads(result["stdout"])
            findings = _extract_findings(report)
        except Exception:
            pass

    criteria = _build_criteria(result, findings)
    return {"criteria": criteria, "raw": result, "findings": findings}


def _extract_findings(report: Dict) -> List[Dict]:
    findings = []
    for item in report.get("results", []):
        findings.append({
            "file": os.path.basename(item.get("filename", "")),
            "line": item.get("line_number", 0),
            "code": item.get("test_id", ""),
            "name": item.get("test_name", ""),
            "severity": item.get("issue_severity", "LOW"),
            "confidence": item.get("issue_confidence", "LOW"),
            "message": item.get("issue_text", ""),
            "cwe": item.get("issue_cwe", {}).get("id", ""),
        })
    return findings


def _build_criteria(result: Dict, findings: List[Dict]) -> List[Dict]:
    criteria = []
    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    def _make(crit_id, name, test_ids, recommendation):
        if tool_missing:
            return make_criterion(
                crit_id, name, "NOT_EXECUTED",
                f"Bandit not available: {result.get('error', 'timeout')}",
                TOOL, recommendation=recommendation,
            )
        matched = [f for f in findings if f["code"] in test_ids]
        if not matched:
            return make_criterion(
                crit_id, name, "PASSED",
                f"No {name} issues detected",
                TOOL, recommendation=recommendation,
            )
        severity_map = {"HIGH": "FAILED", "MEDIUM": "WARNING", "LOW": "WARNING"}
        worst = "WARNING"
        for f in matched:
            if severity_map.get(f["severity"], "WARNING") == "FAILED":
                worst = "FAILED"
                break
        detail = "; ".join(
            f"Line {f['line']}: [{f['code']}] {f['message']}"
            for f in matched[:4]
        )
        return make_criterion(
            crit_id, name, worst,
            f"{len(matched)} finding(s): {detail}",
            TOOL,
            line=matched[0]["line"] if matched else 0,
            recommendation=recommendation,
        )

    criteria.append(_make(
        "BD-01", "No eval() / exec() Usage",
        ["B307", "B102", "B308"],
        "Replace eval/exec with safe alternatives (ast.literal_eval, explicit parsing)",
    ))
    criteria.append(_make(
        "BD-02", "No Weak Cryptographic Algorithms",
        ["B303", "B304", "B305", "B324", "B413"],
        "Use SHA-256 or stronger; avoid MD5, SHA-1, DES, RC4",
    ))
    criteria.append(_make(
        "BD-03", "No Hardcoded Credentials",
        ["B105", "B106", "B107", "B108"],
        "Use environment variables or secret managers for credentials",
    ))
    criteria.append(_make(
        "BD-04", "No Insecure Subprocess / Shell Injection",
        ["B602", "B603", "B604", "B605", "B606", "B607"],
        "Avoid shell=True; use argument lists and validate inputs",
    ))

    # Criterion 5: Any remaining HIGH severity findings
    if tool_missing:
        criteria.append(make_criterion(
            "BD-05", "No Other High-Severity Findings",
            "NOT_EXECUTED",
            "Bandit not available",
            TOOL,
        ))
    else:
        known_codes = {
            "B307", "B102", "B308",
            "B303", "B304", "B305", "B324", "B413",
            "B105", "B106", "B107", "B108",
            "B602", "B603", "B604", "B605", "B606", "B607",
        }
        other_high = [
            f for f in findings
            if f["code"] not in known_codes and f["severity"] == "HIGH"
        ]
        other_medium = [
            f for f in findings
            if f["code"] not in known_codes and f["severity"] == "MEDIUM"
        ]
        if not other_high and not other_medium:
            criteria.append(make_criterion(
                "BD-05", "No Other High-Severity Findings",
                "PASSED",
                "No additional high-severity security issues detected",
                TOOL,
                recommendation="Run Bandit regularly as part of CI/CD",
            ))
        elif other_high:
            detail = "; ".join(
                f"Line {f['line']}: [{f['code']}] {f['message']}" for f in other_high[:4]
            )
            criteria.append(make_criterion(
                "BD-05", "No Other High-Severity Findings",
                "FAILED",
                f"{len(other_high)} high-severity finding(s): {detail}",
                TOOL,
                line=other_high[0]["line"],
                recommendation="Address all HIGH severity Bandit findings before deployment",
            ))
        else:
            detail = "; ".join(
                f"Line {f['line']}: [{f['code']}] {f['message']}" for f in other_medium[:4]
            )
            criteria.append(make_criterion(
                "BD-05", "No Other High-Severity Findings",
                "WARNING",
                f"{len(other_medium)} medium-severity finding(s): {detail}",
                TOOL,
                recommendation="Review and address medium-severity security findings",
            ))

    return criteria
