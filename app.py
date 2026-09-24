from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for

import config
from src.pdf_generator import PdfGenerator


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=config.LOGS_DIR / "error.log", level=logging.ERROR, format="%(asctime)s %(levelname)s %(message)s")
    generator = PdfGenerator(config)

    def schedule_output_deletion(path: Path) -> None:
        try:
            created_at = path.stat().st_mtime_ns
        except OSError:
            return

        def delete_if_unchanged() -> None:
            try:
                if path.is_file() and path.stat().st_mtime_ns == created_at:
                    path.unlink()
            except OSError:
                logging.getLogger(__name__).warning("Could not remove temporary generated file: %s", path.name)

        timer = threading.Timer(config.OUTPUT_DELETE_AFTER_SECONDS, delete_if_unchanged)
        timer.daemon = True
        timer.start()

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/")
    def index():
        csrf_token = session.setdefault("csrf_token", secrets.token_urlsafe(32))
        return render_template("index.html", csrf_token=csrf_token, student_name="", register_number="")

    @app.post("/generate")
    def generate():
        submitted_token = request.form.get("csrf_token", "")
        stored_token = session.get("csrf_token", "")
        if not stored_token or not submitted_token or not secrets.compare_digest(submitted_token, stored_token):
            abort(400, description="Invalid request.")

        student_name = request.form.get("student_name", "").strip()
        register_number = request.form.get("register_number", "").strip()
        errors = []
        if not student_name or len(student_name) > config.MAX_NAME_LENGTH:
            errors.append("Student Name is required and must be 100 characters or fewer.")
        if not register_number or len(register_number) > config.MAX_REGISTER_LENGTH:
            errors.append("Register Number is required and must be 50 characters or fewer.")
        if errors:
            for error in errors:
                flash(error, "alert")
            return render_template("index.html", csrf_token=stored_token, student_name=student_name, register_number=register_number), 400

        try:
            generated = generator.generate(student_name, register_number)
        except RuntimeError as error:
            logging.getLogger(__name__).exception("PDF generation failed")
            flash(str(error), "alert")
            return render_template("index.html", csrf_token=stored_token, student_name=student_name, register_number=register_number), 500
        schedule_output_deletion(generated)
        return redirect(url_for("download", filename=generated.name))

    @app.get("/download/<path:filename>")
    def download(filename: str):
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".pdf"):
            abort(404)
        output_path = config.OUTPUT_DIR / safe_name
        if not output_path.is_file():
            abort(404)
        return send_from_directory(config.OUTPUT_DIR, safe_name, as_attachment=True, mimetype="application/pdf")

    @app.errorhandler(413)
    def request_too_large(_error):
        return "Request too large.", 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
