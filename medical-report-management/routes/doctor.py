"""Doctor area: only reports explicitly shared (and still valid) can be opened."""
import os

from flask import Blueprint, render_template, request, g, send_file

from models import report as report_model
from utils import file_handler
from utils.activity_logger import log_activity
from utils.auth import role_required, AppError

bp = Blueprint("doctor", __name__, url_prefix="/doctor")
doctor_only = role_required("doctor")


def get_valid_share(share_id):
    """The one gatekeeper for doctors.

    Checked on the server for every request (details, preview, download):
      1. the share exists
      2. it was made to THIS doctor
      3. it is not revoked
      4. it has not expired
    """
    share = report_model.get_share(share_id)
    if share is None:
        raise AppError(404, "Report not found.")
    if share["doctor_id"] != g.doctor["id"]:
        raise AppError(403, "You are not authorized to access this report.")
    if share["effective_status"] == "revoked":
        raise AppError(403, "The patient has revoked access to this report.")
    if share["effective_status"] == "expired":
        raise AppError(403, "Access to this report has expired.")
    return share


@bp.route("/dashboard")
@doctor_only
def dashboard():
    shares = report_model.shares_for_doctor(g.doctor["id"])
    count = lambda s: sum(1 for x in shares if x["effective_status"] == s)
    return render_template("doctor/dashboard.html", shares=shares[:6], total=len(shares),
                           active=count("active"), expired=count("expired"), revoked=count("revoked"))


@bp.route("/reports")
@doctor_only
def reports():
    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "")
    shares = report_model.shares_for_doctor(g.doctor["id"])
    if status in ("active", "expired", "revoked"):
        shares = [s for s in shares if s["effective_status"] == status]
    if q:
        shares = [s for s in shares if q in s["title"].lower() or q in s["patient_name"].lower()
                  or q in s["category_name"].lower()]
    return render_template("doctor/reports.html", shares=shares, q=q, status=status)


@bp.route("/reports/<int:share_id>")
@doctor_only
def report_details(share_id):
    share = get_valid_share(share_id)
    log_activity("Report viewed", f"Viewed '{share['title']}' shared by {share['patient_name']}",
                 report_id=share["report_id"], target_user_id=share["patient_user_id"])
    return render_template("doctor/report_details.html", share=share)


def _send(share, as_attachment):
    path = file_handler.file_path(share["owner_patient_id"], share["stored_name"])
    if not os.path.exists(path):
        raise AppError(404, "The file for this report could not be found on the server.")
    return send_file(path, mimetype=file_handler.SERVE_MIME[share["file_type"]], as_attachment=as_attachment,
                     download_name=share["file_name"])


@bp.route("/reports/<int:share_id>/preview")
@doctor_only
def preview(share_id):
    share = get_valid_share(share_id)
    if request.args.get("log") == "1":
        log_activity("Report viewed", f"Previewed '{share['title']}' shared by {share['patient_name']}",
                     report_id=share["report_id"], target_user_id=share["patient_user_id"])
    return _send(share, False)


@bp.route("/reports/<int:share_id>/download")
@doctor_only
def download(share_id):
    share = get_valid_share(share_id)
    log_activity("Report downloaded", f"Downloaded '{share['title']}' shared by {share['patient_name']}",
                 report_id=share["report_id"], target_user_id=share["patient_user_id"])
    return _send(share, True)
