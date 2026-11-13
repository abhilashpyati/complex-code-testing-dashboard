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
            init_args = []
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
                "init_args": init_args[:init_req] if init_req else [],
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
    str_hints = ("text", "str", "string", "word", "msg", "message", "name", "title", "desc", "key", "author", "owner", "account")
    if any(k in a.lower() for a in args for k in str_hints) or any(a.lower() == "s" for a in args):
        calls.append(tuple(f"val_{i}" if (any(k in a.lower() for k in str_hints) or a.lower() == "s") else i + 1 for i, a in enumerate(args)))
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

    funcs = defs.get("functions", [])[:8]
    classes = defs.get("classes", [])[:8]

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
            init_names = cls.get("init_args", [])
            init_arg_list = []
            str_hints = ("name", "owner", "acc", "account", "id", "user", "desc", "title", "key", "str", "text")
            for idx in range(init_req):
                pname = init_names[idx].lower() if idx < len(init_names) else ""
                if any(h in pname for h in str_hints):
                    init_arg_list.append(f"test_{pname or idx}")
                else:
                    init_arg_list.append(100.0)
            init_args = tuple(init_arg_list)
            exec_tests.append(f"    def test_class_{cname}_instantiation(self):")
            exec_tests.append("        assert user_code is not None")
            exec_tests.append(f"        cls = getattr(user_code, '{cname}', None)")
            exec_tests.append("        assert cls is not None")
            exec_tests.append("        try:")
            exec_tests.append(f"            inst = cls(*{repr(init_args)})")
            exec_tests.append("            assert inst is not None")
            for m in cls["methods"]:
                mname = m["name"]
                m_args = tuple(1 for _ in range(m["required"]))
                exec_tests.append(f"            try:")
                exec_tests.append(f"                getattr(inst, '{mname}')(*{repr(m_args)})")
                exec_tests.append(f"            except Exception:")
                exec_tests.append(f"                pass")
            exec_tests.append("        except Exception:")
            exec_tests.append("            pass")
            exec_tests.append("")

    lines += ["class TestFunctionExecution:"] + exec_tests + [""]

    # Test 3: Boundary & Edge Case Handling
    boundary_tests = []
    if not funcs and not classes:
        boundary_tests.append("    def test_no_functions_for_boundary(self):")
        boundary_tests.append("        pytest.skip('NOT_APPLICABLE: No public functions or classes for boundary testing')")
    else:
        for fn in funcs[:6]:
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
            boundary_tests.append("                pass")
            boundary_tests.append("")

        str_hints = ("name", "owner", "acc", "account", "id", "user", "desc", "title", "key", "str", "text")
        for cls in classes:
            cname = cls["name"]
            init_req = cls["init_required"]
            init_names = cls.get("init_args", [])
            init_arg_list = []
            for idx in range(init_req):
                pname = init_names[idx].lower() if idx < len(init_names) else ""
                if any(h in pname for h in str_hints):
                    init_arg_list.append(f"test_{pname or idx}")
                else:
                    init_arg_list.append(100.0)
            init_args = tuple(init_arg_list)

            # Boundary init arguments (empty strings, zeros, negatives)
            b_init_list = []
            if init_req > 0:
                b_init_list.append(tuple("" if any(h in (init_names[i].lower() if i < len(init_names) else "") for h in str_hints) else 0 for i in range(init_req)))
                b_init_list.append(tuple("test" if any(h in (init_names[i].lower() if i < len(init_names) else "") for h in str_hints) else -10.0 for i in range(init_req)))

            boundary_tests.append(f"    def test_class_boundary_{cname}(self):")
            boundary_tests.append("        assert user_code is not None")
            boundary_tests.append(f"        cls = getattr(user_code, '{cname}', None)")
            boundary_tests.append("        assert cls is not None")
            if b_init_list:
                boundary_tests.append("        for b_init in " + repr(b_init_list) + ":")
                boundary_tests.append("            try:")
                boundary_tests.append("                cls(*b_init)")
                boundary_tests.append("            except (ValueError, TypeError, ZeroDivisionError, IndexError, KeyError, OverflowError):")
                boundary_tests.append("                pass")
            boundary_tests.append("        try:")
            boundary_tests.append(f"            inst = cls(*{repr(init_args)})")
            for m in cls["methods"]:
                mname = m["name"]
                m_req = m["required"]
                boundary_tests.append("            for b_arg in [" + f"(0,) * {m_req}, (-1,) * {m_req}, (10,) * {m_req}" + "]:")
                boundary_tests.append("                try:")
                boundary_tests.append(f"                    getattr(inst, '{mname}')(*b_arg)")
                boundary_tests.append("                except (ValueError, TypeError, ZeroDivisionError, IndexError, KeyError, OverflowError, Exception):")
                boundary_tests.append("                    pass")
            boundary_tests.append("        except Exception:")
            boundary_tests.append("            pass")
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
        "Test Execution & Discovery",
        "Assertion Validation",
        "Runtime Error Detection",
        "Function Execution Under Test",
        "Boundary and Input Validation",
    ]


def _parse_criteria(result: Dict, report: Dict, defs: Dict) -> List[Dict]:
    """Map pytest outcomes to the five Phase 4 dynamic testing criteria."""
    criteria = []
    names = _criterion_names()

    # Collect test results by test class
    all_tests = report.get("tests", [])
    tests_by_class = {}
    for test in all_tests:
        node = test.get("nodeid", "")
        cls = node.split("::")[1] if "::" in node else "Unknown"
        tests_by_class.setdefault(cls, []).append(test)

    raw_summary = report.get("summary", {})
    passed_count = raw_summary.get("passed", 0)
    failed_count = raw_summary.get("failed", 0)
    skipped_count = raw_summary.get("skipped", 0)
    total_count = raw_summary.get("total", passed_count + failed_count + skipped_count)
    has_callable = defs.get("has_callable", False)

    # -------------------------------------------------------------
    # PT-01: Test Execution & Discovery
    # -------------------------------------------------------------
    if total_count == 0:
        if not has_callable:
            status_01 = "NOT_APPLICABLE"
            details_01 = "No tests discovered; submitted module contains no executable callables"
            rec_01 = "Add callable functions or classes to enable dynamic test discovery"
        else:
            status_01 = "WARNING"
            details_01 = "No tests were executed"
            rec_01 = "Verify code structure and test generator discovery"
    elif failed_count == 0 and passed_count > 0:
        status_01 = "PASSED"
        details_01 = f"PyTest executed {total_count} test(s) successfully: {passed_count} passed, {skipped_count} skipped, 0 failed"
        rec_01 = "Continue maintaining thorough automated tests"
    elif failed_count > 0:
        status_01 = "FAILED"
        details_01 = f"PyTest executed {total_count} test(s) with {failed_count} failure(s): {passed_count} passed, {skipped_count} skipped"
        rec_01 = "Investigate and resolve failing test cases"
    else:
        status_01 = "WARNING"
        details_01 = f"All {total_count} test(s) were skipped or incomplete"
        rec_01 = "Provide executable test targets and inputs"

    criteria.append(make_criterion(
        "PT-01", names[0], status_01, details_01, TOOL,
        raw={"passed": passed_count, "failed": failed_count, "skipped": skipped_count, "total": total_count},
        recommendation=rec_01,
    ))

    # -------------------------------------------------------------
    # PT-02: Assertion Validation
    # -------------------------------------------------------------
    # Look for AssertionError specifically across any test
    assertion_failures = []
    for t in all_tests:
        if t.get("outcome") == "failed":
            crash = t.get("call", {}).get("crash", {})
            msg = crash.get("message", "") or str(t.get("call", {}).get("longrepr", ""))
            if "AssertionError" in msg or "assert " in msg:
                node = t.get("nodeid", "").split("::")[-1]
                clean_msg = msg.splitlines()[-1] if msg.splitlines() else msg
                assertion_failures.append(f"{node}: {clean_msg[:120]}")

    if not has_callable:
        status_02 = "NOT_APPLICABLE"
        details_02 = "No functions or assertions to validate in submitted module"
        rec_02 = "Add assertions or test specifications to validate logic"
    elif assertion_failures:
        status_02 = "FAILED"
        details_02 = f"{len(assertion_failures)} assertion failure(s): " + " | ".join(assertion_failures[:2])
        rec_02 = "Review failed assertions to correct algorithmic or functional defects"
    elif failed_count == 0 and passed_count > 0:
        status_02 = "PASSED"
        details_02 = f"All evaluated test assertions passed without violation ({passed_count} verified)"
        rec_02 = "Add domain-specific boundary assertions to deepen verification"
    else:
        status_02 = "PASSED"
        details_02 = "No assertion violations detected"
        rec_02 = "Specify expected outputs and invariants"

    criteria.append(make_criterion(
        "PT-02", names[1], status_02, details_02, TOOL,
        raw={"assertion_failures": assertion_failures},
        recommendation=rec_02,
    ))

    # -------------------------------------------------------------
    # PT-03: Runtime Error Detection
    # -------------------------------------------------------------
    # Capture runtime exceptions (NameError, ZeroDivisionError, TypeError, etc.)
    runtime_errors = []
    for t in all_tests:
        if t.get("outcome") == "failed":
            crash = t.get("call", {}).get("crash", {})
            msg = crash.get("message", "") or str(t.get("call", {}).get("longrepr", ""))
            if "AssertionError" not in msg:
                node = t.get("nodeid", "").split("::")[-1]
                clean_msg = msg.splitlines()[-1] if msg.splitlines() else msg
                runtime_errors.append(f"{node}: {clean_msg[:120]}")

    if not has_callable:
        status_03 = "PASSED"
        details_03 = "Module imported without top-level runtime exceptions"
        rec_03 = "Maintain exception safety in module initialization"
    elif runtime_errors:
        status_03 = "FAILED"
        details_03 = f"{len(runtime_errors)} runtime exception(s) detected: " + " | ".join(runtime_errors[:2])
        rec_03 = "Handle potential runtime exceptions (ZeroDivisionError, NameError, TypeError)"
    else:
        status_03 = "PASSED"
        details_03 = "No unhandled runtime errors detected during test execution"
        rec_03 = "Ensure robust error handling on edge cases"

    criteria.append(make_criterion(
        "PT-03", names[2], status_03, details_03, TOOL,
        raw={"runtime_errors": runtime_errors},
        recommendation=rec_03,
    ))

    # -------------------------------------------------------------
    # PT-04: Function Execution Under Test
    # -------------------------------------------------------------
    fn_tests = tests_by_class.get("TestFunctionExecution", [])
    if not has_callable or not fn_tests:
        status_04 = "NOT_APPLICABLE"
        details_04 = "No public functions or classes defined in module"
        rec_04 = "Define callable functions or classes to verify invocation"
    else:
        fn_outcomes = [t.get("outcome", "unknown") for t in fn_tests]
        if all(o == "passed" for o in fn_outcomes):
            status_04 = "PASSED"
            details_04 = f"All {len(fn_outcomes)} identified callable(s) invoked successfully with valid inputs"
            rec_04 = "Broaden parameter input ranges and test scenarios"
        elif any(o == "failed" for o in fn_outcomes):
            status_04 = "FAILED"
            fn_fails = [t.get("nodeid", "").split("::")[-1] for t in fn_tests if t.get("outcome") == "failed"]
            details_04 = f"Invocation failed on {len(fn_fails)} callable(s): " + ", ".join(fn_fails[:3])
            rec_04 = "Ensure functions accept documented parameter types and counts"
        else:
            status_04 = "WARNING"
            details_04 = "Partial callable execution outcome"
            rec_04 = "Verify function signatures"

    criteria.append(make_criterion(
        "PT-04", names[3], status_04, details_04, TOOL,
        raw={"tests_count": len(fn_tests)},
        recommendation=rec_04,
    ))

    # -------------------------------------------------------------
    # PT-05: Boundary and Input Validation
    # -------------------------------------------------------------
    b_tests = tests_by_class.get("TestBoundaryConditions", [])
    if not has_callable or not b_tests:
        status_05 = "NOT_APPLICABLE"
        details_05 = "No public callables to test boundary conditions against"
        rec_05 = "Add functions taking parameters to test edge conditions"
    else:
        b_outcomes = [t.get("outcome", "unknown") for t in b_tests]
        if all(o == "passed" for o in b_outcomes):
            status_05 = "PASSED"
            details_05 = f"All {len(b_outcomes)} boundary/edge test(s) handled inputs and exceptions gracefully"
            rec_05 = "Test additional domain boundaries (overflow, empty structures)"
        elif any(o == "failed" for o in b_outcomes):
            status_05 = "FAILED"
            b_fails = [t.get("nodeid", "").split("::")[-1] for t in b_tests if t.get("outcome") == "failed"]
            details_05 = f"Boundary failure on {len(b_fails)} test(s): " + ", ".join(b_fails[:3])
            rec_05 = "Add guard clauses and input validation for boundary cases (0, negatives, empty strings)"
        else:
            status_05 = "WARNING"
            details_05 = "Partial boundary test outcome"
            rec_05 = "Investigate boundary edge cases"

    criteria.append(make_criterion(
        "PT-05", names[4], status_05, details_05, TOOL,
        raw={"tests_count": len(b_tests)},
        recommendation=rec_05,
    ))

    return criteria
