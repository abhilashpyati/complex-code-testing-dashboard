"""
Pycodestyle Analyzer — Coding Standards Analysis (Group 5 of 25 Core Criteria).

Five criteria:
1. PC-01: Indentation and Formatting (E1xx)
2. PC-02: Line Length Compliance (E501)
3. PC-03: Whitespace Usage (E2xx)
4. PC-04: Blank Line Conventions (E3xx/W3xx)
5. PC-05: General PEP 8 Style Compliance (E4xx/W6xx/E7xx)
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
        matched = [f for f in findings if any(f["code"].startswith(p) for p in prefixes)]
        if not matched:
            status = "PASSED"
            detail = f"No {name} violations detected"
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

    # PC-01: Indentation and Formatting (E1xx)
    criteria.append(_make(
        "PC-01", "Indentation and Formatting (E1xx)",
        ["E1"],
        threshold=0,
        recommendation="Use 4 spaces per indentation level conforming to PEP 8 (E1xx)",
    ))

    # PC-02: Line Length Compliance (E501)
    criteria.append(_make(
        "PC-02", "Line Length Compliance (E501)",
        ["E501", "E502"],
        threshold=3,
        recommendation="Keep line lengths within 120 characters; wrap lines where necessary",
    ))

    # PC-03: Whitespace Usage (E2xx)
    criteria.append(_make(
        "PC-03", "Whitespace Usage (E2xx)",
        ["E2"],
        threshold=3,
        recommendation="Follow standard whitespace conventions around operators, commas, and colons",
    ))

    # PC-04: Blank Line Conventions (E3xx/W3xx)
    criteria.append(_make(
        "PC-04", "Blank Line Conventions (E3xx/W3xx)",
        ["E3", "W3"],
        threshold=2,
        recommendation="Use 2 blank lines between top-level functions/classes and 1 inside classes",
    ))

    # PC-05: General PEP 8 Style Compliance (E4xx/W6xx/E7xx)
    criteria.append(_make(
        "PC-05", "General PEP 8 Style Compliance (E4xx/W6xx/E7xx)",
        ["E4", "E7", "W6", "E9"],
        threshold=1,
        recommendation="Follow general PEP 8 style rules regarding imports, statements, and comparisons",
    ))

    return criteria
