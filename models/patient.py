import secrets
from . import query, execute, now_str


def create(user_id):
    ts = now_str()
    token = secrets.token_urlsafe(24)
    pid = execute("INSERT INTO patients (user_id, qr_token, created_at, updated_at) VALUES (?,?,?,?)", (user_id, token, ts, ts))
    execute("UPDATE patients SET patient_code = ? WHERE id = ?", (f"PAT-{pid:04d}", pid))
    return pid


def get_by_user(user_id):
    pat = query("SELECT * FROM patients WHERE user_id = ?", (user_id,), one=True)
    if pat and not pat["qr_token"]:
        ensure_qr_token(pat["id"])
        pat = query("SELECT * FROM patients WHERE user_id = ?", (user_id,), one=True)
    return pat


def get(patient_id):
    return query(
        "SELECT p.*, u.name, u.email, u.phone FROM patients p JOIN users u ON u.id = p.user_id WHERE p.id = ?",
        (patient_id,), one=True)


def get_by_qr_token(qr_token):
    if not qr_token:
        return None
    return query(
        "SELECT p.*, u.name, u.email, u.phone FROM patients p JOIN users u ON u.id = p.user_id WHERE p.qr_token = ?",
        (qr_token,), one=True)


def ensure_qr_token(patient_id):
    pat = query("SELECT qr_token FROM patients WHERE id = ?", (patient_id,), one=True)
    if pat and not pat["qr_token"]:
        token = secrets.token_urlsafe(24)
        execute("UPDATE patients SET qr_token = ?, updated_at = ? WHERE id = ?", (token, now_str(), patient_id))
        return token
    return pat["qr_token"] if pat else None


def reset_qr_token(patient_id):
    token = secrets.token_urlsafe(24)
    execute("UPDATE patients SET qr_token = ?, updated_at = ? WHERE id = ?", (token, now_str(), patient_id))
    return token


def update(patient_id, age, gender, address, emergency_contact, medical_info):
    execute(
        "UPDATE patients SET age=?, gender=?, address=?, emergency_contact=?, medical_info=?, updated_at=? WHERE id=?",
        (age, gender, address, emergency_contact, medical_info, now_str(), patient_id))

