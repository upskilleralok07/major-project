"""MediVault - Medical Report Management (Flask + SQLite).

Run:   python app.py
Reset: python app.py --reset-db
"""
import hmac
import os
import secrets
import shutil
import sys
from datetime import datetime, timedelta

from flask import Flask, g, jsonify, render_template, request, session, redirect, url_for
from werkzeug.exceptions import HTTPException

from config import Config
from models import close_db, init_schema, query, activity as activity_model, user as user_model
from utils.auth import AppError, wants_json


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.teardown_appcontext(close_db)

    from routes.auth import bp as auth_bp
    from routes.patient import bp as patient_bp
    from routes.doctor import bp as doctor_bp
    from routes.admin import bp as admin_bp
    for bp in (auth_bp, patient_bp, doctor_bp, admin_bp):
        app.register_blueprint(bp)

    # ---------------------------------------------------- request lifecycle
    @app.before_request
    def load_user_and_check_csrf():
        # 1. session validation: the user must still exist and be active
        g.user = None
        uid = session.get("user_id")
        if uid:
            user = user_model.get_by_id(uid)
            if user and user["is_active"]:
                g.user = user
            else:
                session.clear()
        # 2. CSRF protection for every state-changing request
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            expected = session.get("_csrf", "")
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            if not expected or not hmac.compare_digest(expected, sent):
                raise AppError(400, "Your session expired or the form was invalid. Please refresh the page and try again.")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if g.get("user"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    # ------------------------------------------------- template helpers
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    @app.context_processor
    def inject_globals():
        notifications, has_new = [], False
        user = g.get("user")
        if user:
            notifications = activity_model.for_user(user["id"], 5)
            cutoff = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            has_new = any(n["created_at"] >= cutoff for n in notifications)
        return dict(current_user=user, csrf_token=csrf_token, notifications=notifications,
                    has_new_notifications=has_new, max_file_mb=app.config["MAX_FILE_MB"])

    @app.template_filter("fmt_date")
    def fmt_date(value):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y")
        except (TypeError, ValueError):
            return value or "-"

    @app.template_filter("fmt_datetime")
    def fmt_datetime(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
        except (TypeError, ValueError):
            return value or "-"

    @app.template_filter("filesize")
    def filesize(n):
        n = float(n or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024

    @app.template_filter("initials")
    def initials(name):
        parts = [p for p in (name or "?").replace("Dr.", "").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    # ----------------------------------------------------- error pages
    def show_error(code, title, message):
        if wants_json() or request.path == "/reports/search":
            return jsonify(ok=False, message=message), code
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(AppError)
    def handle_app_error(e):
        titles = {400: "Something went wrong", 403: "Access denied", 404: "Not found"}
        return show_error(e.code, titles.get(e.code, "Error"), e.message)

    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        msgs = {
            400: ("Bad request", "The request could not be understood. Please try again."),
            403: ("Access denied", "You are not authorized to access this page."),
            404: ("Page not found", "The page you are looking for does not exist."),
            405: ("Method not allowed", "This action is not allowed here."),
            413: ("File too large", f"File size exceeds the allowed limit of {app.config['MAX_FILE_MB']} MB."),
        }
        title, msg = msgs.get(e.code, ("Error", e.description))
        return show_error(e.code, title, msg)

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        app.logger.exception(e)
        return show_error(500, "Something went wrong", "Unexpected server error. Please try again.")

    # ------------------------------------------------- first-run database
    if not os.path.exists(app.config["DATABASE"]):
        init_database(app)
    return app


def init_database(app, reset=False):
    """Create tables, default categories and the demo accounts."""
    from utils.demo_data import seed_demo
    if reset:
        if os.path.exists(app.config["DATABASE"]):
            os.remove(app.config["DATABASE"])
        shutil.rmtree(app.config["UPLOAD_FOLDER"], ignore_errors=True)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    with app.app_context():
        init_schema()
        seed_demo()
    print("Database ready:", app.config["DATABASE"])


if __name__ == "__main__":
    application = create_app()
    if "--reset-db" in sys.argv:
        init_database(application, reset=True)
        sys.exit(0)
    if "--init-db" in sys.argv:
        init_database(application)
        sys.exit(0)
    application.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", host="127.0.0.1", port=5000)
