"""
Result formatter — normalises raw tool outputs into a consistent structure.
"""
from typing import Any, Dict, List

VALID_STATUSES = ("PASSED", "WARNING", "FAILED", "NOT_EXECUTED", "NOT_APPLICABLE")


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

    status must be one of: PASSED, WARNING, FAILED, NOT_EXECUTED, NOT_APPLICABLE
    """
    assert status in VALID_STATUSES, f"Invalid status: {status}. Must be one of {VALID_STATUSES}"
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
    counts = {
        "PASSED": 0,
        "WARNING": 0,
        "FAILED": 0,
        "NOT_EXECUTED": 0,
        "NOT_APPLICABLE": 0,
    }
    for c in criteria:
        st = c.get("status", "NOT_EXECUTED")
        counts[st] = counts.get(st, 0) + 1
    return counts


def calculate_health_score(
    passed: int,
    warning: int,
    failed: int,
    not_executed: int,
    total: int,
    not_applicable: int = 0,
) -> float:
    """
    Calculate a 0-100 health score.

    - PASSED contributes full weight.
    - WARNING contributes half weight.
    - FAILED and NOT_EXECUTED contribute zero.
    - NOT_APPLICABLE criteria are excluded from the denominator.
    """
    applicable_total = total - not_applicable
    if applicable_total <= 0:
        return 100.0 if passed > 0 else 0.0
    score = (passed + 0.5 * warning) / applicable_total * 100
    return round(score, 1)
