"""
Pylint Analyzer — Module 4 (part 2): Static Code Analysis complement.

Provides five criteria focusing on maintainability and code quality:
1. No Unused Variables (W0612)
2. No Missing Docstrings (C0111/C0114/C0115/C0116)
3. Maintainability Index Acceptable (R-prefixed messages)
4. No Naming Convention Violations (C01xx)
5. No Code Smell / Design Issues (R-prefixed / W-prefixed)
"""
import os
import re
import json
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Pylint"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run pylint and return five criteria."""
    python = get_python_executable()
    cmd = [
        python, "-m", "pylint",
        code_path,
        "--output-format=json",
        "--disable=C0301,W0611",   # ignore line-too-long and import errors (flake8 covers those)
        "--score=yes",
    ]
    result = run_tool(cmd, workspace_dir)
    findings = _parse_findings(result)
    score = _extract_score(result)
    criteria = _build_criteria(result, findings, score)
    return {"criteria": criteria, "raw": result, "findings": findings, "score": score}


def _parse_findings(result: Dict) -> List[Dict]:
    """Parse pylint JSON output."""
    findings = []
    stdout = result.get("stdout", "")
    if not stdout.strip():
        return findings
    # pylint may output non-JSON before/after JSON block
    try:
        # Find JSON array in output
        start = stdout.find("[")
        end = stdout.rfind("]") + 1
        if start != -1 and end > start:
            data = json.loads(stdout[start:end])
            for item in data:
                findings.append({
                    "file": os.path.basename(item.get("path", "user_code.py")),
                    "line": item.get("line", 0),
                    "col": item.get("column", 0),
                    "code": item.get("message-id", ""),
                    "symbol": item.get("symbol", ""),
                    "message": item.get("message", ""),
                    "type": item.get("type", ""),
                })
    except (json.JSONDecodeError, ValueError):
        # Fallback: parse plain text
        for line in stdout.splitlines():
            m = re.match(r"^.+?:(\d+):\d+:\s+([CWRIFE]\d+):\s+(.+)$", line)
            if m:
                findings.append({
                    "file": "user_code.py",
                    "line": int(m.group(1)),
                    "col": 0,
                    "code": m.group(2),
                    "symbol": "",
                    "message": m.group(3),
                    "type": m.group(2)[0],
                })
    return findings


def _extract_score(result: Dict) -> float:
    """Extract pylint score from output."""
    combined = result.get("stdout", "") + result.get("stderr", "")
    m = re.search(r"Your code has been rated at\s+([\-\d\.]+)/10", combined)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return -1.0


def _build_criteria(result: Dict, findings: List[Dict], score: float) -> List[Dict]:
    criteria = []
    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    def _make(crit_id, name, codes, threshold, recommendation):
        if tool_missing:
            return make_criterion(
                crit_id, name, "NOT_EXECUTED",
                f"Pylint not available: {result.get('error', 'timeout')}",
                TOOL, recommendation=recommendation,
            )
        matched = [f for f in findings if f["code"].startswith(tuple(codes))]
        if not matched:
            status = "PASSED"
            detail = f"No {name} issues found"
        elif len(matched) <= threshold:
            status = "WARNING"
            detail = f"{len(matched)} minor issue(s) found"
        else:
            status = "FAILED"
            detail = f"{len(matched)} issue(s) found"
        if matched:
            detail += ": " + "; ".join(
                f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                for f in matched[:4]
            )
        return make_criterion(
            crit_id, name, status, detail, TOOL,
            line=matched[0]["line"] if matched else 0,
            recommendation=recommendation,
        )

    # Criterion 1
    criteria.append(_make(
        "PL-01", "No Unused Variables",
        ["W0612", "W0613"],
        threshold=0,
        recommendation="Remove variables that are assigned but never used",
    ))

    # Criterion 2
    criteria.append(_make(
        "PL-02", "Missing Docstrings",
        ["C0114", "C0115", "C0116", "C0111"],
        threshold=2,
        recommendation="Add docstrings to all public modules, classes, and functions",
    ))

    # Criterion 3: Refactoring / Design
    criteria.append(_make(
        "PL-03", "Refactoring / Design Issues",
        ["R", "W0101", "W0107"],
        threshold=3,
        recommendation="Simplify complex code paths and reduce code duplication",
    ))

    # Criterion 4: Naming conventions
    criteria.append(_make(
        "PL-04", "Naming Convention Violations",
        ["C0103", "C0104"],
        threshold=1,
        recommendation="Follow PEP 8 naming: lowercase_with_underscores for functions/variables",
    ))

    # Criterion 5: Pylint score ≥ 7.0
    if tool_missing:
        criteria.append(make_criterion(
            "PL-05", "Pylint Score ≥ 7.0 / 10",
            "NOT_EXECUTED",
            "Pylint not available",
            TOOL,
        ))
    elif score < 0:
        criteria.append(make_criterion(
            "PL-05", "Pylint Score ≥ 7.0 / 10",
            "WARNING",
            "Score could not be parsed from output",
            TOOL,
        ))
    elif score >= 7.0:
        criteria.append(make_criterion(
            "PL-05", "Pylint Score ≥ 7.0 / 10",
            "PASSED",
            f"Pylint score: {score:.2f}/10 (≥ 7.0 threshold)",
            TOOL,
            recommendation="Maintain a Pylint score above 7.0",
        ))
    elif score >= 5.0:
        criteria.append(make_criterion(
            "PL-05", "Pylint Score ≥ 7.0 / 10",
            "WARNING",
            f"Pylint score: {score:.2f}/10 (below 7.0 threshold)",
            TOOL,
            recommendation="Address Pylint warnings to improve score",
        ))
    else:
        criteria.append(make_criterion(
            "PL-05", "Pylint Score ≥ 7.0 / 10",
            "FAILED",
            f"Pylint score: {score:.2f}/10 (critically low)",
            TOOL,
            recommendation="Significant refactoring required to improve code quality",
        ))

    return criteria
