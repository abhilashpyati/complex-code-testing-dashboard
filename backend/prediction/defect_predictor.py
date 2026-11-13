"""
Defect Predictor — Module 8: Rule-Based Defect Risk Prediction.

This is a HEURISTIC model, NOT a machine-learning probability.
Score is calculated from weighted contributions of:
  - Cyclomatic complexity    (25%)
  - Security findings        (30%)
  - Static analysis findings (20%)
  - Code coverage            (15%)
  - Style violations         (10%)

Risk Categories:
  LOW:      0–24
  MODERATE: 25–49
  HIGH:     50–74
  CRITICAL: 75–100
"""
from typing import Dict, List

from config import (
    RISK_WEIGHT_COMPLEXITY,
    RISK_WEIGHT_SECURITY,
    RISK_WEIGHT_STATIC,
    RISK_WEIGHT_COVERAGE,
    RISK_WEIGHT_STYLE,
    COMPLEXITY_MODERATE_MAX,
    COMPLEXITY_HIGH_MAX,
)


def predict(
    complexity_data: Dict,
    security_findings: List[Dict],
    static_findings: List[Dict],
    coverage_metrics: Dict,
    style_findings: List[Dict],
) -> Dict:
    """
    Compute a defect risk score (0–100) and category.

    Returns a dict with: score, category, components, high_risk_functions,
    recommendations, methodology_note.
    """
    # --- Component scores (each 0–100) ---

    # 1. Complexity score
    complexity_score = _complexity_score(complexity_data)

    # 2. Security score
    security_score = _security_score(security_findings)

    # 3. Static analysis score
    static_score = _static_score(static_findings)

    # 4. Coverage score (inverted: low coverage = high risk)
    coverage_score = _coverage_score(coverage_metrics)

    # 5. Style score
    style_score = _style_score(style_findings)

    # --- Weighted aggregate ---
    total_score = (
        complexity_score * RISK_WEIGHT_COMPLEXITY
        + security_score * RISK_WEIGHT_SECURITY
        + static_score * RISK_WEIGHT_STATIC
        + coverage_score * RISK_WEIGHT_COVERAGE
        + style_score * RISK_WEIGHT_STYLE
    )
    total_score = round(min(100, max(0, total_score)), 1)

    # Risk category
    if total_score < 25:
        category = "LOW"
    elif total_score < 50:
        category = "MODERATE"
    elif total_score < 75:
        category = "HIGH"
    else:
        category = "CRITICAL"

    # High-risk functions
    high_risk_functions = _identify_high_risk_functions(complexity_data)

    # Recommendations
    recommendations = _generate_recommendations(
        total_score, category, complexity_score, security_score,
        static_score, coverage_score, style_score, security_findings,
    )

    return {
        "score": total_score,
        "category": category,
        "components": {
            "complexity": {
                "score": round(complexity_score, 1),
                "weight": RISK_WEIGHT_COMPLEXITY,
                "contribution": round(complexity_score * RISK_WEIGHT_COMPLEXITY, 1),
            },
            "security": {
                "score": round(security_score, 1),
                "weight": RISK_WEIGHT_SECURITY,
                "contribution": round(security_score * RISK_WEIGHT_SECURITY, 1),
            },
            "static_analysis": {
                "score": round(static_score, 1),
                "weight": RISK_WEIGHT_STATIC,
                "contribution": round(static_score * RISK_WEIGHT_STATIC, 1),
            },
            "coverage": {
                "score": round(coverage_score, 1),
                "weight": RISK_WEIGHT_COVERAGE,
                "contribution": round(coverage_score * RISK_WEIGHT_COVERAGE, 1),
            },
            "style": {
                "score": round(style_score, 1),
                "weight": RISK_WEIGHT_STYLE,
                "contribution": round(style_score * RISK_WEIGHT_STYLE, 1),
            },
        },
        "high_risk_functions": high_risk_functions,
        "recommendations": recommendations,
        "methodology_note": (
            "This score is a HEURISTIC estimate, not a machine-learning probability. "
            "It is computed from weighted contributions of cyclomatic complexity (25%), "
            "security findings (30%), static analysis findings (20%), "
            "code coverage deficit (15%), and style violations (10%). "
            "Use this score as a starting point for code review prioritisation, "
            "not as a definitive defect count."
        ),
    }


def _complexity_score(data: Dict) -> float:
    """Higher complexity → higher risk score."""
    overall = data.get("overall", {})
    avg_complexity = overall.get("average", 0)
    dist = overall.get("distribution", {})

    # Base score from average complexity
    if avg_complexity <= 5:
        base = avg_complexity * 4
    elif avg_complexity <= 12:
        base = 20 + (avg_complexity - 5) * 7
    elif avg_complexity <= 25:
        base = 69 + (avg_complexity - 12) * 2
    else:
        base = 95

    # Bonus for critical functions
    critical_count = dist.get("CRITICAL", 0)
    high_count = dist.get("HIGH", 0)
    base = min(100, base + critical_count * 10 + high_count * 5)
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
    return min(100, score)


def _static_score(findings: List[Dict]) -> float:
    """More static analysis findings → higher risk."""
    if not findings:
        return 0.0
    count = len(findings)
    if count <= 2:
        return count * 10
    elif count <= 10:
        return 20 + (count - 2) * 7
    else:
        return min(100, 76 + (count - 10) * 2)


def _coverage_score(metrics: Dict) -> float:
    """Low coverage = high risk. 100% coverage → 0 risk score."""
    stmt_cov = metrics.get("statement_coverage", 0)
    branch_cov = metrics.get("branch_coverage", 0)
    # Average the two; invert
    avg_cov = (stmt_cov + branch_cov) / 2
    return max(0, 100 - avg_cov)


def _style_score(findings: List[Dict]) -> float:
    """Style violations contribute a small risk component."""
    count = len(findings)
    if count == 0:
        return 0.0
    return min(100, count * 3)


def _identify_high_risk_functions(data: Dict) -> List[Dict]:
    functions = data.get("functions", [])
    high_risk = [
        f for f in functions
        if f.get("risk") in ("HIGH", "CRITICAL")
    ]
    return sorted(high_risk, key=lambda f: f.get("complexity", 0), reverse=True)


def _generate_recommendations(
    score, category, complexity_score, security_score,
    static_score, coverage_score, style_score, security_findings,
) -> List[str]:
    recs = []

    if security_score > 50:
        recs.append(
            "⚠️ HIGH SECURITY RISK: Address Bandit security findings immediately. "
            "Security vulnerabilities are weighted most heavily in the risk score."
        )
    if complexity_score > 60:
        recs.append(
            "🔀 HIGH COMPLEXITY: Refactor functions with complexity > 12. "
            "High cyclomatic complexity directly increases the probability of latent defects."
        )
    if coverage_score > 60:
        recs.append(
            "📊 LOW COVERAGE: Increase test coverage. "
            "Uncovered code paths are breeding grounds for undetected bugs."
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
