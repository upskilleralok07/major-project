from . import query, execute, now_str


def create(user_id, specialization="", hospital=""):
    ts = now_str()
    return execute(
        "INSERT INTO doctors (user_id, specialization, hospital, created_at, updated_at) VALUES (?,?,?,?,?)",
        (user_id, specialization, hospital, ts, ts))


def get_by_user(user_id):
    return query("SELECT * FROM doctors WHERE user_id = ?", (user_id,), one=True)


def get(doctor_id):
    return query(
        "SELECT d.*, u.name, u.email, u.is_active, u.id AS uid FROM doctors d JOIN users u ON u.id = d.user_id WHERE d.id = ?",
        (doctor_id,), one=True)


def update(doctor_id, specialization, hospital):
    execute("UPDATE doctors SET specialization=?, hospital=?, updated_at=? WHERE id=?",
            (specialization, hospital, now_str(), doctor_id))


def list_active():
    return query(
        "SELECT d.id, d.specialization, d.hospital, u.name, u.email FROM doctors d "
        "JOIN users u ON u.id = d.user_id WHERE u.is_active = 1 ORDER BY u.name")
