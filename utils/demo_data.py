"""Creates fake demo users, reports, shares and activity (FAKE DATA ONLY)."""
from datetime import datetime, timedelta

from models import user as user_model, patient as patient_model, doctor as doctor_model
from models import report as report_model, activity as activity_model, execute, query
from utils import file_handler

DEMO_PATIENT = ("Arun Kumar", "patient@example.com", "9876543210", "Patient@123")
DEMO_DOCTOR = ("Dr. Meena Raghavan", "doctor@example.com", "9876500001", "Doctor@123")
DEMO_ADMIN = ("System Admin", "admin@example.com", "9876500000", "Admin@123")


def _ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _cat_id(name):
    return query("SELECT id FROM report_categories WHERE name = ?", (name,), one=True)["id"]


def _add_report(patient_id, i, cat, title, hospital, lab, doctor, dept, days_ago, important, kind, notes):
    report_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    if kind == "pdf":
        data = file_handler.make_sample_pdf(title, [
            "Patient   : (demo patient)", f"Report date: {report_date}", f"Hospital  : {hospital or '-'}",
            f"Laboratory: {lab or '-'}", f"Doctor    : {doctor or '-'}", f"Department: {dept or '-'}", "",
            "This is a fake sample report created for the college demo.",
            "It contains no real medical data.", f"Reference: DEMO-{i:03d}-{days_ago}"])
        ext = "pdf"
    else:
        data = file_handler.make_sample_png(kind, w=480 + i * 8, h=360)
        ext = "png"
    stored = file_handler.save_file(patient_id, data, ext)
    import hashlib
    rid = report_model.create(
        patient_id, _cat_id(cat), title, hospital, lab, doctor, dept, report_date, notes, 1 if important else 0,
        f"{title.lower().replace(' ', '_').replace('/', '-')}.{ext}", stored, ext, len(data),
        hashlib.sha256(data).hexdigest())
    uploaded = _ts(datetime.now() - timedelta(days=max(days_ago - 1, 0), hours=2))
    execute("UPDATE reports SET uploaded_at=?, updated_at=? WHERE id=?", (uploaded, uploaded, rid))
    return rid, uploaded


def seed_demo():
    if user_model.get_by_email(DEMO_ADMIN[1]):
        return  # already seeded

    admin_id = user_model.create_user(*DEMO_ADMIN[:3], DEMO_ADMIN[3], "admin")
    p_uid = user_model.create_user(DEMO_PATIENT[0], DEMO_PATIENT[1], DEMO_PATIENT[2], DEMO_PATIENT[3], "patient")
    pid = patient_model.create(p_uid)
    patient_model.update(pid, 28, "Male", "12, Gandhi Street, Chennai, Tamil Nadu",
                         "Lakshmi Kumar (Mother) - 9876512345", "Blood group: B+. Allergy: Penicillin.")

    p2_uid = user_model.create_user("Priya Sharma", "priya@example.com", "9876543299", "Patient@123", "patient")
    pid2 = patient_model.create(p2_uid)
    patient_model.update(pid2, 34, "Female", "45, Lake View Road, Coimbatore", "Rahul Sharma (Husband) - 9876500077",
                         "Blood group: O+. No known allergies.")

    d1_uid = user_model.create_user(*DEMO_DOCTOR[:3], DEMO_DOCTOR[3], "doctor")
    d1 = doctor_model.create(d1_uid, "General Medicine", "City General Hospital")
    d2_uid = user_model.create_user("Dr. Suresh Babu", "doctor2@example.com", "9876500002", "Doctor@123", "doctor")
    d2 = doctor_model.create(d2_uid, "Cardiology", "Heartcare Clinic")

    R = {}
    specs = [
        ("cbc1", "Blood Test", "Complete Blood Count (CBC)", "Apollo Hospitals", "Apollo Diagnostics Lab", "Dr. Meena Raghavan", "Pathology", 200, 0, "pdf", "Routine annual check-up."),
        ("cbc2", "Blood Test", "Complete Blood Count - Follow-up", "Apollo Hospitals", "Apollo Diagnostics Lab", "Dr. Meena Raghavan", "Pathology", 20, 1, "pdf", "Follow-up test after treatment."),
        ("xray", "X-Ray", "Chest X-Ray", "City General Hospital", "", "Dr. Suresh Babu", "Radiology", 150, 0, "xray", "Taken because of a persistent cough."),
        ("usg", "Scan", "Abdominal Ultrasound Scan", "", "Sunrise Scan Centre", "Dr. Kavitha Nair", "Radiology", 110, 1, "scan", "Fasting for 8 hours before scan."),
        ("ecg", "ECG", "ECG Report", "Heartcare Clinic", "", "Dr. Suresh Babu", "Cardiology", 75, 1, "ecg", "Resting ECG."),
        ("rx", "Prescription", "Prescription - Fever & Cold", "City General Hospital", "", "Dr. Meena Raghavan", "General Medicine", 45, 0, "pdf", "5-day course."),
        ("lipid", "Blood Test", "Lipid Profile", "", "MetroLab Diagnostics", "Dr. Meena Raghavan", "Biochemistry", 95, 0, "pdf", "12 hour fasting sample."),
        ("dis", "Discharge Summary", "Discharge Summary - Appendectomy", "Apollo Hospitals", "", "Dr. Anand Krishnan", "General Surgery", 260, 1, "pdf", "Admitted for 3 days."),
        ("mri", "Scan", "MRI Knee Scan", "", "Sunrise Scan Centre", "Dr. Kavitha Nair", "Radiology", 10, 0, "scan", "Left knee pain."),
        ("thy", "Blood Test", "Thyroid Function Test", "", "MetroLab Diagnostics", "Dr. Meena Raghavan", "Biochemistry", 5, 0, "pdf", ""),
    ]
    uploads = []
    for i, (key, cat, title, hosp, lab, doc, dept, days, imp, kind, notes) in enumerate(specs, 1):
        rid, up = _add_report(pid, i, cat, title, hosp, lab, doc, dept, days, imp, kind, notes)
        R[key] = rid
        uploads.append((rid, title, up))

    r2a, up = _add_report(pid2, 21, "Blood Test", "Blood Sugar (Fasting)", "", "MetroLab Diagnostics",
                          "Dr. Suresh Babu", "Biochemistry", 30, 0, "pdf", "Fasting sample.")
    r2b, up2 = _add_report(pid2, 22, "Prescription", "Prescription - Vitamin D", "City General Hospital", "",
                           "Dr. Meena Raghavan", "General Medicine", 12, 1, "pdf", "")

    # ------------------------------------------------------------ shares
    now = datetime.now()
    def share(rid, doc_id, msg, created, expires, revoked=False):
        sid = report_model.create_share(rid, pid, doc_id, msg, _ts(expires))
        execute("UPDATE report_shares SET created_at=?, updated_at=? WHERE id=?", (_ts(created), _ts(created), sid))
        if revoked:
            execute("UPDATE report_shares SET status='revoked', revoked_at=?, updated_at=? WHERE id=?",
                    (_ts(created + timedelta(days=1)), _ts(created + timedelta(days=1)), sid))
        return sid

    share(R["cbc2"], d1, "Please review my latest blood test before the appointment.", now - timedelta(days=1), now + timedelta(days=7))
    share(R["ecg"], d2, "ECG taken last quarter - sharing for your opinion.", now - timedelta(hours=5), now + timedelta(days=2))
    share(R["xray"], d1, "Chest X-ray for the cough.", now - timedelta(days=10), now - timedelta(days=2))
    share(R["dis"], d2, "Surgery discharge summary.", now - timedelta(days=6), now + timedelta(days=20), revoked=True)

    # ---------------------------------------------------------- activity
    add = activity_model.add
    for rid, title, up in uploads:
        add(p_uid, "Report uploaded", f"Uploaded '{title}'", rid, created_at=up, ip="127.0.0.1")
    add(p_uid, "Login", "Logged in", None, created_at=_ts(now - timedelta(days=3, hours=1)), ip="127.0.0.1")
    add(p_uid, "Report viewed", "Viewed 'Lipid Profile'", R["lipid"], created_at=_ts(now - timedelta(days=3)), ip="127.0.0.1")
    add(p_uid, "Report downloaded", "Downloaded 'Prescription - Fever & Cold'", R["rx"], created_at=_ts(now - timedelta(days=2, hours=4)), ip="127.0.0.1")
    add(p_uid, "Report edited", "Edited 'MRI Knee Scan'", R["mri"], created_at=_ts(now - timedelta(days=2)), ip="127.0.0.1")
    add(p_uid, "Report shared", "Shared 'Chest X-Ray' with Dr. Meena Raghavan", R["xray"], target_user_id=d1_uid, created_at=_ts(now - timedelta(days=10)), ip="127.0.0.1")
    add(d1_uid, "Report viewed", "Viewed 'Chest X-Ray' shared by Arun Kumar", R["xray"], target_user_id=p_uid, created_at=_ts(now - timedelta(days=9)), ip="127.0.0.1")
    add(p_uid, "Report shared", "Shared 'Discharge Summary - Appendectomy' with Dr. Suresh Babu", R["dis"], target_user_id=d2_uid, created_at=_ts(now - timedelta(days=6)), ip="127.0.0.1")
    add(p_uid, "Share revoked", "Revoked access to 'Discharge Summary - Appendectomy' for Dr. Suresh Babu", R["dis"], target_user_id=d2_uid, created_at=_ts(now - timedelta(days=5)), ip="127.0.0.1")
    add(p_uid, "Report shared", "Shared 'ECG Report' with Dr. Suresh Babu", R["ecg"], target_user_id=d2_uid, created_at=_ts(now - timedelta(hours=5)), ip="127.0.0.1")
    add(p_uid, "Report shared", "Shared 'Complete Blood Count - Follow-up' with Dr. Meena Raghavan", R["cbc2"], target_user_id=d1_uid, created_at=_ts(now - timedelta(days=1)), ip="127.0.0.1")
    add(p_uid, "Logout", "Logged out", None, created_at=_ts(now - timedelta(days=1, hours=2)), ip="127.0.0.1")
    add(d1_uid, "Login", "Logged in", None, created_at=_ts(now - timedelta(hours=20)), ip="127.0.0.1")
    add(admin_id, "Login", "Logged in", None, created_at=_ts(now - timedelta(hours=30)), ip="127.0.0.1")
    add(p2_uid, "Report uploaded", "Uploaded 'Blood Sugar (Fasting)'", r2a, created_at=up, ip="127.0.0.1")
    add(p2_uid, "Report uploaded", "Uploaded 'Prescription - Vitamin D'", r2b, created_at=up2, ip="127.0.0.1")
