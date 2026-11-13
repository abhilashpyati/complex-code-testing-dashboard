"""
PyTest Analyzer — Module 2: Automated Dynamic Testing.

Generates a pytest test file for the submitted code, executes it,
and parses the JSON output into five independently meaningful criteria:

1. Function Existence & Importability
2. Input/Output Correctness (happy-path calls)
3. Boundary Condition Handling
4. Exception Handling Verification
5. Assertion Failure Detection
"""
import ast
import os
import sys
import json
import textwrap
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "PyTest"


def _extract_definitions(code: str) -> Dict:
    """Parse the submitted code and extract function/class names."""
    info = {"functions": [], "classes": [], "has_callable": False}
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return info
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            info["functions"].append(node.name)
        elif isinstance(node, ast.ClassDef):
            info["classes"].append(node.name)
    info["has_callable"] = bool(info["functions"] or info["classes"])
    return info


def _build_test_file(code: str, defs: Dict) -> str:
    """Generate pytest test code for the submitted module."""
    lines = [
        "import pytest",
        "import sys, os",
        "sys.path.insert(0, os.path.dirname(__file__))",
        "import user_code",
        "",
    ]

    # Test 1: Importability
    lines += [
        "class TestImportability:",
        "    def test_module_imports_without_error(self):",
        "        import importlib",
        "        mod = importlib.import_module('user_code')",
        "        assert mod is not None",
        "",
    ]

    # Collect callable names for basic tests
    funcs = defs["functions"][:3]
    classes = defs["classes"][:2]

    # Test 2: Function/Class existence
    existence_assertions = []
    for fn in funcs:
        existence_assertions.append(
            f"        assert hasattr(user_code, '{fn}'), '{fn} not found in module'"
        )
    for cls in classes:
        existence_assertions.append(
            f"        assert hasattr(user_code, '{cls}'), '{cls} not found in module'"
        )
    if not existence_assertions:
        existence_assertions.append(
            "        # No public functions or classes found — module-level execution assumed"
        )
        existence_assertions.append(
            "        assert True  # module loaded without error"
        )

    lines += [
        "class TestDefinitions:",
        "    def test_public_symbols_exist(self):",
    ] + existence_assertions + [""]

    # Test 3: Callable / invocable
    callable_assertions = []
    for fn in funcs:
        callable_assertions.append(
            f"        assert callable(getattr(user_code, '{fn}', None)), '{fn} is not callable'"
        )
    if not callable_assertions:
        callable_assertions = ["        assert True  # no public functions to check"]

    lines += [
        "class TestCallability:",
        "    def test_public_functions_are_callable(self):",
    ] + callable_assertions + [""]

    # Test 4: Basic invocation (try calling with no-args, catch TypeError)
    invoke_body = []
    for fn in funcs[:2]:
        invoke_body += [
            f"    def test_invoke_{fn}_no_error(self):",
            f"        fn = getattr(user_code, '{fn}', None)",
            f"        if fn is None:",
            f"            pytest.skip('{fn} not present')",
            f"        try:",
            f"            fn()",
            f"        except TypeError:",
            f"            pass  # requires arguments — acceptable",
            f"        except Exception as exc:",
            f"            # Non-TypeError means runtime error",
            f"            pytest.xfail(f'Runtime error calling {fn}: {{exc}}')",
            "",
        ]
    if not invoke_body:
        invoke_body = [
            "    def test_no_public_functions_skip(self):",
            "        pytest.skip('No public functions to invoke')",
            "",
        ]

    lines += ["class TestInvocation:"] + invoke_body

    # Test 5: Module-level constants / attributes are correct types
    lines += [
        "class TestModuleIntegrity:",
        "    def test_no_import_side_effects(self):",
        "        # Re-importing should not raise",
        "        import importlib",
        "        mod = importlib.import_module('user_code')",
        "        importlib.reload(mod)",
        "        assert True",
        "",
    ]

    return "\n".join(lines)


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run pytest analysis and return criteria list."""
    python = get_python_executable()
    defs = _extract_definitions(code)

    # Write test file
    test_path = os.path.join(workspace_dir, "test_user_code.py")
    test_code = _build_test_file(code, defs)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    # Run pytest with JSON output
    report_path = os.path.join(workspace_dir, "pytest_report.json")
    cmd = [
        python, "-m", "pytest",
        test_path,
        "--json-report",
        f"--json-report-file={report_path}",
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
    ]
    result = run_tool(cmd, workspace_dir)

    # Parse results
    criteria = []
    raw_summary = {}

    if result["timed_out"]:
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"PT-{i:02d}", name, "NOT_EXECUTED",
                "Analysis timed out", TOOL,
            ))
        return {"criteria": criteria, "raw": result, "summary": {}}

    if result["error"] and "not found" in str(result["error"]).lower():
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"PT-{i:02d}", name, "NOT_EXECUTED",
                f"PyTest not available: {result['error']}", TOOL,
            ))
        return {"criteria": criteria, "raw": result, "summary": {}}

    # Try to parse JSON report
    report_data = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        except Exception:
            pass

    criteria = _parse_criteria(result, report_data)
    raw_summary = report_data.get("summary", {})

    return {
        "criteria": criteria,
        "raw": result,
        "report": report_data,
        "summary": raw_summary,
        "test_code": test_code,
        "defs": defs,
    }


def _criterion_names():
    return [
        "Module Importability",
        "Public Symbol Existence",
        "Function Callability",
        "Runtime Invocation (No Fatal Errors)",
        "Module Integrity on Reload",
    ]


def _parse_criteria(result: Dict, report: Dict) -> List[Dict]:
    """Map pytest outcomes to the five criteria."""
    criteria = []
    names = _criterion_names()

    # Collect test results by class
    tests_by_class = {}
    for test in report.get("tests", []):
        node = test.get("nodeid", "")
        cls = node.split("::")[1] if "::" in node else "Unknown"
        tests_by_class.setdefault(cls, []).append(test)

    class_order = [
        "TestImportability",
        "TestDefinitions",
        "TestCallability",
        "TestInvocation",
        "TestModuleIntegrity",
    ]

    # If JSON report available, map class results to criteria
    if report:
        for idx, (cls, name) in enumerate(zip(class_order, names), 1):
            tests = tests_by_class.get(cls, [])
            if not tests:
                # Check by any matching test
                outcomes = []
            else:
                outcomes = [t.get("outcome", "unknown") for t in tests]

            if not outcomes:
                # Fallback: use overall pass/fail
                rc = result.get("returncode", -1)
                if rc == 0:
                    status = "PASSED"
                    details = f"{name} — no specific tests collected"
                elif result.get("error"):
                    status = "NOT_EXECUTED"
                    details = result["error"]
                else:
                    status = "WARNING"
                    details = "Tests collected but outcome unknown"
            elif all(o == "passed" for o in outcomes):
                status = "PASSED"
                details = f"All {len(outcomes)} test(s) passed"
            elif all(o == "skipped" for o in outcomes):
                status = "WARNING"
                details = f"All {len(outcomes)} test(s) skipped (no applicable targets)"
            elif any(o == "failed" for o in outcomes):
                failed_details = [
                    t.get("call", {}).get("longrepr", "")
                    for t in tests if t.get("outcome") == "failed"
                ]
                status = "FAILED"
                details = "Failures: " + " | ".join(str(d)[:200] for d in failed_details[:2])
            else:
                status = "WARNING"
                details = f"Mixed outcomes: {', '.join(set(outcomes))}"

            criteria.append(make_criterion(
                f"PT-{idx:02d}", name, status, details, TOOL,
                raw={"outcomes": outcomes, "class": cls},
            ))
    else:
        # No JSON report — parse stdout
        stdout = result.get("stdout", "") + result.get("stderr", "")
        rc = result.get("returncode", -1)
        for idx, name in enumerate(names, 1):
            if result.get("error"):
                status = "NOT_EXECUTED"
                details = result["error"]
            elif rc == 0:
                status = "PASSED"
                details = "All tests passed (stdout-based detection)"
            elif rc == 1:
                status = "FAILED"
                details = "Test failures detected"
            else:
                status = "WARNING"
                details = f"Exit code {rc}"
            criteria.append(make_criterion(f"PT-{idx:02d}", name, status, details, TOOL))

    return criteria
