"""Everything a patient can do (plus profile & settings for every role)."""
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, send_file)

from models import (patient as patient_model, doctor as doctor_model, report as report_model,
                    activity as activity_model, user as user_model)
from routes.auth import password_problem, PHONE_RE
from utils import file_handler
from utils.activity_logger import log_activity
from utils.auth import login_required, role_required, AppError, wants_json

bp = Blueprint("patient", __name__)
patient_only = role_required("patient")


# ------------------------------------------------------------------ helpers

def owned_report(report_id):
    """Load a report and make sure it belongs to the logged-in patient."""
    report = report_model.get(report_id)
    if report is None:
        raise AppError(404, "Report not found.")
    if report["patient_id"] != g.patient["id"]:
        raise AppError(403, "You are not authorized to access this report.")
    return report


def parse_report_form(form):
    """Validate the report fields shared by upload and edit. Returns (values, errors)."""
    errors = {}
    title = form.get("title", "").strip()
    if not title:
        errors["title"] = "Report title is required."
    elif len(title) > 150:
        errors["title"] = "Title is too long (max 150 characters)."
    category = report_model.get_category(form.get("category_id", type=int)) if form.get("category_id") else None
    if not category:
        errors["category_id"] = "Please select a category."
    date_text = form.get("report_date", "").strip()
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d")
        if d.date() > datetime.now().date():
            errors["report_date"] = "Report date cannot be in the future."
    except ValueError:
        errors["report_date"] = "Please enter a valid report date."
    values = {
        "title": title,
        "category_id": category["id"] if category else None,
        "hospital": form.get("hospital_name", "").strip()[:120],
        "lab": form.get("laboratory_name", "").strip()[:120],
        "doctor": form.get("doctor_name", "").strip()[:120],
        "department": form.get("department", "").strip()[:120],
        "report_date": date_text,
        "notes": form.get("notes", "").strip()[:2000],
        "is_important": 1 if form.get("is_important") in ("1", "on", "true") else 0,
    }
    return values, errors


def report_to_dict(r):
    return {
        "id": r["id"], "title": r["title"], "category_id": r["category_id"], "category": r["category_name"],
        "category_icon": r["category_icon"], "hospital": r["hospital_name"] or "", "laboratory": r["laboratory_name"] or "",
        "doctor": r["doctor_name"] or "", "department": r["department"] or "", "date": r["report_date"],
        "important": bool(r["is_important"]), "file_type": r["file_type"], "file_size": r["file_size"],
        "file_name": r["file_name"],
        "urls": {
            "view": url_for("patient.report_details", report_id=r["id"]),
            "preview": url_for("patient.preview_report", report_id=r["id"]),
            "download": url_for("patient.download_report", report_id=r["id"]),
            "share": url_for("patient.share_report", report_id=r["id"]),
            "important": url_for("patient.toggle_important", report_id=r["id"]),
        },
    }


# ---------------------------------------------------------------- dashboard

@bp.route("/dashboard")
@patient_only
def dashboard():
    pid = g.patient["id"]
    shares = report_model.shares_for_patient(pid)
    return render_template(
        "dashboard.html",
        stats=report_model.stats(pid),
        recent=report_model.search(pid, sort="uploaded", limit=5),
        important=report_model.search(pid, important=True, limit=4),
        activities=activity_model.for_user(g.user["id"], 6),
        active_shares=sum(1 for s in shares if s["effective_status"] == "active"),
        chart_data={"categories": report_model.by_category(pid), "months": report_model.by_month(pid)},
    )


# ----------------------------------------------------------------- profile

@bp.route("/profile")
@login_required
def profile():
    pat = patient_model.get_by_user(g.user["id"]) if g.user["role"] == "patient" else None
    doc = doctor_model.get_by_user(g.user["id"]) if g.user["role"] == "doctor" else None
    return render_template("profile.html", pat=pat, doc=doc, editing=False, errors={})


@bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    role = g.user["role"]
    pat = patient_model.get_by_user(g.user["id"]) if role == "patient" else None
    doc = doctor_model.get_by_user(g.user["id"]) if role == "doctor" else None
    errors = {}
    if request.method == "POST":
        f = request.form
        name, phone = f.get("name", "").strip(), f.get("phone", "").strip()
        if len(name) < 2:
            errors["name"] = "Please enter your full name."
        if not PHONE_RE.match(phone):
            errors["phone"] = "Please enter a valid phone number."
        age = None
        if pat is not None:
            if f.get("age", "").strip():
                try:
                    age = int(f.get("age"))
                    if not 0 <= age <= 130:
                        raise ValueError
                except ValueError:
                    errors["age"] = "Age must be a number between 0 and 130."
            if f.get("gender", "") not in ("", "Male", "Female", "Other"):
                errors["gender"] = "Please choose a valid gender."
        if not errors:
            user_model.update_basic(g.user["id"], name, phone)
            if pat is not None:
                patient_model.update(pat["id"], age, f.get("gender", ""), f.get("address", "").strip()[:300],
                                     f.get("emergency_contact", "").strip()[:150], f.get("medical_info", "").strip()[:1000])
            if doc is not None:
                doctor_model.update(doc["id"], f.get("specialization", "").strip()[:100], f.get("hospital", "").strip()[:120])
            flash("Profile updated successfully.", "success")
            return redirect(url_for("patient.profile"))
        # show what the user typed again
        g.user = dict(g.user, name=name, phone=phone)
        if pat is not None:
            pat = dict(pat, age=f.get("age"), gender=f.get("gender"), address=f.get("address"),
                       emergency_contact=f.get("emergency_contact"), medical_info=f.get("medical_info"))
    return render_template("profile.html", pat=pat, doc=doc, editing=True, errors=errors)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    error = None
    if request.method == "POST":
        current, new, confirm = (request.form.get(k, "") for k in ("current_password", "new_password", "confirm_password"))
        if not user_model.check_password(g.user, current):
            error = "Your current password is incorrect."
        elif password_problem(new):
            error = password_problem(new)
        elif new != confirm:
            error = "New passwords do not match."
        else:
            user_model.change_password(g.user["id"], new)
            log_activity("Password changed", "Password updated")
            flash("Password changed successfully.", "success")
            return redirect(url_for("patient.settings"))
    return render_template("settings.html", error=error)


# ------------------------------------------------------------ report lists

@bp.route("/reports")
@patient_only
def reports():
    return render_template("reports.html", categories=report_model.categories(), important_only=False)


@bp.route("/important")
@patient_only
def important_reports():
    return render_template("important.html", categories=report_model.categories(), important_only=True)


@bp.route("/reports/search")
@patient_only
def search_reports():
    a = request.args
    rows = report_model.search(
        g.patient["id"], q=a.get("q", "").strip(), category=a.get("category", ""), hospital=a.get("hospital", ""),
        doctor=a.get("doctor", ""), date_from=a.get("date_from", ""), date_to=a.get("date_to", ""),
        important=a.get("important") == "1", sort=a.get("sort", "newest"))
    hospitals, doctors = report_model.filter_options(g.patient["id"])
    return jsonify(ok=True, count=len(rows), reports=[report_to_dict(r) for r in rows],
                   hospitals=hospitals, doctors=doctors)


# ------------------------------------------------------------------ upload

@bp.route("/reports/upload", methods=["GET", "POST"])
@patient_only
def upload_report():
    if request.method == "GET":
        return render_template("upload_report.html", categories=report_model.categories(),
                               today=datetime.now().strftime("%Y-%m-%d"))
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify(ok=False, message="Please choose a file to upload."), 400
    values, errors = parse_report_form(request.form)
    if errors:
        return jsonify(ok=False, message=next(iter(errors.values())), errors=errors), 400
    ok, message, info = file_handler.validate_upload(file, current_app_max_mb())
    if not ok:
        return jsonify(ok=False, message=message), 400

    pid = g.patient["id"]
    existing = report_model.find_by_hash(pid, info["hash"])
    if existing and request.form.get("allow_duplicate") != "1":
        return jsonify(ok=False, duplicate=True, message="Possible duplicate report found.",
                       existing={"id": existing["id"], "title": existing["title"],
                                 "date": existing["report_date"],
                                 "url": url_for("patient.report_details", report_id=existing["id"])}), 409
    try:
        stored = file_handler.save_file(pid, info["data"], info["ext"])
        rid = report_model.create(
            pid, values["category_id"], values["title"], values["hospital"], values["lab"], values["doctor"],
            values["department"], values["report_date"], values["notes"], values["is_important"],
            info["original_name"], stored, info["ext"], info["size"], info["hash"])
    except Exception:
        return jsonify(ok=False, message="Unable to upload report. Please try again."), 500
    log_activity("Report uploaded", f"Uploaded '{values['title']}'", report_id=rid)
    flash("Report uploaded successfully.", "success")
    return jsonify(ok=True, message="Report uploaded successfully.",
                   redirect=url_for("patient.report_details", report_id=rid))


def current_app_max_mb():
    from flask import current_app
    return current_app.config["MAX_FILE_MB"]


# ----------------------------------------------------------- single report

@bp.route("/reports/<int:report_id>")
@patient_only
def report_details(report_id):
    report = owned_report(report_id)
    log_activity("Report viewed", f"Viewed '{report['title']}'", report_id=report_id)
    return render_template("report_details.html", report=report, shares=report_model.shares_for_report(report_id))


@bp.route("/reports/<int:report_id>/edit", methods=["GET", "POST"])
@patient_only
def edit_report(report_id):
    report = dict(owned_report(report_id))
    errors = {}
    if request.method == "POST":
        values, errors = parse_report_form(request.form)
        if not errors:
            report_model.update(report_id, values["category_id"], values["title"], values["hospital"], values["lab"],
                                values["doctor"], values["department"], values["report_date"], values["notes"],
                                values["is_important"])
            log_activity("Report edited", f"Edited '{values['title']}'", report_id=report_id)
            flash("Report updated successfully.", "success")
            return redirect(url_for("patient.report_details", report_id=report_id))
        report = dict(report, title=values["title"], category_id=values["category_id"] or report["category_id"],
                      hospital_name=values["hospital"], laboratory_name=values["lab"], doctor_name=values["doctor"],
                      department=values["department"], report_date=values["report_date"], notes=values["notes"],
                      is_important=values["is_important"])
    return render_template("edit_report.html", report=report, errors=errors, categories=report_model.categories(),
                           today=datetime.now().strftime("%Y-%m-%d"))


@bp.route("/reports/<int:report_id>/delete", methods=["POST"])
@patient_only
def delete_report(report_id):
    report = owned_report(report_id)
    file_handler.delete_file(g.patient["id"], report["stored_name"])
    report_model.delete(report_id)
    log_activity("Report deleted", f"Deleted '{report['title']}'", report_id=report_id)
    flash("Report deleted.", "success")
    return redirect(url_for("patient.reports"))


def _send(report, as_attachment):
    path = file_handler.file_path(report["patient_id"], report["stored_name"])
    import os
    if not os.path.exists(path):
        raise AppError(404, "The file for this report could not be found on the server.")
    return send_file(path, mimetype=file_handler.SERVE_MIME[report["file_type"]], as_attachment=as_attachment,
                     download_name=report["file_name"])


@bp.route("/reports/<int:report_id>/download")
@patient_only
def download_report(report_id):
    report = owned_report(report_id)
    log_activity("Report downloaded", f"Downloaded '{report['title']}'", report_id=report_id)
    return _send(report, True)


@bp.route("/reports/<int:report_id>/preview")
@patient_only
def preview_report(report_id):
    report = owned_report(report_id)
    if request.args.get("log") == "1":
        log_activity("Report viewed", f"Previewed '{report['title']}'", report_id=report_id)
    return _send(report, False)


@bp.route("/reports/<int:report_id>/important", methods=["POST"])
@patient_only
def toggle_important(report_id):
    report = owned_report(report_id)
    new_value = not report["is_important"]
    report_model.set_important(report_id, new_value)
    if wants_json():
        return jsonify(ok=True, important=new_value,
                       message="Marked as important." if new_value else "Removed from important reports.")
    flash("Marked as important." if new_value else "Removed from important reports.", "success")
    return redirect(request.referrer or url_for("patient.report_details", report_id=report_id))


# ---------------------------------------------------------- timeline/compare

@bp.route("/timeline")
@patient_only
def timeline():
    return render_template("timeline.html", years=report_model.timeline(g.patient["id"]))


@bp.route("/compare")
@patient_only
def compare():
    pid = g.patient["id"]
    all_reports = report_model.search(pid, sort="newest")
    a_id, b_id = request.args.get("a", type=int), request.args.get("b", type=int)
    ra = rb = None
    if a_id and b_id:
        ra, rb = report_model.get(a_id), report_model.get(b_id)
        if not ra or not rb or ra["patient_id"] != pid or rb["patient_id"] != pid:
            raise AppError(403, "You are not authorized to access this report.")
        if ra["id"] == rb["id"]:
            flash("Please choose two different reports to compare.", "error")
            ra = rb = None
        elif ra["category_id"] != rb["category_id"]:
            flash("You can only compare two reports from the same category.", "error")
            ra = rb = None
        else:
            log_activity("Reports compared", f"Compared '{ra['title']}' and '{rb['title']}'")
    return render_template("compare.html", reports=all_reports, categories=report_model.categories(),
                           ra=ra, rb=rb, sel_a=a_id, sel_b=b_id)


# ------------------------------------------------------------------ sharing

@bp.route("/reports/<int:report_id>/share", methods=["GET", "POST"])
@patient_only
def share_report(report_id):
    report = owned_report(report_id)
    doctors = doctor_model.list_active()
    errors = {}
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", type=int)
        doctor = doctor_model.get(doctor_id) if doctor_id else None
        if not doctor or not doctor["is_active"]:
            errors["doctor_id"] = "Please select a doctor."
        message = request.form.get("message", "").strip()[:500]
        expires_at = None
        try:
            expires_dt = datetime.strptime(
                f"{request.form.get('expiry_date', '')} {request.form.get('expiry_time', '')}", "%Y-%m-%d %H:%M")
            if expires_dt <= datetime.now():
                errors["expiry"] = "Expiry must be a future date and time."
            elif expires_dt > datetime.now() + timedelta(days=365):
                errors["expiry"] = "Expiry cannot be more than 1 year from now."
            else:
                expires_at = expires_dt.strftime("%Y-%m-%d %H:%M:00")
        except ValueError:
            errors["expiry"] = "Please choose a valid expiry date and time."
        if not errors and report_model.active_share_exists(report_id, doctor_id):
            errors["doctor_id"] = "This report is already actively shared with that doctor. Revoke it first to change the expiry."
        if not errors:
            report_model.create_share(report_id, g.patient["id"], doctor_id, message, expires_at)
            log_activity("Report shared", f"Shared '{report['title']}' with {doctor['name']} until {expires_at[:16]}",
                         report_id=report_id, target_user_id=doctor["uid"])
            flash(f"Report shared with {doctor['name']}.", "success")
            return redirect(url_for("patient.shared_reports"))
    default_exp = datetime.now() + timedelta(days=7)
    return render_template("share_report.html", report=report, doctors=doctors, errors=errors,
                           default_date=default_exp.strftime("%Y-%m-%d"), default_time=default_exp.strftime("%H:%M"),
                           today=datetime.now().strftime("%Y-%m-%d"), form=request.form)


@bp.route("/shared-reports")
@patient_only
def shared_reports():
    return render_template("shared_reports.html", shares=report_model.shares_for_patient(g.patient["id"]))


@bp.route("/shares/<int:share_id>/revoke", methods=["POST"])
@patient_only
def revoke_share(share_id):
    share = report_model.get_share(share_id)
    if share is None:
        raise AppError(404, "Share not found.")
    if share["patient_id"] != g.patient["id"]:
        raise AppError(403, "You are not authorized to access this report.")
    if share["effective_status"] == "active":
        report_model.revoke_share(share_id)
        log_activity("Share revoked", f"Revoked access to '{share['title']}' for {share['doctor_name']}",
                     report_id=share["report_id"], target_user_id=share["doctor_user_id"])
        flash("Access revoked. The doctor can no longer open this report.", "success")
    else:
        flash("This share is no longer active.", "error")
    return redirect(request.referrer or url_for("patient.shared_reports"))


# ----------------------------------------------------------------- activity

def _group_by_day(rows):
    today = datetime.now().date()
    groups = []
    for r in rows:
        day = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S").date()
        label = "Today" if day == today else "Yesterday" if day == today - timedelta(days=1) else day.strftime("%d %B %Y")
        if not groups or groups[-1]["label"] != label:
            groups.append({"label": label, "items": []})
        groups[-1]["items"].append(r)
    return groups


@bp.route("/activities")
@patient_only
def activities():
    return render_template("activities.html", groups=_group_by_day(activity_model.for_user(g.user["id"], 200)))
