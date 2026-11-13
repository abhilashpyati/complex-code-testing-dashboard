"""
Cyclomatic Complexity Analyzer — Module 7.
Uses Radon to calculate McCabe complexity for functions and classes.

Formula: V(G) = E - N + 2P  (or decision points + 1 for a single function)

Risk categories:
  LOW:      1–5
  MODERATE: 6–12
  HIGH:     13–25
  CRITICAL: > 25
"""
import os
import json
from typing import Dict, List

from backend.services.execution_service import run_tool, get_python_executable
from backend.utils.result_formatter import make_criterion
from config import COMPLEXITY_LOW_MAX, COMPLEXITY_MODERATE_MAX, COMPLEXITY_HIGH_MAX

TOOL = "Radon"


def get_risk_level(complexity: int) -> str:
    if complexity <= COMPLEXITY_LOW_MAX:
        return "LOW"
    elif complexity <= COMPLEXITY_MODERATE_MAX:
        return "MODERATE"
    elif complexity <= COMPLEXITY_HIGH_MAX:
        return "HIGH"
    else:
        return "CRITICAL"


def get_grade(complexity: int) -> str:
    # Radon grade scale: A(1-5), B(6-10), C(11-15), D(16-20), E(21-25), F(>25)
    if complexity <= 5:
        return "A"
    elif complexity <= 10:
        return "B"
    elif complexity <= 15:
        return "C"
    elif complexity <= 20:
        return "D"
    elif complexity <= 25:
        return "E"
    else:
        return "F"


def analyze(workspace_dir: str, code_path: str, code: str) -> Dict:
    """Run Radon complexity analysis."""
    python = get_python_executable()

    # cc: cyclomatic complexity per function/class
    cc_result = run_tool(
        [python, "-m", "radon", "cc", code_path, "-s", "-j"],
        workspace_dir,
    )

    # mi: maintainability index
    mi_result = run_tool(
        [python, "-m", "radon", "mi", code_path, "-s", "-j"],
        workspace_dir,
    )

    functions = _parse_cc(cc_result)
    mi_data = _parse_mi(mi_result)

    overall = _calculate_overall(functions)
    recommendations = _generate_recommendations(functions)

    return {
        "functions": functions,
        "mi_data": mi_data,
        "overall": overall,
        "recommendations": recommendations,
        "raw_cc": cc_result,
        "raw_mi": mi_result,
    }


def _parse_cc(result: Dict) -> List[Dict]:
    """Parse Radon CC JSON output."""
    functions = []
    stdout = result.get("stdout", "")
    if not stdout.strip():
        return functions
    try:
        # Radon JSON output: {filename: [results]}
        start = stdout.find("{")
        if start != -1:
            data = json.loads(stdout[start:])
            for fname, items in data.items():
                for item in items:
                    complexity = item.get("complexity", 1)
                    functions.append({
                        "name": item.get("name", "unknown"),
                        "type": item.get("type", "function"),
                        "line": item.get("lineno", 0),
                        "complexity": complexity,
                        "risk": get_risk_level(complexity),
                        "grade": get_grade(complexity),
                    })
    except (json.JSONDecodeError, ValueError):
        pass
    return functions


def _parse_mi(result: Dict) -> Dict:
    """Parse Radon MI JSON output."""
    stdout = result.get("stdout", "")
    mi_data = {}
    if not stdout.strip():
        return mi_data
    try:
        start = stdout.find("{")
        if start != -1:
            data = json.loads(stdout[start:])
            for fname, info in data.items():
                mi_data[fname] = {
                    "mi": info.get("mi", 0),
                    "rank": info.get("rank", "?"),
                }
    except (json.JSONDecodeError, ValueError):
        pass
    return mi_data


def _calculate_overall(functions: List[Dict]) -> Dict:
    if not functions:
        return {
            "average": 0,
            "max": 0,
            "min": 0,
            "total": 0,
            "risk": "LOW",
            "grade": "A",
            "distribution": {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0},
        }

    complexities = [f["complexity"] for f in functions]
    avg = sum(complexities) / len(complexities)
    dist = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
    for f in functions:
        dist[f["risk"]] += 1

    overall_complexity = max(complexities)
    return {
        "average": round(avg, 2),
        "max": max(complexities),
        "min": min(complexities),
        "total": sum(complexities),
        "count": len(functions),
        "risk": get_risk_level(int(avg)),
        "grade": get_grade(int(avg)),
        "distribution": dist,
    }


def _generate_recommendations(functions: List[Dict]) -> List[str]:
    recs = []
    high_complexity = [f for f in functions if f["complexity"] > COMPLEXITY_MODERATE_MAX]
    if high_complexity:
        names = ", ".join(f["name"] for f in high_complexity[:5])
        recs.append(
            f"Refactor high-complexity functions: {names}. "
            "Consider splitting into smaller, single-responsibility functions."
        )
    critical = [f for f in functions if f["risk"] == "CRITICAL"]
    if critical:
        recs.append(
            f"{len(critical)} function(s) are CRITICAL complexity. "
            "Each represents many independent execution paths — thorough testing is essential."
        )
    if not recs:
        recs.append("Complexity levels are acceptable. Continue monitoring as code grows.")
    return recs
