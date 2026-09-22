from werkzeug.security import generate_password_hash, check_password_hash

from . import query, execute, now_str


def get_by_id(user_id):
    return query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)


def get_by_email(email):
    return query("SELECT * FROM users WHERE email = ?", (email.strip().lower(),), one=True)


def create_user(name, email, phone, password, role):
    ts = now_str()
    return execute(
        "INSERT INTO users (name, email, phone, password_hash, role, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?,1,?,?)",
        (name.strip(), email.strip().lower(), phone.strip(), generate_password_hash(password), role, ts, ts),
    )


def check_password(user, password):
    return check_password_hash(user["password_hash"], password)


def update_basic(user_id, name, phone):
    execute("UPDATE users SET name=?, phone=?, updated_at=? WHERE id=?",
            (name.strip(), phone.strip(), now_str(), user_id))


def change_password(user_id, new_password):
    execute("UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
            (generate_password_hash(new_password), now_str(), user_id))


def set_active(user_id, active):
    execute("UPDATE users SET is_active=?, updated_at=? WHERE id=?",
            (1 if active else 0, now_str(), user_id))


def list_users(q="", role="", status=""):
    sql = "SELECT * FROM users WHERE 1=1"
    args = []
    if q:
        sql += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"
        args += [f"%{q}%"] * 3
    if role in ("patient", "doctor", "admin"):
        sql += " AND role = ?"
        args.append(role)
    if status == "active":
        sql += " AND is_active = 1"
    elif status == "inactive":
        sql += " AND is_active = 0"
    sql += " ORDER BY created_at DESC, id DESC"
    return query(sql, args)


def count_by_role():
    rows = query("SELECT role, COUNT(*) AS n FROM users GROUP BY role")
    return {r["role"]: r["n"] for r in rows}
