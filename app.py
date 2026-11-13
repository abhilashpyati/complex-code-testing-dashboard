"""
Flask Application Entry Point.
Complex Code Testing Dashboard — Software Testing Academic Project.
"""
import os
from flask import Flask, render_template, jsonify

from config import SECRET_KEY, DEBUG
from backend.routes.analysis_routes import analysis_bp
from backend.routes.report_routes import report_bp


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024  # 100 KB

    # Register blueprints
    app.register_blueprint(analysis_bp)
    app.register_blueprint(report_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large (max 100 KB)"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
