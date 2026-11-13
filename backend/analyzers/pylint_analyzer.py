"""
Pylint Analyzer — Code Quality Analysis (Group 3 of 25 Core Criteria).

Five criteria:
1. PL-01: Naming Conventions (C0103/C0104)
2. PL-02: Unused Variables and Imports (W0612/W0611/W0613)
3. PL-03: Error Detection (E-prefixed/F-prefixed)
4. PL-04: Warning Detection and Code Quality (W-prefixed, C011x docstrings, R-prefixed)
5. PL-05: Overall Code Quality and Pylint Score (>= 7.0/10)
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
        "--disable=C0301",   # ignore line-too-long (pycodestyle covers it)
        "--score=yes",
    ]
    result = run_tool(cmd, workspace_dir)
    findings = _parse_findings(result)
    score = _extract_score(result, findings)
    criteria = _build_criteria(result, findings, score)
    return {"criteria": criteria, "raw": result, "findings": findings, "score": score}


def _parse_findings(result: Dict) -> List[Dict]:
    """Parse pylint JSON output."""
    findings = []
    stdout = result.get("stdout", "")
    if not stdout.strip():
        return findings

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


def _extract_score(result: Dict, findings: List[Dict]) -> float:
    """Extract pylint score from output or calculate standard score from findings."""
    combined = result.get("stdout", "") + result.get("stderr", "")
    m = re.search(r"Your code has been rated at\s+([\-\d\.]+)/10", combined)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # When JSON output format is used, calculate score based on findings severity
    if result.get("error") and "not found" in str(result.get("error", "")).lower():
        return -1.0
    if not findings:
        return 10.0

    deduction = 0.0
    for f in findings:
        t = f.get("type", "").lower()
        code = f.get("code", "")
        if t in ("fatal", "error") or code.startswith(("F", "E")):
            deduction += 2.0
        elif t == "warning" or code.startswith("W"):
            deduction += 0.5
        else:  # convention or refactor
            deduction += 0.2

    return max(0.0, round(10.0 - deduction, 2))


def _build_criteria(result: Dict, findings: List[Dict], score: float) -> List[Dict]:
    criteria = []
    tool_missing = (
        result.get("error") and "not found" in str(result.get("error", "")).lower()
    ) or result.get("timed_out")

    # Criterion 1: PL-01 Naming Conventions (C0103, C0104)
    if tool_missing:
        criteria.append(make_criterion(
            "PL-01", "Naming Conventions (C0103/C0104)", "NOT_EXECUTED",
            f"Pylint not available: {result.get('error', 'timeout')}", TOOL,
            recommendation="Follow PEP 8 naming: snake_case for functions/vars, PascalCase for classes",
        ))
    else:
        naming_findings = [f for f in findings if f["code"] in ("C0103", "C0104") or "naming" in f.get("symbol", "").lower()]
        if not naming_findings:
            criteria.append(make_criterion(
                "PL-01", "Naming Conventions (C0103/C0104)", "PASSED",
                "All names conform to standard Python naming conventions", TOOL,
                recommendation="Follow PEP 8 naming conventions consistently",
            ))
        else:
            criteria.append(make_criterion(
                "PL-01", "Naming Conventions (C0103/C0104)", "WARNING",
                f"{len(naming_findings)} naming convention violation(s): " + "; ".join(
                    f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                    for f in naming_findings[:4]
                ), TOOL,
                line=naming_findings[0]["line"] if naming_findings else 0,
                recommendation="Use snake_case for functions and variables, PascalCase for classes",
            ))

    # Criterion 2: PL-02 Unused Variables and Imports (W0612, W0611, W0613)
    if tool_missing:
        criteria.append(make_criterion(
            "PL-02", "Unused Variables and Imports (W0612/W0611/W0613)", "NOT_EXECUTED",
            "Pylint not available", TOOL,
            recommendation="Remove unused variables, parameters, and imports",
        ))
    else:
        unused_findings = [f for f in findings if f["code"] in ("W0611", "W0612", "W0613") or "unused" in f.get("symbol", "").lower()]
        if not unused_findings:
            criteria.append(make_criterion(
                "PL-02", "Unused Variables and Imports (W0612/W0611/W0613)", "PASSED",
                "No unused variables, arguments, or import statements detected", TOOL,
                recommendation="Keep code clean of unused symbols",
            ))
        else:
            criteria.append(make_criterion(
                "PL-02", "Unused Variables and Imports (W0612/W0611/W0613)", "WARNING",
                f"{len(unused_findings)} unused variable/import violation(s): " + "; ".join(
                    f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                    for f in unused_findings[:4]
                ), TOOL,
                line=unused_findings[0]["line"] if unused_findings else 0,
                recommendation="Remove variables and imports that are assigned or imported but never used",
            ))

    # Criterion 3: PL-03 Error Detection (E-prefixed errors, F-prefixed fatal errors)
    if tool_missing:
        criteria.append(make_criterion(
            "PL-03", "Error Detection (E-prefixed/Fatal F-prefixed)", "NOT_EXECUTED",
            "Pylint not available", TOOL,
            recommendation="Fix all syntax, import, and semantic errors",
        ))
    else:
        error_findings = [f for f in findings if f["code"].startswith(("E", "F")) or f.get("type", "").lower() in ("error", "fatal")]
        if not error_findings:
            criteria.append(make_criterion(
                "PL-03", "Error Detection (E-prefixed/Fatal F-prefixed)", "PASSED",
                "No Pylint syntax or semantic errors detected", TOOL,
                recommendation="Continue maintaining error-free code execution",
            ))
        else:
            criteria.append(make_criterion(
                "PL-03", "Error Detection (E-prefixed/Fatal F-prefixed)", "FAILED",
                f"{len(error_findings)} error(s) detected: " + "; ".join(
                    f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                    for f in error_findings[:4]
                ), TOOL,
                line=error_findings[0]["line"] if error_findings else 0,
                recommendation="Resolve all runtime and semantic errors flagged by Pylint",
            ))

    # Criterion 4: PL-04 Warning Detection and Code Quality (W-prefixed, C011x docstrings, R-prefixed)
    if tool_missing:
        criteria.append(make_criterion(
            "PL-04", "Warning Detection and Code Quality", "NOT_EXECUTED",
            "Pylint not available", TOOL,
            recommendation="Address warnings, docstring gaps, and design code smells",
        ))
    else:
        # Exclude naming (PL-01) and unused (PL-02) and errors (PL-03)
        excluded_codes = {"C0103", "C0104", "W0611", "W0612", "W0613"}
        quality_findings = [
            f for f in findings
            if f["code"] not in excluded_codes and not f["code"].startswith(("E", "F"))
        ]
        if not quality_findings:
            criteria.append(make_criterion(
                "PL-04", "Warning Detection and Code Quality", "PASSED",
                "No code quality warnings, missing docstrings, or design issues detected", TOOL,
                recommendation="Maintain high documentation and design standards",
            ))
        elif len(quality_findings) <= 2:
            criteria.append(make_criterion(
                "PL-04", "Warning Detection and Code Quality", "WARNING",
                f"{len(quality_findings)} minor warning(s): " + "; ".join(
                    f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                    for f in quality_findings[:3]
                ), TOOL,
                line=quality_findings[0]["line"] if quality_findings else 0,
                recommendation="Document functions and classes, and simplify complex designs",
            ))
        else:
            criteria.append(make_criterion(
                "PL-04", "Warning Detection and Code Quality", "FAILED",
                f"{len(quality_findings)} warning(s) and quality issue(s): " + "; ".join(
                    f"Line {f['line']}: {f['symbol'] or f['code']} — {f['message']}"
                    for f in quality_findings[:4]
                ), TOOL,
                line=quality_findings[0]["line"] if quality_findings else 0,
                recommendation="Add missing docstrings and refactor problematic methods",
            ))

    # Criterion 5: PL-05 Overall Code Quality and Pylint Score (>= 7.0/10)
    if tool_missing:
        criteria.append(make_criterion(
            "PL-05", "Overall Code Quality and Pylint Score (≥ 7.0/10)", "NOT_EXECUTED",
            "Pylint score not available", TOOL,
            recommendation="Ensure Pylint runs successfully",
        ))
    elif score < 0:
        criteria.append(make_criterion(
            "PL-05", "Overall Code Quality and Pylint Score (≥ 7.0/10)", "NOT_APPLICABLE",
            "Score could not be extracted from Pylint output", TOOL,
            recommendation="Review Pylint raw output for details",
        ))
    elif score >= 7.0:
        criteria.append(make_criterion(
            "PL-05", "Overall Code Quality and Pylint Score (≥ 7.0/10)", "PASSED",
            f"Pylint score {score:.2f} / 10.0 meets threshold (≥ 7.0)", TOOL,
            recommendation="Maintain score above 7.0 / 10",
        ))
    elif score >= 5.0:
        criteria.append(make_criterion(
            "PL-05", "Overall Code Quality and Pylint Score (≥ 7.0/10)", "WARNING",
            f"Pylint score {score:.2f} / 10.0 is below recommended threshold of 7.0", TOOL,
            recommendation="Address top Pylint warnings to raise score above 7.0",
        ))
    else:
        criteria.append(make_criterion(
            "PL-05", "Overall Code Quality and Pylint Score (≥ 7.0/10)", "FAILED",
            f"Pylint score {score:.2f} / 10.0 is critically low (< 5.0)", TOOL,
            recommendation="Refactor code thoroughly to address widespread code quality violations",
        ))

    return criteria
