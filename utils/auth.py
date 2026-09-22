from functools import wraps

from flask import g, redirect, url_for, flash, request, jsonify, abort

from models import patient as patient_model, doctor as doctor_model


def wants_json():
    return (request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.accept_mimetypes.best == "application/json")


def home_for(role):
    return {"patient": "/dashboard", "doctor": "/doctor/dashboard", "admin": "/admin/dashboard"}.get(role, "/login")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if wants_json():
                return jsonify(ok=False, message="Please log in to continue."), 401
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Only allow the given roles. Also loads g.patient / g.doctor for convenience."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                abort(403)
            if g.user["role"] == "patient":
                g.patient = patient_model.get_by_user(g.user["id"])
            elif g.user["role"] == "doctor":
                g.doctor = doctor_model.get_by_user(g.user["id"])
            return view(*args, **kwargs)
        return wrapped
    return decorator


class AppError(Exception):
    """Raise this to show a friendly error page (or JSON for fetch requests)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message
