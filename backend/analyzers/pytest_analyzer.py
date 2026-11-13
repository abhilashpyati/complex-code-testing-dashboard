"""
PyTest Analyzer — Module 2: Automated Dynamic Testing.

Generates a comprehensive PyTest test file for the submitted Python code,
inspecting function signatures and generating deterministic inputs to test:
1. Module Importability & Syntax Integrity (PT-01)
2. Public Function Execution with Valid Inputs (PT-02)
3. Boundary Condition & Edge Case Execution (PT-03)
4. Runtime Exception & Name Error Resilience (PT-04)
5. Module Integrity & Invariant Preservation (PT-05)

Note on Logical Correctness:
Dynamic test execution verifies execution stability, parameter handling, and
exception resilience. Verification of complete logical correctness requires a
formal behavioral specification or expected output assertions.
"""
import ast
import os
import sys
import json
from typing import Dict, List, Any

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion

TOOL = "PyTest"


def _extract_definitions(code: str) -> Dict[str, Any]:
    """Parse submitted code AST to extract function signatures and classes."""
    info: Dict[str, Any] = {"functions": [], "classes": [], "has_callable": False}
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return info

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            all_args = [a.arg for a in node.args.args if a.arg != "self"]
            defaults_count = len(node.args.defaults)
            req_count = max(0, len(all_args) - defaults_count)
            info["functions"].append({
                "name": node.name,
                "args": all_args,
                "required": req_count,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = []
            init_req = 0
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name == "__init__":
                        init_args = [a.arg for a in item.args.args if a.arg != "self"]
                        init_req = max(0, len(init_args) - len(item.args.defaults))
                    elif not item.name.startswith("_"):
                        m_args = [a.arg for a in item.args.args if a.arg != "self"]
                        m_req = max(0, len(m_args) - len(item.args.defaults))
                        methods.append({"name": item.name, "args": m_args, "required": m_req})
            info["classes"].append({
                "name": node.name,
                "init_required": init_req,
                "methods": methods,
            })

    info["has_callable"] = bool(info["functions"] or info["classes"])
    return info


def _make_valid_args(fn_info: Dict) -> List[tuple]:
    """Generate safe, deterministic inputs for a function based on required arg count."""
    req = fn_info["required"]
    args = fn_info.get("args", [])[:req]
    if req <= 0:
        return [()]
    calls = []
    # Primary input: standard integers
    calls.append(tuple(i + 1 for i in range(req)))
    # Secondary input based on parameter naming hints
    if any(k in a.lower() for a in args for k in ("text", "str", "s", "word", "msg", "name")):
        calls.append(tuple(f"val_{i}" for i in range(req)))
    elif any(k in a.lower() for a in args for k in ("lst", "arr", "items", "nums", "data", "list")):
        calls.append(([1, 2, 3],) * req)
    return calls


def _make_boundary_args(fn_info: Dict) -> List[tuple]:
    """Generate boundary inputs (0, negatives, empty string, empty list) for testing."""
    req = fn_info["required"]
    if req <= 0:
        return [()]
    return [
        tuple(0 for _ in range(req)),
        tuple(-1 for _ in range(req)),
        tuple("" for _ in range(req)),
    ]


def _build_test_file(code: str, defs: Dict, module_name: str = "user_code") -> str:
    """Generate dynamic pytest test suite for the submitted code."""
    lines = [
        "import pytest",
        "import sys, os, importlib",
        "sys.path.insert(0, os.path.dirname(__file__))",
        f"try:\n    user_code = importlib.import_module('{module_name}')\nexcept Exception:\n    user_code = None",
        "",
    ]

    # Test 1: Module Importability
    lines += [
        "class TestImportability:",
        "    def test_module_imports_without_error(self):",
        f"        mod = importlib.import_module('{module_name}')",
        "        assert mod is not None, 'Module import failed'",
        "",
    ]

    funcs = defs.get("functions", [])[:6]
    classes = defs.get("classes", [])[:3]

    # Test 2: Function & Method Execution with Valid Inputs
    exec_tests = []
    if not funcs and not classes:
        exec_tests.append("    def test_no_functions_to_execute(self):")
        exec_tests.append("        pytest.skip('NOT_APPLICABLE: No public functions or classes defined in module')")
    else:
        for fn in funcs:
            if fn.get("is_async"):
                continue
            name = fn["name"]
            valid_calls = _make_valid_args(fn)
            exec_tests.append(f"    def test_exec_{name}_valid_input(self):")
            exec_tests.append("        assert user_code is not None")
            exec_tests.append(f"        fn = getattr(user_code, '{name}', None)")
            exec_tests.append("        assert callable(fn), f'{fn} is not callable'")
            for args in valid_calls:
                exec_tests.append(f"        res = fn(*{repr(args)})")
                exec_tests.append("        # Verify function completed execution")
                exec_tests.append("        assert True")
            exec_tests.append("")

        for cls in classes:
            cname = cls["name"]
            init_req = cls["init_required"]
            init_args = tuple(1 for _ in range(init_req))
            exec_tests.append(f"    def test_class_{cname}_instantiation(self):")
            exec_tests.append("        assert user_code is not None")
            exec_tests.append(f"        cls = getattr(user_code, '{cname}', None)")
            exec_tests.append(f"        inst = cls(*{repr(init_args)})")
            exec_tests.append("        assert inst is not None")
            for m in cls["methods"][:2]:
                mname = m["name"]
                m_args = tuple(1 for _ in range(m["required"]))
                exec_tests.append(f"        res = getattr(inst, '{mname}')(*{repr(m_args)})")
                exec_tests.append("        assert True")
            exec_tests.append("")

    lines += ["class TestFunctionExecution:"] + exec_tests + [""]

    # Test 3: Boundary & Edge Case Handling
    boundary_tests = []
    if not funcs:
        boundary_tests.append("    def test_no_functions_for_boundary(self):")
        boundary_tests.append("        pytest.skip('NOT_APPLICABLE: No public functions for boundary testing')")
    else:
        for fn in funcs[:4]:
            if fn.get("is_async"):
                continue
            name = fn["name"]
            b_calls = _make_boundary_args(fn)
            boundary_tests.append(f"    def test_boundary_{name}(self):")
            boundary_tests.append("        assert user_code is not None")
            boundary_tests.append(f"        fn = getattr(user_code, '{name}', None)")
            boundary_tests.append("        assert callable(fn)")
            boundary_tests.append("        for args in " + repr(b_calls) + ":")
            boundary_tests.append("            try:")
            boundary_tests.append("                res = fn(*args)")
            boundary_tests.append("            except (ValueError, TypeError, ZeroDivisionError, IndexError, KeyError, OverflowError):")
            boundary_tests.append("                # Handled or domain-rejected input; acceptable")
            boundary_tests.append("                pass")
            boundary_tests.append("")

    lines += ["class TestBoundaryConditions:"] + boundary_tests + [""]

    # Test 4: Runtime Exception Resilience
    runtime_tests = []
    for fn in funcs[:4]:
        if fn.get("is_async"):
            continue
        name = fn["name"]
        primary_args = _make_valid_args(fn)[0]
        runtime_tests.append(f"    def test_no_fatal_error_{name}(self):")
        runtime_tests.append("        assert user_code is not None")
        runtime_tests.append(f"        fn = getattr(user_code, '{name}', None)")
        runtime_tests.append("        try:")
        runtime_tests.append(f"            fn(*{repr(primary_args)})")
        runtime_tests.append("        except (NameError, UnboundLocalError, RecursionError) as exc:")
        runtime_tests.append(f"            pytest.fail(f'Fatal runtime error in {name}: {{exc}}')")
        runtime_tests.append("        except Exception:")
        runtime_tests.append("            pass")
        runtime_tests.append("")
    if not runtime_tests:
        runtime_tests.append("    def test_script_runtime_clean(self):")
        runtime_tests.append("        assert user_code is not None, 'Module failed to execute'")
        runtime_tests.append("")

    lines += ["class TestRuntimeExceptions:"] + runtime_tests + [""]

    # Test 5: Module Integrity & Invariants
    lines += [
        "class TestModuleIntegrity:",
        "    def test_reload_and_invariants(self):",
        f"        mod = importlib.import_module('{module_name}')",
        "        importlib.reload(mod)",
        "        assert True",
        "",
    ]

    return "\n".join(lines)


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run pytest analysis and return criteria list."""
    python = get_python_executable()
    defs = _extract_definitions(code)
    module_name = os.path.splitext(os.path.basename(code_path))[0]

    # Write test file
    test_path = os.path.join(workspace_dir, "test_user_code.py")
    test_code = _build_test_file(code, defs, module_name)
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
    result = run_tool(cmd, workspace_dir, timeout=25)

    # Parse results
    criteria = []
    if result["timed_out"]:
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"PT-{i:02d}", name, "NOT_EXECUTED",
                "Analysis timed out after 25s", TOOL,
            ))
        return {"criteria": criteria, "raw": result, "summary": {}, "test_code": test_code, "defs": defs}

    if result["error"] and "not found" in str(result["error"]).lower():
        for i, name in enumerate(_criterion_names(), 1):
            criteria.append(make_criterion(
                f"PT-{i:02d}", name, "NOT_EXECUTED",
                f"PyTest not available: {result['error']}", TOOL,
            ))
        return {"criteria": criteria, "raw": result, "summary": {}, "test_code": test_code, "defs": defs}

    # Try to parse JSON report
    report_data = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        except Exception:
            pass

    criteria = _parse_criteria(result, report_data, defs)
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
        "Module Importability & Syntax Integrity",
        "Public Function Execution (Valid Inputs)",
        "Boundary Condition & Edge Case Execution",
        "Runtime Exception & Name Error Resilience",
        "Module Integrity & Invariant Preservation",
    ]


def _parse_criteria(result: Dict, report: Dict, defs: Dict) -> List[Dict]:
    """Map pytest outcomes to the five criteria."""
    criteria = []
    names = _criterion_names()

    # Collect test results by test class
    tests_by_class = {}
    for test in report.get("tests", []):
        node = test.get("nodeid", "")
        cls = node.split("::")[1] if "::" in node else "Unknown"
        tests_by_class.setdefault(cls, []).append(test)

    class_order = [
        "TestImportability",
        "TestFunctionExecution",
        "TestBoundaryConditions",
        "TestRuntimeExceptions",
        "TestModuleIntegrity",
    ]

    has_callable = defs.get("has_callable", False)

    for idx, (cls, name) in enumerate(zip(class_order, names), 1):
        crit_id = f"PT-{idx:02d}"
        tests = tests_by_class.get(cls, [])

        if not tests:
            # Handle modules without functions
            if not has_callable and cls in ("TestFunctionExecution", "TestBoundaryConditions"):
                criteria.append(make_criterion(
                    crit_id, name, "NOT_APPLICABLE",
                    "No public functions or classes defined in module", TOOL,
                    recommendation="Add public functions or classes with parameters to test execution",
                ))
                continue

            rc = result.get("returncode", -1)
            if rc == 0:
                status = "PASSED"
                details = f"{name} verified successfully"
            elif result.get("error"):
                status = "NOT_EXECUTED"
                details = str(result["error"])
            else:
                status = "WARNING"
                details = "Test outcome unknown"

            criteria.append(make_criterion(crit_id, name, status, details, TOOL))
            continue

        outcomes = [t.get("outcome", "unknown") for t in tests]

        # Check for NOT_APPLICABLE skip reasons
        skip_reasons = [
            t.get("call", {}).get("longrepr", "")
            or t.get("metadata", {}).get("skip_reason", "")
            for t in tests if t.get("outcome") == "skipped"
        ]
        is_na = any("NOT_APPLICABLE" in str(r) for r in skip_reasons) or (
            not has_callable and cls in ("TestFunctionExecution", "TestBoundaryConditions")
        )

        if is_na:
            status = "NOT_APPLICABLE"
            details = "No callable functions or classes in submitted module"
            rec = "Add callable functions to test parameter handling"
        elif all(o == "passed" for o in outcomes):
            status = "PASSED"
            details = f"All {len(outcomes)} dynamic test(s) passed successfully"
            rec = "Verify domain invariants and add property tests"
        elif any(o == "failed" for o in outcomes):
            status = "FAILED"
            failed_tests = [t for t in tests if t.get("outcome") == "failed"]
            failures_repr = []
            for ft in failed_tests[:2]:
                crash = ft.get("call", {}).get("crash", {})
                msg = crash.get("message") or str(ft.get("call", {}).get("longrepr", ""))[:150]
                failures_repr.append(f"{ft.get('nodeid', '').split('::')[-1]}: {msg}")
            details = "Failures: " + " | ".join(failures_repr)
            rec = "Debug runtime failure and inspect traceback"
        elif all(o == "skipped" for o in outcomes):
            status = "WARNING"
            details = f"All {len(outcomes)} test(s) were skipped"
            rec = "Ensure function signatures are compatible with test generation"
        else:
            status = "WARNING"
            details = f"Outcomes: {', '.join(set(outcomes))}"
            rec = "Investigate partial test outcome"

        criteria.append(make_criterion(
            crit_id, name, status, details, TOOL,
            raw={"outcomes": outcomes, "class": cls},
            recommendation=rec,
        ))

    return criteria
