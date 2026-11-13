"""
Flake8 Analyzer — Static Code Analysis (Group 2 of 25 Core Criteria).

Five criteria:
1. FL-01: Unused Imports (F401)
2. FL-02: Undefined Names (F821)
3. FL-03: Syntax and Parsing Issues (E999, E901, E902)
4. FL-04: Wildcard Import Usage (F403, F405)
5. FL-05: General Linting and Code Quality Issues (E722, E741, F811, F841, etc.)
"""
import os
import re
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Flake8"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run flake8 and return five criteria."""
    python = get_python_executable()
    cmd = [
        python, "-m", "flake8",
        code_path,
        "--format=%(row)d:%(col)d:%(code)s:%(text)s",
        "--max-line-length=120",
        "--statistics",
    ]
    result = run_tool(cmd, workspace_dir)
    findings = _parse_findings(result)
    criteria = _build_criteria(result, findings)
    return {"criteria": criteria, "raw": result, "findings": findings}


def _parse_findings(result: Dict) -> List[Dict]:
    """Parse flake8 output into structured findings."""
    findings = []
    if result.get("error") and "not found" in str(result.get("error", "")).lower():
        return findings

    for line in (result.get("stdout", "") + result.get("stderr", "")).splitlines():
        # Try format: file:row:col:code:message
        m = re.match(r"^(.+?):(\d+):(\d+):\s*([A-Z]\d+)\s*(.+)$", line)
        if m:
            findings.append({
                "file": os.path.basename(m.group(1)),
                "line": int(m.group(2)),
                "col": int(m.group(3)),
                "code": m.group(4),
                "message": m.group(5).strip(),
            })
        else:
            # Try alternate format: row:col:code:message
            m2 = re.match(r"^(\d+):(\d+):([A-Z]\d+):(.+)$", line)
            if m2:
                findings.append({
                    "file": "user_code.py",
                    "line": int(m2.group(1)),
                    "col": int(m2.group(2)),
                    "code": m2.group(3),
                    "message": m2.group(4).strip(),
                })
    return findings


def _build_criteria(result: Dict, findings: List[Dict]) -> List[Dict]:
    criteria = []

    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    def _criterion(crit_id, name, codes, recommendation, default_severity="WARNING"):
        if tool_missing:
            return make_criterion(crit_id, name, "NOT_EXECUTED",
                                  f"Flake8 not available: {result.get('error', 'timeout')}",
                                  TOOL, recommendation=recommendation)
        matched = [f for f in findings if f["code"] in codes or any(f["code"].startswith(c) for c in codes)]
        if not matched:
            return make_criterion(
                crit_id, name, "PASSED",
                f"No violations detected ({', '.join(codes)})",
                TOOL, recommendation=recommendation,
            )
        severity = "FAILED" if any(f["code"].startswith(("E9", "F821", "F822", "F823")) for f in matched) or default_severity == "FAILED" else "WARNING"
        details = "; ".join(
            f"Line {f['line']}: {f['code']} — {f['message']}"
            for f in matched[:5]
        )
        return make_criterion(
            crit_id, name, severity,
            f"{len(matched)} violation(s): {details}",
            TOOL,
            line=matched[0]["line"] if matched else 0,
            recommendation=recommendation,
        )

    # Criterion 1: FL-01 - Unused Imports
    criteria.append(_criterion(
        "FL-01", "Unused Imports (F401)",
        ["F401"],
        "Remove unused import statements to keep the namespace clean",
        default_severity="WARNING",
    ))

    # Criterion 2: FL-02 - Undefined Names
    criteria.append(_criterion(
        "FL-02", "Undefined Names (F821)",
        ["F821", "F822", "F823"],
        "Ensure all variables and names are defined before use",
        default_severity="FAILED",
    ))

    # Criterion 3: FL-03 - Syntax and Parsing Issues
    criteria.append(_criterion(
        "FL-03", "Syntax and Parsing Issues (E999/E901/E902)",
        ["E999", "E901", "E902"],
        "Correct Python syntax errors to ensure valid compilation",
        default_severity="FAILED",
    ))

    # Criterion 4: FL-04 - Wildcard Import Usage
    criteria.append(_criterion(
        "FL-04", "Wildcard Import Usage (F403/F405)",
        ["F403", "F405"],
        "Replace 'from module import *' with explicit imports to prevent namespace pollution",
        default_severity="WARNING",
    ))

    # Criterion 5: FL-05 - General Linting and Code Quality Issues
    if tool_missing:
        criteria.append(make_criterion(
            "FL-05", "General Linting and Code Quality Issues",
            "NOT_EXECUTED",
            "Flake8 not available", TOOL,
        ))
    else:
        # Match other flake8 issues like bare except (E722), ambiguous name (E741), redefinition (F811), unused var (F841)
        excluded_codes = {"F401", "F821", "F822", "F823", "E999", "E901", "E902", "F403", "F405"}
        matched = [f for f in findings if f["code"] not in excluded_codes]
        if not matched:
            criteria.append(make_criterion(
                "FL-05", "General Linting and Code Quality Issues",
                "PASSED",
                "No general linting issues or code quality anomalies detected",
                TOOL,
                recommendation="Maintain clean coding standards",
            ))
        else:
            has_fatal = any(f["code"].startswith(("F", "E9")) for f in matched)
            severity = "FAILED" if has_fatal else "WARNING"
            criteria.append(make_criterion(
                "FL-05", "General Linting and Code Quality Issues",
                severity,
                f"{len(matched)} general linting issue(s): "
                + "; ".join(f"Line {f['line']}: {f['code']} — {f['message']}" for f in matched[:4]),
                TOOL,
                line=matched[0]["line"] if matched else 0,
                recommendation="Address general linting issues such as bare except clauses, unused variables, and ambiguous symbols",
            ))

    return criteria
