"""Categories, reports and report sharing."""
from datetime import datetime

from . import query, execute, now_str

# ---------------------------------------------------------------- categories

def categories():
    return query("SELECT * FROM report_categories ORDER BY id")


def get_category(cat_id):
    return query("SELECT * FROM report_categories WHERE id = ?", (cat_id,), one=True)


def category_usage():
    return query(
        "SELECT c.*, COUNT(r.id) AS report_count FROM report_categories c "
        "LEFT JOIN reports r ON r.category_id = c.id GROUP BY c.id ORDER BY c.id")


def add_category(name, icon="file"):
    ts = now_str()
    return execute("INSERT INTO report_categories (name, icon, created_at, updated_at) VALUES (?,?,?,?)",
                   (name.strip(), icon, ts, ts))


def rename_category(cat_id, name):
    execute("UPDATE report_categories SET name=?, updated_at=? WHERE id=?", (name.strip(), now_str(), cat_id))


def delete_category(cat_id):
    execute("DELETE FROM report_categories WHERE id = ?", (cat_id,))


# ------------------------------------------------------------------- reports

_SELECT = ("SELECT r.*, c.name AS category_name, c.icon AS category_icon FROM reports r "
           "JOIN report_categories c ON c.id = r.category_id ")


def get(report_id):
    return query(_SELECT + "WHERE r.id = ?", (report_id,), one=True)


def create(patient_id, category_id, title, hospital, lab, doctor, department, report_date, notes,
           is_important, file_name, stored_name, file_type, file_size, file_hash):
    ts = now_str()
    return execute(
        "INSERT INTO reports (patient_id, category_id, title, hospital_name, laboratory_name, doctor_name, "
        "department, report_date, notes, is_important, file_name, stored_name, file_type, file_size, file_hash, "
        "uploaded_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (patient_id, category_id, title, hospital, lab, doctor, department, report_date, notes, is_important,
         file_name, stored_name, file_type, file_size, file_hash, ts, ts))


def update(report_id, category_id, title, hospital, lab, doctor, department, report_date, notes, is_important):
    execute(
        "UPDATE reports SET category_id=?, title=?, hospital_name=?, laboratory_name=?, doctor_name=?, "
        "department=?, report_date=?, notes=?, is_important=?, updated_at=? WHERE id=?",
        (category_id, title, hospital, lab, doctor, department, report_date, notes, is_important, now_str(), report_id))


def delete(report_id):
    execute("DELETE FROM reports WHERE id = ?", (report_id,))


def set_important(report_id, value):
    execute("UPDATE reports SET is_important=?, updated_at=? WHERE id=?", (1 if value else 0, now_str(), report_id))


def find_by_hash(patient_id, file_hash):
    return query(_SELECT + "WHERE r.patient_id = ? AND r.file_hash = ? ORDER BY r.id LIMIT 1",
                 (patient_id, file_hash), one=True)


def search(patient_id, q="", category="", hospital="", doctor="", date_from="", date_to="",
           important=False, sort="newest", limit=None):
    sql = _SELECT + "WHERE r.patient_id = ?"
    args = [patient_id]
    if q:
        sql += (" AND (r.title LIKE ? OR r.hospital_name LIKE ? OR r.laboratory_name LIKE ? "
                "OR r.doctor_name LIKE ?)")
        args += [f"%{q}%"] * 4
    if category:
        sql += " AND r.category_id = ?"
        args.append(category)
    if hospital:
        sql += " AND (r.hospital_name = ? OR r.laboratory_name = ?)"
        args += [hospital, hospital]
    if doctor:
        sql += " AND r.doctor_name = ?"
        args.append(doctor)
    if date_from:
        sql += " AND r.report_date >= ?"
        args.append(date_from)
    if date_to:
        sql += " AND r.report_date <= ?"
        args.append(date_to)
    if important:
        sql += " AND r.is_important = 1"
    order = {
        "newest": "r.report_date DESC, r.id DESC",
        "oldest": "r.report_date ASC, r.id ASC",
        "uploaded": "r.uploaded_at DESC, r.id DESC",
    }.get(sort, "r.report_date DESC, r.id DESC")
    sql += " ORDER BY " + order
    if limit:
        sql += " LIMIT ?"
        args.append(int(limit))
    return query(sql, args)


def filter_options(patient_id):
    hospitals = query(
        "SELECT DISTINCT name FROM ("
        "SELECT hospital_name AS name FROM reports WHERE patient_id=? AND IFNULL(hospital_name,'') <> '' "
        "UNION SELECT laboratory_name FROM reports WHERE patient_id=? AND IFNULL(laboratory_name,'') <> '') "
        "ORDER BY name", (patient_id, patient_id))
    doctors = query(
        "SELECT DISTINCT doctor_name AS name FROM reports WHERE patient_id=? AND IFNULL(doctor_name,'') <> '' "
        "ORDER BY doctor_name", (patient_id,))
    return [h["name"] for h in hospitals], [d["name"] for d in doctors]


def stats(patient_id):
    row = query(
        "SELECT COUNT(*) AS total, "
        "COALESCE(SUM(is_important),0) AS important, "
        "COUNT(DISTINCT NULLIF(TRIM(hospital_name),'')) AS hospitals, "
        "COUNT(DISTINCT NULLIF(TRIM(doctor_name),'')) AS doctors "
        "FROM reports WHERE patient_id = ?", (patient_id,), one=True)
    return dict(row)


def by_category(patient_id):
    rows = query(
        "SELECT c.name, COUNT(r.id) AS n FROM report_categories c JOIN reports r ON r.category_id = c.id "
        "WHERE r.patient_id = ? GROUP BY c.id ORDER BY n DESC", (patient_id,))
    return [{"name": r["name"], "count": r["n"]} for r in rows]


def by_month(patient_id, limit=12):
    rows = query(
        "SELECT strftime('%Y-%m', report_date) AS month, COUNT(*) AS n FROM reports WHERE patient_id = ? "
        "GROUP BY month ORDER BY month DESC LIMIT ?", (patient_id, limit))
    rows = list(reversed(rows))
    out = []
    for r in rows:
        label = datetime.strptime(r["month"], "%Y-%m").strftime("%b %Y")
        out.append({"label": label, "count": r["n"]})
    return out


def timeline(patient_id):
    """Return [{year, months:[{name, reports:[...]}]}] newest first."""
    rows = search(patient_id, sort="newest")
    years = []
    for r in rows:
        d = datetime.strptime(r["report_date"], "%Y-%m-%d")
        if not years or years[-1]["year"] != d.year:
            years.append({"year": d.year, "months": []})
        months = years[-1]["months"]
        mname = d.strftime("%B")
        if not months or months[-1]["name"] != mname:
            months.append({"name": mname, "reports": []})
        months[-1]["reports"].append(r)
    return years


def totals():
    return dict(query(
        "SELECT (SELECT COUNT(*) FROM reports) AS reports, (SELECT COUNT(*) FROM report_shares) AS shares",
        one=True))


# -------------------------------------------------------------------- shares

def share_status(share):
    """Status is always calculated on the server: revoked > expired > active."""
    if share["status"] == "revoked":
        return "revoked"
    if share["expires_at"] <= now_str():
        return "expired"
    return "active"


def _decorate(rows):
    out = []
    for row in rows:
        d = dict(row)
        d["effective_status"] = share_status(row)
        out.append(d)
    return out


_SHARE_SELECT = (
    "SELECT s.*, r.title, r.report_date, r.hospital_name, r.laboratory_name, r.doctor_name AS report_doctor, "
    "r.file_type, r.file_size, r.file_name, r.notes, r.stored_name, r.patient_id AS owner_patient_id, "
    "c.name AS category_name, c.icon AS category_icon, "
    "pu.name AS patient_name, p.patient_code, du.name AS doctor_name, du.id AS doctor_user_id, "
    "pu.id AS patient_user_id "
    "FROM report_shares s "
    "JOIN reports r ON r.id = s.report_id "
    "JOIN report_categories c ON c.id = r.category_id "
    "JOIN patients p ON p.id = s.patient_id JOIN users pu ON pu.id = p.user_id "
    "JOIN doctors d ON d.id = s.doctor_id JOIN users du ON du.id = d.user_id ")


def create_share(report_id, patient_id, doctor_id, message, expires_at):
    ts = now_str()
    return execute(
        "INSERT INTO report_shares (report_id, patient_id, doctor_id, message, expires_at, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,'active',?,?)", (report_id, patient_id, doctor_id, message, expires_at, ts, ts))


def get_share(share_id):
    row = query(_SHARE_SELECT + "WHERE s.id = ?", (share_id,), one=True)
    return _decorate([row])[0] if row else None


def shares_for_patient(patient_id):
    return _decorate(query(_SHARE_SELECT + "WHERE s.patient_id = ? ORDER BY s.created_at DESC, s.id DESC", (patient_id,)))


def shares_for_report(report_id):
    return _decorate(query(_SHARE_SELECT + "WHERE s.report_id = ? ORDER BY s.created_at DESC, s.id DESC", (report_id,)))


def shares_for_doctor(doctor_id):
    return _decorate(query(_SHARE_SELECT + "WHERE s.doctor_id = ? ORDER BY s.created_at DESC, s.id DESC", (doctor_id,)))


def active_share_exists(report_id, doctor_id):
    for s in shares_for_report(report_id):
        if s["doctor_id"] == doctor_id and s["effective_status"] == "active":
            return True
    return False


def revoke_share(share_id):
    ts = now_str()
    execute("UPDATE report_shares SET status='revoked', revoked_at=?, updated_at=? WHERE id=?", (ts, ts, share_id))
