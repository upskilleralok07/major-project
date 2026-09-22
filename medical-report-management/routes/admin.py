"""Admin area: users, categories, statistics and system logs."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from models import (user as user_model, report as report_model, activity as activity_model, patient as patient_model,
                    doctor as doctor_model, query)
from utils.activity_logger import log_activity
from utils.auth import role_required, AppError

bp = Blueprint("admin", __name__, url_prefix="/admin")
admin_only = role_required("admin")

ICONS = ["droplet", "image", "layers", "activity", "pill", "clipboard", "file", "heart"]


@bp.route("/dashboard")
@admin_only
def dashboard():
    roles = user_model.count_by_role()
    totals = report_model.totals()
    stats = {
        "users": sum(roles.values()), "patients": roles.get("patient", 0), "doctors": roles.get("doctor", 0),
        "reports": totals["reports"], "shares": totals["shares"],
    }
    usage = report_model.category_usage()
    top = max([c["report_count"] for c in usage] + [1])
    return render_template("admin/dashboard.html", stats=stats, usage=usage, top=top,
                           logs=activity_model.search_all(limit=8))


@bp.route("/users")
@admin_only
def users():
    q, role, status = request.args.get("q", "").strip(), request.args.get("role", ""), request.args.get("status", "")
    return render_template("admin/users.html", users=user_model.list_users(q, role, status), q=q, role=role, status=status)


@bp.route("/users/<int:user_id>")
@admin_only
def user_detail(user_id):
    user = user_model.get_by_id(user_id)
    if not user:
        raise AppError(404, "User not found.")
    pat = patient_model.get_by_user(user_id) if user["role"] == "patient" else None
    doc = doctor_model.get_by_user(user_id) if user["role"] == "doctor" else None
    report_count = share_count = 0
    if pat:
        report_count = report_model.stats(pat["id"])["total"]
        share_count = len(report_model.shares_for_patient(pat["id"]))
    if doc:
        share_count = len(report_model.shares_for_doctor(doc["id"]))
    return render_template("admin/user_detail.html", u=user, pat=pat, doc=doc, report_count=report_count,
                           share_count=share_count, logs=activity_model.for_target_user(user_id, 15))


@bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_only
def user_status(user_id):
    user = user_model.get_by_id(user_id)
    if not user:
        raise AppError(404, "User not found.")
    if user["id"] == g.user["id"]:
        flash("You cannot deactivate your own account.", "error")
    else:
        new_state = not user["is_active"]
        user_model.set_active(user_id, new_state)
        word = "activated" if new_state else "deactivated"
        log_activity("User " + word, f"{user['name']} ({user['email']}) was {word}", target_user_id=user_id)
        flash(f"{user['name']} has been {word}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/categories", methods=["GET", "POST"])
@admin_only
def categories():
    if request.method == "POST":
        action = request.form.get("action", "")
        name = request.form.get("name", "").strip()
        cat_id = request.form.get("category_id", type=int)
        existing = query("SELECT id FROM report_categories WHERE LOWER(name) = LOWER(?)", (name,), one=True)
        if action == "add":
            icon = request.form.get("icon", "file")
            if not name or len(name) > 40:
                flash("Category name is required (max 40 characters).", "error")
            elif existing:
                flash("That category already exists.", "error")
            else:
                report_model.add_category(name, icon if icon in ICONS else "file")
                log_activity("Category added", f"Added category '{name}'")
                flash("Category added.", "success")
        elif action == "rename":
            if not name or len(name) > 40 or (existing and existing["id"] != cat_id):
                flash("Please enter a unique category name.", "error")
            elif report_model.get_category(cat_id):
                report_model.rename_category(cat_id, name)
                log_activity("Category renamed", f"Renamed category to '{name}'")
                flash("Category renamed.", "success")
        elif action == "delete":
            cat = report_model.get_category(cat_id)
            used = query("SELECT COUNT(*) AS n FROM reports WHERE category_id = ?", (cat_id,), one=True)["n"] if cat else 0
            if not cat:
                flash("Category not found.", "error")
            elif cat["name"] == "Other":
                flash("The 'Other' category cannot be deleted.", "error")
            elif used:
                flash(f"Cannot delete '{cat['name']}' because {used} report(s) use it.", "error")
            else:
                report_model.delete_category(cat_id)
                log_activity("Category deleted", f"Deleted category '{cat['name']}'")
                flash("Category deleted.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html", categories=report_model.category_usage(), icons=ICONS)


@bp.route("/activity")
@admin_only
def activity():
    q, action = request.args.get("q", "").strip(), request.args.get("action", "")
    return render_template("admin/activities.html", logs=activity_model.search_all(q, action),
                           actions=activity_model.distinct_actions(), q=q, action=action)
