"""
Coverage Analyzer — Module 3: Code Coverage Analysis.
Uses Coverage.py to measure statement and branch coverage.

Workflow:
1. Executes PyTest under Coverage.py with branch tracking (--branch).
2. Measures ONLY the submitted source file, excluding test harnesses and third-party files.
3. Distinguishes test failures from coverage collection failures.
4. Identifies files without branches and reports branch coverage as NOT_APPLICABLE.
5. Does not fabricate zero coverage when coverage is unavailable.

Five criteria:
1. Statement Coverage ≥ 80% (CV-01)
2. Branch Coverage ≥ 60% (CV-02)
3. No Uncovered Executable Statements (CV-03)
4. No Uncovered Branches (CV-04)
5. Coverage Report Generation Success (CV-05)
"""
import os
import re
import json
from typing import Dict, List, Optional

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Coverage.py"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run Coverage.py and return criteria and accurate metrics."""
    python = get_python_executable()
    target_filename = os.path.basename(code_path)
    coverage_data_file = os.path.join(workspace_dir, ".coverage")
    json_report_path = os.path.join(workspace_dir, "coverage.json")
    test_path = os.path.join(workspace_dir, "test_user_code.py")

    # If code is empty or has only whitespace
    if not code.strip():
        criteria = [
            make_criterion(f"CV-{i:02d}", name, "NOT_APPLICABLE",
                           "Submitted source code is empty; no executable statements", TOOL)
            for i, name in enumerate(_criterion_names(), 1)
        ]
        return {
            "criteria": criteria,
            "raw": {},
            "metrics": {
                "statement_coverage": None,
                "branch_coverage": None,
                "executed_lines": [],
                "missing_lines": [],
                "missing_branches": [],
                "coverage_status": "NOT_APPLICABLE",
                "notes": "Empty source code",
            },
        }

    # Step 1: Execute test suite under Coverage.py
    # Note: We do NOT fallback to direct module import if tests fail;
    # Coverage data is collected for executed statements even when tests fail.
    run_result = None
    if os.path.exists(test_path):
        run_result = run_tool(
            [
                python, "-m", "coverage", "run",
                f"--data-file={coverage_data_file}",
                "--branch",
                f"--source={workspace_dir}",
                "-m", "pytest",
                test_path,
                "-q",
                "--no-header",
            ],
            workspace_dir,
            timeout=25,
        )
    else:
        # If test suite wasn't generated (e.g. script-only code without functions)
        runner_path = os.path.join(workspace_dir, "run_coverage.py")
        module_name = os.path.splitext(target_filename)[0]
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(
                "import sys, os, importlib\n"
                "sys.path.insert(0, os.path.dirname(__file__))\n"
                f"try:\n    importlib.import_module('{module_name}')\nexcept Exception:\n    pass\n"
            )
        run_result = run_tool(
            [
                python, "-m", "coverage", "run",
                f"--data-file={coverage_data_file}",
                "--branch",
                f"--source={workspace_dir}",
                runner_path,
            ],
            workspace_dir,
            timeout=25,
        )

    # Step 2: Generate JSON report with separate -o and path
    report_result = run_tool(
        [
            python, "-m", "coverage", "json",
            f"--data-file={coverage_data_file}",
            "-o", json_report_path,
        ],
        workspace_dir,
        timeout=15,
    )

    # Parse JSON report
    cov_data: Dict = {}
    if os.path.exists(json_report_path):
        try:
            with open(json_report_path, "r", encoding="utf-8") as f:
                cov_data = json.load(f)
        except Exception:
            pass

    return _build_criteria(run_result, report_result, cov_data, workspace_dir, code, code_path)


def _build_criteria(
    run_result: Dict,
    report_result: Dict,
    cov_data: Dict,
    workspace_dir: str,
    code: str,
    code_path: str,
) -> Dict:
    tool_timed_out = run_result.get("timed_out", False)
    tool_missing = bool(run_result.get("error") and "not found" in str(run_result.get("error")).lower())

    if tool_timed_out or tool_missing:
        reason = "timeout after 25s" if tool_timed_out else str(run_result.get("error"))
        criteria = []
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"CV-{i:02d}", name, "NOT_EXECUTED",
                f"Coverage.py unavailable: {reason}", TOOL,
            ))
        return {
            "criteria": criteria,
            "raw": run_result,
            "metrics": {
                "statement_coverage": None,
                "branch_coverage": None,
                "executed_lines": [],
                "missing_lines": [],
                "missing_branches": [],
                "coverage_status": "NOT_EXECUTED",
                "notes": f"Tool unavailable: {reason}",
            },
        }

    report_generated = bool(cov_data)
    target_filename = os.path.basename(code_path)

    # Extract target file data specifically
    target_file_data = None
    if cov_data:
        for fname, fdata in cov_data.get("files", {}).items():
            base = os.path.basename(fname)
            if base == target_filename or base == "user_code.py" or target_filename in fname:
                target_file_data = fdata
                break

    # If coverage could not be parsed or generated
    if not report_generated or target_file_data is None:
        c1_status = "NOT_EXECUTED"
        c1_detail = "Coverage data could not be collected for the submitted file"
        c2_status = "NOT_EXECUTED"
        c2_detail = "Branch coverage data unavailable"
        c3_status = "NOT_EXECUTED"
        c3_detail = "Statement execution tracking unavailable"
        c4_status = "NOT_EXECUTED"
        c4_detail = "Branch execution tracking unavailable"
        c5_status = "FAILED"
        c5_detail = f"Coverage JSON report generation failed: {report_result.get('error') or report_result.get('stderr')}"

        criteria = [
            make_criterion("CV-01", "Statement Coverage ≥ 80%", c1_status, c1_detail, TOOL),
            make_criterion("CV-02", "Branch Coverage ≥ 60%", c2_status, c2_detail, TOOL),
            make_criterion("CV-03", "No Uncovered Executable Statements", c3_status, c3_detail, TOOL),
            make_criterion("CV-04", "No Uncovered Branches", c4_status, c4_detail, TOOL),
            make_criterion("CV-05", "Coverage Report Generation", c5_status, c5_detail, TOOL),
        ]
        return {
            "criteria": criteria,
            "raw": run_result,
            "metrics": {
                "statement_coverage": None,
                "branch_coverage": None,
                "executed_lines": [],
                "missing_lines": [],
                "missing_branches": [],
                "coverage_status": "FAILED",
                "notes": "Coverage report generation failed",
            },
        }

    summary = target_file_data.get("summary", {})
    stmt_cov = summary.get("percent_statements_covered", summary.get("percent_covered", 0.0))
    num_branches = summary.get("num_branches", 0)
    covered_branches = summary.get("covered_branches", 0)
    has_branches = num_branches > 0

    branch_cov: Optional[float] = None
    if has_branches:
        branch_cov = round(covered_branches / num_branches * 100, 1)

    executed_lines = target_file_data.get("executed_lines", [])
    missing_lines = target_file_data.get("missing_lines", [])
    missing_branches = target_file_data.get("missing_branches", [])

    # Criterion 1: Statement Coverage ≥ 80%
    if stmt_cov >= 80:
        c1_status = "PASSED"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (≥ 80% threshold, {len(executed_lines)}/{summary.get('num_statements', len(executed_lines))} statements)"
    elif stmt_cov >= 50:
        c1_status = "WARNING"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (below 80% threshold)"
    else:
        c1_status = "FAILED"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (critically low)"

    # Criterion 2: Branch Coverage ≥ 60%
    if not has_branches:
        c2_status = "NOT_APPLICABLE"
        c2_detail = "No conditional branches in submitted source code (sequential execution only)"
    elif branch_cov >= 60:
        c2_status = "PASSED"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (≥ 60% threshold, {covered_branches}/{num_branches} branches taken)"
    elif branch_cov >= 30:
        c2_status = "WARNING"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (below 60% threshold)"
    else:
        c2_status = "FAILED"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (critically low)"

    # Criterion 3: Uncovered Executable Statements
    if not missing_lines:
        c3_status = "PASSED"
        c3_detail = f"All {len(executed_lines)} executable statements were reached"
    elif len(missing_lines) <= 5:
        c3_status = "WARNING"
        c3_detail = f"Uncovered statements on lines: {missing_lines}"
    else:
        c3_status = "FAILED"
        c3_detail = f"{len(missing_lines)} statements uncovered: lines {missing_lines[:8]}..."

    # Criterion 4: Uncovered Branches
    if not has_branches:
        c4_status = "NOT_APPLICABLE"
        c4_detail = "No branch opportunities present in submitted code"
    elif not missing_branches:
        c4_status = "PASSED"
        c4_detail = f"All {num_branches} branch paths were successfully exercised"
    elif len(missing_branches) <= 3:
        c4_status = "WARNING"
        c4_detail = f"{len(missing_branches)} unreached branch path(s)"
    else:
        c4_status = "FAILED"
        c4_detail = f"{len(missing_branches)} unreached branch path(s) detected: {missing_branches[:5]}"

    # Criterion 5: Coverage Report Generation
    c5_status = "PASSED"
    c5_detail = "Coverage JSON report successfully generated and validated"

    criteria = [
        make_criterion("CV-01", "Statement Coverage ≥ 80%", c1_status, c1_detail, TOOL,
                       recommendation="Add tests that exercise unreached statements"),
        make_criterion("CV-02", "Branch Coverage ≥ 60%", c2_status, c2_detail, TOOL,
                       recommendation="Add tests for both True and False branches of conditional statements"),
        make_criterion("CV-03", "No Uncovered Executable Statements", c3_status, c3_detail, TOOL,
                       recommendation="Exercise remaining uncovered code paths"),
        make_criterion("CV-04", "No Uncovered Branches", c4_status, c4_detail, TOOL,
                       recommendation="Exercise alternate conditional branches"),
        make_criterion("CV-05", "Coverage Report Generation", c5_status, c5_detail, TOOL,
                       recommendation="Coverage measurement completed successfully"),
    ]

    metrics = {
        "statement_coverage": round(stmt_cov, 1),
        "branch_coverage": round(branch_cov, 1) if branch_cov is not None else None,
        "executed_lines": executed_lines,
        "missing_lines": missing_lines,
        "missing_branches": missing_branches,
        "has_branches": has_branches,
        "coverage_status": "COMPLETED",
    }

    return {"criteria": criteria, "raw": run_result, "metrics": metrics}


def _criterion_names():
    return [
        "Statement Coverage ≥ 80%",
        "Branch Coverage ≥ 60%",
        "No Uncovered Executable Statements",
        "No Uncovered Branches",
        "Coverage Report Generation",
    ]
