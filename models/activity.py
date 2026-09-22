from . import query, execute, now_str


def add(user_id, action, details="", report_id=None, target_user_id=None, ip=None, created_at=None):
    return execute(
        "INSERT INTO activity_logs (user_id, target_user_id, action, details, report_id, ip_address, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (user_id, target_user_id, action, details, report_id, ip, created_at or now_str()))


_BASE = ("SELECT a.*, u.name AS actor_name, u.role AS actor_role FROM activity_logs a "
         "LEFT JOIN users u ON u.id = a.user_id ")


def for_user(user_id, limit=200):
    """Activities done by the user, or done by someone else on this user's data."""
    return query(_BASE + "WHERE a.user_id = ? OR a.target_user_id = ? ORDER BY a.created_at DESC, a.id DESC LIMIT ?",
                 (user_id, user_id, limit))


def search_all(q="", action="", limit=300):
    sql = _BASE + "WHERE 1=1"
    args = []
    if q:
        sql += " AND (u.name LIKE ? OR u.email LIKE ? OR a.details LIKE ?)"
        args += [f"%{q}%"] * 3
    if action:
        sql += " AND a.action = ?"
        args.append(action)
    sql += " ORDER BY a.created_at DESC, a.id DESC LIMIT ?"
    args.append(limit)
    return query(sql, args)


def for_target_user(user_id, limit=100):
    return query(_BASE + "WHERE a.user_id = ? ORDER BY a.created_at DESC, a.id DESC LIMIT ?", (user_id, limit))


def distinct_actions():
    return [r["action"] for r in query("SELECT DISTINCT action FROM activity_logs ORDER BY action")]
