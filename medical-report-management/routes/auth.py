"""Landing page, register, login, logout."""
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g

from models import user as user_model, patient as patient_model, doctor as doctor_model
from utils.activity_logger import log_activity
from utils.auth import home_for

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")


def password_problem(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


@bp.route("/")
def index():
    if g.user:
        return redirect(home_for(g.user["role"]))
    return render_template("landing.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(home_for(g.user["role"]))
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        phone = form.get("phone", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")
        role = form.get("role", "patient")
        specialization = form.get("specialization", "").strip()

        if len(name) < 2:
            errors["name"] = "Please enter your full name."
        if not EMAIL_RE.match(email):
            errors["email"] = "Please enter a valid email address."
        elif user_model.get_by_email(email):
            errors["email"] = "An account with this email already exists."
        if not PHONE_RE.match(phone):
            errors["phone"] = "Please enter a valid phone number."
        problem = password_problem(password)
        if problem:
            errors["password"] = problem
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if role not in ("patient", "doctor"):   # admin accounts can never be self-registered
            errors["role"] = "Please choose a valid role."

        if not errors:
            uid = user_model.create_user(name, email, phone, password, role)
            if role == "patient":
                patient_model.create(uid)
            else:
                doctor_model.create(uid, specialization)
            log_activity("Registered", f"New {role} account created", user_id=uid)
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", errors=errors, form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(home_for(g.user["role"]))
    error, email = None, ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = user_model.get_by_email(email) if email else None
        if not user or not user_model.check_password(user, password):
            error = "Invalid email or password."
        elif not user["is_active"]:
            error = "Your account has been deactivated. Please contact the administrator."
        else:
            session.clear()                       # new session = protection against session fixation
            session["user_id"] = user["id"]
            session.permanent = bool(request.form.get("remember"))
            log_activity("Login", "Logged in", user_id=user["id"])
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//") and nxt not in ("/login", "/register"):
                return redirect(nxt)
            return redirect(home_for(user["role"]))
    return render_template("login.html", error=error, email=email)


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "POST" and g.user:
        log_activity("Logout", "Logged out")
        session.clear()
        flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
