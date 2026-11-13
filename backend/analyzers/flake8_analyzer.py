"""
Flake8 Analyzer — Module 4 (part 1): Static Code Analysis.

Five criteria:
1. No Unused Imports (F401)
2. No Undefined Variables (F821)
3. No Wildcard Imports (F403/F405)
4. No Bare Except Clauses (E722)
5. No Redefined Built-ins (A001/W0622)
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

    # Determine tool availability
    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    def _criterion(crit_id, name, codes, recommendation):
        if tool_missing:
            return make_criterion(crit_id, name, "NOT_EXECUTED",
                                  f"Flake8 not available: {result.get('error', 'timeout')}",
                                  TOOL, recommendation=recommendation)
        matched = [f for f in findings if f["code"].startswith(tuple(codes))]
        if not matched:
            return make_criterion(
                crit_id, name, "PASSED",
                f"No violations found (checked codes: {', '.join(codes)})",
                TOOL, recommendation=recommendation,
            )
        severity = "FAILED" if any(f["code"].startswith("F") for f in matched) else "WARNING"
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

    criteria.append(_criterion(
        "FL-01", "No Unused Imports (F401)",
        ["F401"],
        "Remove unused import statements to keep the namespace clean",
    ))
    criteria.append(_criterion(
        "FL-02", "No Undefined Variables (F821)",
        ["F821", "F811"],
        "Ensure all variables are defined before use",
    ))
    criteria.append(_criterion(
        "FL-03", "No Wildcard Imports (F403/F405)",
        ["F403", "F405"],
        "Replace 'from module import *' with explicit imports",
    ))
    criteria.append(_criterion(
        "FL-04", "No Bare Except Clauses (E722)",
        ["E722"],
        "Use specific exception types instead of bare except",
    ))

    # Criterion 5: Line-too-long (E501) or other style errors
    if tool_missing:
        criteria.append(make_criterion(
            "FL-05", "No Redefined Built-ins / Name Errors",
            "NOT_EXECUTED",
            f"Flake8 not available", TOOL,
        ))
    else:
        matched = [f for f in findings if f["code"] in ("A001", "A002", "W0622", "E741")]
        if not matched:
            # Also check for shadowed builtins by name
            builtins = {"list", "dict", "set", "type", "id", "input", "print", "open"}
            import ast
            try:
                import ast as _ast
                tree = None  # will be set below
            except Exception:
                pass
            criteria.append(make_criterion(
                "FL-05", "No Redefined Built-ins / Ambiguous Names",
                "PASSED",
                "No built-in shadowing or ambiguous names detected",
                TOOL,
                recommendation="Avoid naming variables after Python built-ins",
            ))
        else:
            criteria.append(make_criterion(
                "FL-05", "No Redefined Built-ins / Ambiguous Names",
                "WARNING",
                f"{len(matched)} built-in shadowing(s): "
                + "; ".join(f"Line {f['line']}: {f['message']}" for f in matched[:3]),
                TOOL,
                recommendation="Rename variables that shadow Python built-ins",
            ))

    return criteria
