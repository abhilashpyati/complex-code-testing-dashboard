"""
Defect Predictor — Module 8: Rule-Based Defect Risk Prediction (Phase 4).

This is a HEURISTIC model, NOT a machine-learning probability.
Score is calculated from weighted contributions of four available components:
  - Security findings        (35.3%)
  - Cyclomatic complexity    (29.4%)
  - Static analysis findings (23.5%)
  - Style violations         (11.8%)
  Total:                     100.0%

If any component metric is unavailable (e.g. Radon timed out or failed),
weights are dynamically re-normalized across available components.

Risk Categories:
  LOW:      0–24
  MODERATE: 25–49
  HIGH:     50–74
  CRITICAL: 75–100
"""
from typing import Dict, List, Optional

from config import (
    RISK_WEIGHT_SECURITY,
    RISK_WEIGHT_COMPLEXITY,
    RISK_WEIGHT_STATIC,
    RISK_WEIGHT_STYLE,
)

WEIGHTS = {
    "security": RISK_WEIGHT_SECURITY,
    "complexity": RISK_WEIGHT_COMPLEXITY,
    "static_analysis": RISK_WEIGHT_STATIC,
    "style": RISK_WEIGHT_STYLE,
}


def predict(
    complexity_data: Dict,
    security_findings: List[Dict],
    static_findings: List[Dict],
    style_findings: List[Dict],
) -> Dict:
    """
    Compute a heuristic defect risk score (0–100) and category across 4 components.

    Returns a dict with: score, category, components, high_risk_functions,
    recommendations, methodology_note.
    """
    # --- Component scores (each 0–100 or None if unavailable) ---
    security_score = _security_score(security_findings)
    complexity_score = _complexity_score(complexity_data)
    static_score = _static_score(static_findings)
    style_score = _style_score(style_findings)

    # Component definitions: (name, score, base_weight)
    raw_components = [
        ("security", security_score, RISK_WEIGHT_SECURITY),
        ("complexity", complexity_score, RISK_WEIGHT_COMPLEXITY),
        ("static_analysis", static_score, RISK_WEIGHT_STATIC),
        ("style", style_score, RISK_WEIGHT_STYLE),
    ]

    # Calculate available weights and normalize
    available_weights = sum(w for _, s, w in raw_components if s is not None)
    weighted_sum = sum(s * w for _, s, w in raw_components if s is not None)

    if available_weights > 0:
        total_score = round(min(100.0, max(0.0, weighted_sum / available_weights)), 1)
    else:
        total_score = 0.0

    # Risk category
    if total_score < 25:
        category = "LOW"
    elif total_score < 50:
        category = "MODERATE"
    elif total_score < 75:
        category = "HIGH"
    else:
        category = "CRITICAL"

    # Build components dictionary
    components = {}
    for name, s, w in raw_components:
        if s is not None and available_weights > 0:
            effective_weight = round(w / available_weights, 3)
            contribution = round((s * w) / available_weights, 1)
            components[name] = {
                "score": round(s, 1),
                "weight": w,
                "effective_weight": effective_weight,
                "contribution": contribution,
                "status": "AVAILABLE",
            }
        else:
            components[name] = {
                "score": None,
                "weight": w,
                "effective_weight": 0.0,
                "contribution": 0.0,
                "status": "UNAVAILABLE",
            }

    # High-risk functions
    high_risk_functions = _identify_high_risk_functions(complexity_data)

    # Recommendations
    recommendations = _generate_recommendations(
        total_score, category, complexity_score, security_score,
        static_score, style_score, security_findings,
    )

    return {
        "score": total_score,
        "category": category,
        "components": components,
        "high_risk_functions": high_risk_functions,
        "recommendations": recommendations,
        "methodology_note": (
            "Defect risk is a heuristic estimate based on security, complexity, "
            "static analysis, and coding-style metrics. It does not guarantee the "
            "presence or absence of defects."
        ),
    }


def _complexity_score(data: Optional[Dict]) -> Optional[float]:
    """Higher complexity → higher risk score. Returns None if complexity data unavailable."""
    if not data or not isinstance(data, dict):
        return None
    overall = data.get("overall", {})
    if not isinstance(overall, dict) or overall.get("status") == "NOT_EXECUTED":
        return None

    avg_complexity = overall.get("average")
    if avg_complexity is None:
        return None

    dist = overall.get("distribution", {})

    # Base score from average complexity
    if avg_complexity <= 5:
        base = avg_complexity * 4.0
    elif avg_complexity <= 12:
        base = 20.0 + (avg_complexity - 5.0) * 7.0
    elif avg_complexity <= 25:
        base = 69.0 + (avg_complexity - 12.0) * 2.0
    else:
        base = 95.0

    # Bonus for critical functions
    critical_count = dist.get("CRITICAL", 0)
    high_count = dist.get("HIGH", 0)
    base = min(100.0, base + critical_count * 10.0 + high_count * 5.0)
    return base


def _security_score(findings: List[Dict]) -> float:
    """More / higher severity security findings → higher risk."""
    if not findings:
        return 0.0
    score = 0.0
    for f in findings:
        sev = f.get("severity", "LOW").upper()
        conf = f.get("confidence", "LOW").upper()
        if sev == "HIGH":
            score += 25
        elif sev == "MEDIUM":
            score += 12
        else:
            score += 5
        if conf == "HIGH":
            score += 5
    return min(100.0, score)


def _static_score(findings: List[Dict]) -> float:
    """More static analysis findings → higher risk."""
    if not findings:
        return 0.0
    count = len(findings)
    if count <= 2:
        return float(count * 10)
    elif count <= 10:
        return float(20 + (count - 2) * 7)
    else:
        return min(100.0, float(76 + (count - 10) * 2))


def _style_score(findings: List[Dict]) -> float:
    """Style violations contribute to the style risk component."""
    count = len(findings)
    if count == 0:
        return 0.0
    return min(100.0, float(count * 3))


def _identify_high_risk_functions(data: Optional[Dict]) -> List[Dict]:
    if not data or not isinstance(data, dict):
        return []
    functions = data.get("functions", [])
    if not isinstance(functions, list):
        return []
    high_risk = [
        f for f in functions
        if isinstance(f, dict) and f.get("risk") in ("HIGH", "CRITICAL")
    ]
    return sorted(high_risk, key=lambda f: f.get("complexity", 0), reverse=True)


def _generate_recommendations(
    score, category, complexity_score, security_score,
    static_score, style_score, security_findings,
) -> List[str]:
    recs = []

    if security_score > 50:
        recs.append(
            "⚠️ HIGH SECURITY RISK: Address Bandit security findings immediately. "
            "Security vulnerabilities are weighted most heavily in the risk score."
        )
    if complexity_score is not None and complexity_score > 60:
        recs.append(
            "🔀 HIGH COMPLEXITY: Refactor functions with complexity > 12. "
            "High cyclomatic complexity directly increases the probability of latent defects."
        )
    if static_score > 50:
        recs.append(
            "🔍 STATIC ISSUES: Resolve unused variables, missing docstrings, "
            "and naming convention violations."
        )
    if style_score > 40:
        recs.append(
            "📐 STYLE VIOLATIONS: Fix PEP 8 violations to improve code readability "
            "and reduce maintenance defects."
        )
    if not recs:
        recs.append(
            "✅ Code quality is good. Continue enforcing standards and writing tests."
        )

    # Specific security recommendations
    for f in security_findings[:2]:
        code = f.get("code", "")
        if code in ("B307", "B102"):
            recs.append("Remove or replace eval() / exec() with safer alternatives.")
        elif code in ("B303", "B324"):
            recs.append("Replace MD5/SHA-1 with SHA-256 or bcrypt for cryptographic use.")

    return recs
