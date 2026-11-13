"""
Analysis Routes — REST API endpoints for code analysis.
"""
import os
from flask import Blueprint, request, jsonify, current_app

from backend.services import analysis_service
from backend.utils.validators import validate_source_code, validate_filename
from config import SAMPLE_NAMES, SECURITY_WARNING

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")

# Max upload size (enforced at Flask level too)
MAX_UPLOAD_BYTES = 100_000


@analysis_bp.route("/health", methods=["GET"])
def health_check():
    """Application health check."""
    return jsonify({"status": "ok", "message": "Complex Code Testing Dashboard is running"})


@analysis_bp.route("/analyze", methods=["POST"])
def analyze_code():
    """
    Analyse submitted Python source code.

    Accepts JSON: { "code": "...", "filename": "optional.py" }
    Returns full analysis result.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    code = data.get("code", "")
    filename = data.get("filename", "user_code.py") or "user_code.py"

    # Sanitise filename
    is_valid_name, name_reason = validate_filename(os.path.basename(filename))
    if not is_valid_name:
        filename = "user_code.py"

    # Validate source
    is_valid, errors = validate_source_code(code)
    if not is_valid:
        return jsonify({
            "error": "Source code validation failed",
            "validation_errors": errors,
        }), 422

    try:
        result = analysis_service.run_analysis(code, filename)
        return jsonify(result)
    except Exception as exc:
        current_app.logger.error("Analysis error: %s", exc, exc_info=True)
        return jsonify({"error": "Internal analysis error", "details": str(exc)}), 500


@analysis_bp.route("/analyze/upload", methods=["POST"])
def analyze_upload():
    """
    Analyse an uploaded .py file.

    Accepts multipart/form-data with field 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "No file selected"}), 400

    # Validate filename
    is_valid_name, name_reason = validate_filename(uploaded.filename)
    if not is_valid_name:
        return jsonify({"error": f"Invalid filename: {name_reason}"}), 400

    raw_bytes = uploaded.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        return jsonify({"error": f"File exceeds maximum size of {MAX_UPLOAD_BYTES // 1024} KB"}), 413

    try:
        code = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "File must be UTF-8 encoded Python source"}), 400

    is_valid, errors = validate_source_code(code)
    if not is_valid:
        return jsonify({
            "error": "Source code validation failed",
            "validation_errors": errors,
        }), 422

    try:
        result = analysis_service.run_analysis(code, uploaded.filename)
        return jsonify(result)
    except Exception as exc:
        current_app.logger.error("Upload analysis error: %s", exc, exc_info=True)
        return jsonify({"error": "Internal analysis error", "details": str(exc)}), 500


@analysis_bp.route("/results/<analysis_id>", methods=["GET"])
def get_results(analysis_id: str):
    """Retrieve a previous analysis result by ID."""
    result = analysis_service.get_result(analysis_id)
    if result is None:
        return jsonify({"error": "Result not found or expired"}), 404
    return jsonify(result)


@analysis_bp.route("/samples", methods=["GET"])
def get_samples():
    """Return available sample program names and their source code."""
    samples_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "samples",
    )
    samples = {}
    for name in SAMPLE_NAMES:
        path = os.path.join(samples_dir, f"{name}.py")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                samples[name] = {
                    "name": name.replace("_", " ").title(),
                    "filename": f"{name}.py",
                    "code": f.read(),
                }
    return jsonify({"samples": samples, "security_note": SECURITY_WARNING})
