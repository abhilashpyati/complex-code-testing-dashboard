"""
Result formatter — normalises raw tool outputs into a consistent structure.
"""
from typing import Any, Dict, List


def make_criterion(
    criterion_id: str,
    name: str,
    status: str,
    details: str,
    tool: str,
    line: int = 0,
    recommendation: str = "",
    raw: Any = None,
) -> Dict:
    """
    Create a normalised test criterion dict.

    status must be one of: PASSED, WARNING, FAILED, NOT_EXECUTED
    """
    assert status in ("PASSED", "WARNING", "FAILED", "NOT_EXECUTED"), \
        f"Invalid status: {status}"
    return {
        "id": criterion_id,
        "name": name,
        "status": status,
        "details": details,
        "tool": tool,
        "line": line,
        "recommendation": recommendation,
        "raw": raw,
    }


def summarise_criteria(criteria: List[Dict]) -> Dict:
    """Return counts of each status category across criteria."""
    counts = {"PASSED": 0, "WARNING": 0, "FAILED": 0, "NOT_EXECUTED": 0}
    for c in criteria:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    return counts


def calculate_health_score(
    passed: int,
    warning: int,
    failed: int,
    not_executed: int,
    total: int,
) -> float:
    """
    Calculate a 0-100 health score.

    - PASSED contributes full weight.
    - WARNING contributes half weight.
    - FAILED and NOT_EXECUTED contribute zero.
    """
    if total == 0:
        return 0.0
    score = (passed + 0.5 * warning) / total * 100
    return round(score, 1)
