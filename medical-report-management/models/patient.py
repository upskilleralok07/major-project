from . import query, execute, now_str


def create(user_id):
    ts = now_str()
    pid = execute("INSERT INTO patients (user_id, created_at, updated_at) VALUES (?,?,?)", (user_id, ts, ts))
    execute("UPDATE patients SET patient_code = ? WHERE id = ?", (f"PAT-{pid:04d}", pid))
    return pid


def get_by_user(user_id):
    return query("SELECT * FROM patients WHERE user_id = ?", (user_id,), one=True)


def get(patient_id):
    return query(
        "SELECT p.*, u.name, u.email, u.phone FROM patients p JOIN users u ON u.id = p.user_id WHERE p.id = ?",
        (patient_id,), one=True)


def update(patient_id, age, gender, address, emergency_contact, medical_info):
    execute(
        "UPDATE patients SET age=?, gender=?, address=?, emergency_contact=?, medical_info=?, updated_at=? WHERE id=?",
        (age, gender, address, emergency_contact, medical_info, now_str(), patient_id))
