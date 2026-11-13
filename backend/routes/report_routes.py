"""
Report Routes — download JSON and HTML reports.
"""
from flask import Blueprint, request, jsonify, Response

from backend.services.analysis_service import get_result
from backend.services.report_service import generate_json_report, generate_html_report

report_bp = Blueprint("report", __name__, url_prefix="/api/report")


@report_bp.route("/<analysis_id>", methods=["GET"])
def download_report(analysis_id: str):
    """
    Generate a downloadable report.

    Query params:
      format=json  (default)
      format=html
    """
    result = get_result(analysis_id)
    if result is None:
        return jsonify({"error": "Result not found or expired"}), 404

    fmt = request.args.get("format", "json").lower()

    if fmt == "html":
        html = generate_html_report(result)
        filename = f"report_{analysis_id[:8]}.html"
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        json_str = generate_json_report(result)
        filename = f"report_{analysis_id[:8]}.json"
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
