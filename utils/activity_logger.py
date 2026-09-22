from flask import g, request

from models import activity


def log_activity(action, details="", report_id=None, user_id=None, target_user_id=None):
    """Write one row to activity_logs. If user_id is omitted the logged-in user is used."""
    if user_id is None and getattr(g, "user", None):
        user_id = g.user["id"]
    ip = request.remote_addr if request else None
    activity.add(user_id, action, details, report_id, target_user_id, ip)
