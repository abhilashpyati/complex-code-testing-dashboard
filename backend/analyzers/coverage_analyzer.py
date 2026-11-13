"""
Coverage Analyzer — Module 3: Code Coverage Analysis.
Uses Coverage.py to measure statement and branch coverage.

Five criteria:
1. Statement Coverage ≥ 80%
2. Branch Coverage ≥ 60%
3. No Uncovered Executable Statements
4. No Uncovered Branches
5. Coverage Report Generation Success
"""
import os
import re
import json
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "Coverage.py"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run Coverage.py and return five criteria."""
    python = get_python_executable()
    module_name = os.path.splitext(os.path.basename(code_path))[0]
    coverage_data_file = os.path.join(workspace_dir, ".coverage")
    json_report_path = os.path.join(workspace_dir, "coverage.json")
    test_path = os.path.join(workspace_dir, "test_user_code.py")

    # Step 1: Run coverage
    # If pytest test file exists in the workspace, run coverage against the tests
    run_result = None
    if os.path.exists(test_path):
        run_result = run_tool(
            [
                python, "-m", "coverage", "run",
                f"--data-file={coverage_data_file}",
                "--branch",
                "-m", "pytest",
                test_path,
                "-q",
                "--no-header",
            ],
            workspace_dir,
            timeout=25,
        )

    # If test file doesn't exist or run failed, fallback to direct module import runner
    if not run_result or run_result.get("returncode") != 0 or not os.path.exists(coverage_data_file):
        runner_path = os.path.join(workspace_dir, "run_coverage.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(
                "import sys, os, importlib\n"
                "sys.path.insert(0, os.path.dirname(__file__))\n"
                f"for mod in ('user_code', '{module_name}'):\n"
                "    try:\n"
                "        importlib.import_module(mod)\n"
                "    except Exception:\n"
                "        pass\n"
            )
        run_result = run_tool(
            [
                python, "-m", "coverage", "run",
                f"--data-file={coverage_data_file}",
                "--branch",
                runner_path,
            ],
            workspace_dir,
            timeout=25,
        )

    # Step 2: Generate JSON report with separate -o and path argument
    report_result = run_tool(
        [
            python, "-m", "coverage", "json",
            f"--data-file={coverage_data_file}",
            "-o", json_report_path,
        ],
        workspace_dir,
    )

    # Parse coverage JSON data
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
    tool_available = not (
        (run_result.get("error") and "not found" in str(run_result["error"]).lower())
        or run_result.get("timed_out")
    )

    if not tool_available:
        criteria = []
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"CV-{i:02d}", name, "NOT_EXECUTED",
                f"Coverage.py not available: {run_result.get('error', 'timeout')}",
                TOOL,
            ))
        return {"criteria": criteria, "raw": {}, "metrics": {}}

    # Extract metrics from JSON report
    stmt_cov = 0.0
    branch_cov = 0.0
    missing_lines: List[int] = []
    executed_lines: List[int] = []
    missing_branches: List = []
    report_generated = bool(cov_data)

    if cov_data:
        target_filename = os.path.basename(code_path)
        target_file_data = None

        # Find the specific submitted source file in coverage report
        for fname, fdata in cov_data.get("files", {}).items():
            base = os.path.basename(fname)
            if base == target_filename or base == "user_code.py" or target_filename in fname:
                target_file_data = fdata
                break

        if target_file_data:
            summary = target_file_data.get("summary", {})
            stmt_cov = summary.get("percent_statements_covered", summary.get("percent_covered", 0.0))
            num_branches = summary.get("num_branches", 0)
            covered_branches = summary.get("covered_branches", 0)
            if num_branches > 0:
                branch_cov = round(covered_branches / num_branches * 100, 1)
            else:
                # If there are no conditional branches in the code, branch coverage is 100%
                branch_cov = 100.0

            missing_lines = target_file_data.get("missing_lines", [])
            executed_lines = target_file_data.get("executed_lines", [])
            missing_branches = target_file_data.get("missing_branches", [])
        else:
            totals = cov_data.get("totals", {})
            stmt_cov = totals.get("percent_statements_covered", totals.get("percent_covered", 0.0))
            num_branches = totals.get("num_branches", 0)
            covered_branches = totals.get("covered_branches", 0)
            if num_branches > 0:
                branch_cov = round(covered_branches / num_branches * 100, 1)
            else:
                branch_cov = 100.0

    # Fallback: try parsing text report
    if not cov_data and not run_result.get("error"):
        stmt_cov, branch_cov = _parse_text_report(run_result.get("stdout", ""))

    # Criterion 1: Statement Coverage ≥ 80%
    if stmt_cov >= 80:
        c1_status = "PASSED"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (≥ 80% threshold)"
    elif stmt_cov >= 50:
        c1_status = "WARNING"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (below 80% threshold)"
    else:
        c1_status = "FAILED"
        c1_detail = f"Statement coverage: {stmt_cov:.1f}% (critically low)"

    # Criterion 2: Branch Coverage ≥ 60%
    if branch_cov >= 60:
        c2_status = "PASSED"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (≥ 60% threshold)"
    elif branch_cov >= 30:
        c2_status = "WARNING"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (below 60% threshold)"
    else:
        c2_status = "FAILED"
        c2_detail = f"Branch coverage: {branch_cov:.1f}% (critically low)"

    # Criterion 3: Uncovered lines
    if not missing_lines:
        c3_status = "PASSED"
        c3_detail = "All executable statements were reached"
    elif len(missing_lines) <= 5:
        c3_status = "WARNING"
        c3_detail = f"Uncovered lines: {missing_lines}"
    else:
        c3_status = "FAILED"
        c3_detail = f"{len(missing_lines)} lines uncovered: {missing_lines[:10]}..."

    # Criterion 4: Uncovered branches
    if not missing_branches:
        c4_status = "PASSED"
        c4_detail = "All branches were executed"
    elif len(missing_branches) <= 3:
        c4_status = "WARNING"
        c4_detail = f"Uncovered branches: {len(missing_branches)} branch(es)"
    else:
        c4_status = "FAILED"
        c4_detail = f"{len(missing_branches)} uncovered branch(es) detected"

    # Criterion 5: Report generation
    if report_generated:
        c5_status = "PASSED"
        c5_detail = "Coverage JSON report successfully generated"
    elif not run_result.get("error"):
        c5_status = "WARNING"
        c5_detail = "Coverage ran but JSON report generation failed"
    else:
        c5_status = "FAILED"
        c5_detail = f"Coverage report generation failed: {run_result.get('error')}"

    criteria = [
        make_criterion("CV-01", "Statement Coverage ≥ 80%", c1_status, c1_detail, TOOL,
                       recommendation="Add tests that call each function with valid inputs"),
        make_criterion("CV-02", "Branch Coverage ≥ 60%", c2_status, c2_detail, TOOL,
                       recommendation="Add tests for each conditional branch (if/else/try/except)"),
        make_criterion("CV-03", "No Uncovered Executable Statements", c3_status, c3_detail, TOOL,
                       recommendation="Ensure every code path is exercised in tests"),
        make_criterion("CV-04", "No Uncovered Branches", c4_status, c4_detail, TOOL,
                       recommendation="Test both True and False paths of all conditionals"),
        make_criterion("CV-05", "Coverage Report Generation", c5_status, c5_detail, TOOL,
                       recommendation="Ensure coverage.py is correctly installed"),
    ]

    metrics = {
        "statement_coverage": round(stmt_cov, 1),
        "branch_coverage": round(branch_cov, 1),
        "executed_lines": executed_lines,
        "missing_lines": missing_lines,
        "missing_branches": missing_branches,
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


def _parse_text_report(stdout: str):
    """Fallback: parse 'TOTAL  x  y  z%' line from coverage report text."""
    stmt_cov = 0.0
    branch_cov = 0.0
    for line in stdout.splitlines():
        if line.startswith("TOTAL") or "TOTAL" in line:
            parts = line.split()
            for part in reversed(parts):
                if part.endswith("%"):
                    try:
                        stmt_cov = float(part.rstrip("%"))
                        break
                    except ValueError:
                        pass
    return stmt_cov, branch_cov
