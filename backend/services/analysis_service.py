"""
Analysis Service — orchestrates all analysis tools.
Maintains an in-memory store of recent analysis results.
"""
import uuid
import threading
import time
import os
from datetime import datetime
from typing import Dict, Optional

from backend.services.execution_service import create_workspace, cleanup_workspace
from backend.analyzers import (
    pytest_analyzer,
    coverage_analyzer,
    flake8_analyzer,
    pylint_analyzer,
    bandit_analyzer,
    pycodestyle_analyzer,
)
from backend.complexity.complexity_analyzer import analyze as analyze_complexity
from backend.prediction.defect_predictor import predict as predict_defects
from backend.utils.result_formatter import summarise_criteria, calculate_health_score
from config import RESULT_TTL_SECONDS

# In-memory result store: {analysis_id: {data, timestamp}}
_results: Dict[str, Dict] = {}
_results_lock = threading.Lock()


def _store_result(analysis_id: str, data: Dict) -> None:
    with _results_lock:
        _purge_expired()
        _results[analysis_id] = {
            "data": data,
            "timestamp": time.time(),
        }


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _results.items() if now - v["timestamp"] > RESULT_TTL_SECONDS]
    for k in expired:
        del _results[k]


def get_result(analysis_id: str) -> Optional[Dict]:
    with _results_lock:
        entry = _results.get(analysis_id)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > RESULT_TTL_SECONDS:
            del _results[analysis_id]
            return None
        return entry["data"]


def run_analysis(code: str, filename: str = "user_code.py") -> Dict:
    """
    Execute all analysis tools against submitted source code.
    Returns a complete analysis result dict.
    """
    analysis_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    workspace_dir, code_path = create_workspace(code, filename)

    try:
        result = _execute_analysis(analysis_id, timestamp, code, code_path, workspace_dir, filename)
    finally:
        cleanup_workspace(workspace_dir)

    _store_result(analysis_id, result)
    return result


def _execute_analysis(
    analysis_id: str,
    timestamp: str,
    code: str,
    code_path: str,
    workspace_dir: str,
    filename: str,
) -> Dict:
    # --- Run all analyzers ---
    pytest_result = pytest_analyzer.analyze(workspace_dir, code_path, code)
    coverage_result = coverage_analyzer.analyze(workspace_dir, code_path, code)
    flake8_result = flake8_analyzer.analyze(workspace_dir, code_path, code)
    pylint_result = pylint_analyzer.analyze(workspace_dir, code_path, code)
    bandit_result = bandit_analyzer.analyze(workspace_dir, code_path, code)
    pycodestyle_result = pycodestyle_analyzer.analyze(workspace_dir, code_path, code)
    complexity_result = analyze_complexity(workspace_dir, code_path, code)

    # --- Collect all 25 criteria ---
    all_criteria = (
        pytest_result["criteria"]          # 5
        + coverage_result["criteria"]      # 5
        + flake8_result["criteria"]        # 5
        + pylint_result["criteria"]        # 5
        + bandit_result["criteria"]        # 5
    )

    # --- Defect prediction ---
    all_static = flake8_result.get("findings", []) + pylint_result.get("findings", [])
    all_style = pycodestyle_result.get("findings", [])
    prediction = predict_defects(
        complexity_data=complexity_result,
        security_findings=bandit_result.get("findings", []),
        static_findings=all_static,
        coverage_metrics=coverage_result.get("metrics", {}),
        style_findings=all_style,
    )

    # --- Summary counts ---
    summary = summarise_criteria(all_criteria)
    health_score = calculate_health_score(
        summary.get("PASSED", 0),
        summary.get("WARNING", 0),
        summary.get("FAILED", 0),
        summary.get("NOT_EXECUTED", 0),
        len(all_criteria),
        not_applicable=summary.get("NOT_APPLICABLE", 0),
    )

    return {
        "analysis_id": analysis_id,
        "timestamp": timestamp,
        "filename": filename,
        "code_lines": len(code.splitlines()),
        "code_chars": len(code),

        # 25 criteria
        "criteria": {
            "pytest": pytest_result["criteria"],
            "coverage": coverage_result["criteria"],
            "flake8": flake8_result["criteria"],
            "pylint": pylint_result["criteria"],
            "bandit": bandit_result["criteria"],
        },
        "all_criteria": all_criteria,

        # Metrics
        "coverage_metrics": coverage_result.get("metrics", {}),
        "complexity": complexity_result,
        "defect_prediction": prediction,

        # Raw findings for display
        "findings": {
            "flake8": flake8_result.get("findings", []),
            "pylint": pylint_result.get("findings", []),
            "bandit": bandit_result.get("findings", []),
            "pycodestyle": pycodestyle_result.get("findings", []),
        },

        # Pycodestyle criteria (for reference but not in core 25)
        "pycodestyle_criteria": pycodestyle_result.get("criteria", []),

        # Test metadata
        "pytest_meta": {
            "summary": pytest_result.get("summary", {}),
            "defs": pytest_result.get("defs", {}),
        },
        "pylint_score": pylint_result.get("score", -1),

        # Dashboard summary
        "summary": summary,
        "health_score": health_score,
    }
