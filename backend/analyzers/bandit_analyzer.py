"""
Bandit Security Analyzer — Security Vulnerability Analysis (Group 4 of 25 Core Criteria).

Five criteria:
1. BD-01: Hardcoded Credentials and Sensitive Information (B105/B106/B107/B108)
2. BD-02: Unsafe Function Usage (B307/B102 eval/exec)
3. BD-03: Weak Cryptographic Practices (B303/B304/B305/B324)
4. BD-04: Insecure Subprocess Usage (B602/B603/B604/B605)
5. BD-05: Overall Security Findings and Severity
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
                f"No {name.lower()} issues detected",
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

    # Criterion 1: BD-01 Hardcoded Credentials and Sensitive Information
    criteria.append(_make(
        "BD-01", "Hardcoded Credentials and Sensitive Information",
        ["B105", "B106", "B107", "B108"],
        "Use environment variables or secret managers for credentials",
    ))

    # Criterion 2: BD-02 Unsafe Function Usage (eval/exec)
    criteria.append(_make(
        "BD-02", "Unsafe Function Usage (eval/exec)",
        ["B307", "B102", "B308"],
        "Replace eval/exec with safe alternatives (ast.literal_eval, explicit parsing)",
    ))

    # Criterion 3: BD-03 Weak Cryptographic Practices
    criteria.append(_make(
        "BD-03", "Weak Cryptographic Practices",
        ["B303", "B304", "B305", "B324", "B413"],
        "Use SHA-256 or stronger; avoid MD5, SHA-1, DES, RC4",
    ))

    # Criterion 4: BD-04 Insecure Subprocess Usage
    criteria.append(_make(
        "BD-04", "Insecure Subprocess Usage",
        ["B602", "B603", "B604", "B605", "B606", "B607"],
        "Avoid shell=True; use argument lists and validate inputs",
    ))

    # Criterion 5: BD-05 Overall Security Findings and Severity
    if tool_missing:
        criteria.append(make_criterion(
            "BD-05", "Overall Security Findings and Severity",
            "NOT_EXECUTED",
            "Bandit not available",
            TOOL,
            recommendation="Run Bandit security scanner regularly",
        ))
    else:
        high_sev = [f for f in findings if f["severity"] == "HIGH"]
        med_sev = [f for f in findings if f["severity"] == "MEDIUM"]
        low_sev = [f for f in findings if f["severity"] == "LOW"]

        if not findings:
            criteria.append(make_criterion(
                "BD-05", "Overall Security Findings and Severity",
                "PASSED",
                "No security vulnerabilities or warnings detected across any severity levels",
                TOOL,
                recommendation="Continue maintaining secure coding practices",
            ))
        elif high_sev:
            criteria.append(make_criterion(
                "BD-05", "Overall Security Findings and Severity",
                "FAILED",
                f"{len(high_sev)} HIGH severity, {len(med_sev)} MEDIUM, {len(low_sev)} LOW security finding(s): "
                + "; ".join(f"Line {f['line']}: [{f['code']}] {f['message']}" for f in high_sev[:3]),
                TOOL,
                line=high_sev[0]["line"] if high_sev else 0,
                recommendation="Immediately remediate all HIGH severity security vulnerabilities",
            ))
        elif med_sev:
            criteria.append(make_criterion(
                "BD-05", "Overall Security Findings and Severity",
                "WARNING",
                f"{len(med_sev)} MEDIUM severity, {len(low_sev)} LOW security finding(s): "
                + "; ".join(f"Line {f['line']}: [{f['code']}] {f['message']}" for f in med_sev[:3]),
                TOOL,
                line=med_sev[0]["line"] if med_sev else 0,
                recommendation="Review and address MEDIUM severity security findings",
            ))
        else:
            criteria.append(make_criterion(
                "BD-05", "Overall Security Findings and Severity",
                "WARNING",
                f"{len(low_sev)} LOW severity security advisory finding(s): "
                + "; ".join(f"Line {f['line']}: [{f['code']}] {f['message']}" for f in low_sev[:3]),
                TOOL,
                line=low_sev[0]["line"] if low_sev else 0,
                recommendation="Review low-severity findings for defense-in-depth hardening",
            ))

    return criteria
