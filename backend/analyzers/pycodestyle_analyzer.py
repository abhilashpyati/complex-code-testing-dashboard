"""
Pycodestyle Analyzer — Module 6: Coding Standards (PEP 8).

Five criteria:
1. Indentation Compliance (E1xx)
2. Line Length Compliance (E501)
3. Whitespace Compliance (E2xx)
4. Blank Line Compliance (E3xx)
5. Import / Statement Compliance (E4xx/W6xx)
"""
import os
import re
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Pycodestyle"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run pycodestyle and return five criteria."""
    python = get_python_executable()
    cmd = [
        python, "-m", "pycodestyle",
        code_path,
        "--statistics",
        "--max-line-length=120",
        "--format=%(row)d:%(col)d: %(code)s %(text)s",
    ]
    result = run_tool(cmd, workspace_dir)
    findings = _parse_findings(result)
    criteria = _build_criteria(result, findings)
    return {"criteria": criteria, "raw": result, "findings": findings}


def _parse_findings(result: Dict) -> List[Dict]:
    findings = []
    if result.get("error") and "not found" in str(result.get("error", "")).lower():
        return findings
    for line in (result.get("stdout", "") + result.get("stderr", "")).splitlines():
        m = re.match(r"^(\d+):(\d+):\s+([EW]\d+)\s+(.+)$", line)
        if m:
            findings.append({
                "line": int(m.group(1)),
                "col": int(m.group(2)),
                "code": m.group(3),
                "message": m.group(4).strip(),
            })
    return findings


def _build_criteria(result: Dict, findings: List[Dict]) -> List[Dict]:
    criteria = []
    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    def _make(crit_id, name, prefixes, threshold, recommendation):
        if tool_missing:
            return make_criterion(
                crit_id, name, "NOT_EXECUTED",
                f"Pycodestyle not available: {result.get('error', 'timeout')}",
                TOOL, recommendation=recommendation,
            )
        matched = [f for f in findings if f["code"][:2] in prefixes or f["code"][:3] in prefixes]
        if not matched:
            status = "PASSED"
            detail = f"No {name} violations"
        elif len(matched) <= threshold:
            status = "WARNING"
            detail = f"{len(matched)} minor violation(s)"
        else:
            status = "FAILED"
            detail = f"{len(matched)} violation(s)"
        if matched:
            detail += ": " + "; ".join(
                f"Line {f['line']}: {f['code']} — {f['message']}"
                for f in matched[:5]
            )
        return make_criterion(
            crit_id, name, status, detail, TOOL,
            line=matched[0]["line"] if matched else 0,
            recommendation=recommendation,
        )

    criteria.append(_make(
        "PC-01", "Indentation Compliance (E1xx)",
        ["E1"],
        threshold=0,
        recommendation="Use 4 spaces per indentation level (PEP 8 E1xx)",
    ))
    criteria.append(_make(
        "PC-02", "Line Length ≤ 120 Characters (E501)",
        ["E5"],
        threshold=5,
        recommendation="Keep lines ≤ 120 characters; break long lines",
    ))
    criteria.append(_make(
        "PC-03", "Whitespace Compliance (E2xx)",
        ["E2"],
        threshold=3,
        recommendation="Fix spacing around operators, commas, and brackets",
    ))
    criteria.append(_make(
        "PC-04", "Blank Line Compliance (E3xx)",
        ["E3", "W3"],
        threshold=2,
        recommendation="Surround top-level definitions with 2 blank lines",
    ))
    criteria.append(_make(
        "PC-05", "Import / Statement Compliance (E4xx/W6xx)",
        ["E4", "W6"],
        threshold=1,
        recommendation="Place imports at top of file; one import per line",
    ))

    return criteria
