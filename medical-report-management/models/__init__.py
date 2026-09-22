"""Database helpers + schema (plain sqlite3, no ORM)."""
import sqlite3
from datetime import datetime

from flask import g, current_app

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('patient','doctor','admin')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    patient_code      TEXT UNIQUE,
    age               INTEGER,
    gender            TEXT,
    address           TEXT,
    emergency_contact TEXT,
    medical_info      TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    specialization TEXT,
    hospital       TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_categories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    icon       TEXT NOT NULL DEFAULT 'file',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES report_categories(id),
    title           TEXT NOT NULL,
    hospital_name   TEXT,
    laboratory_name TEXT,
    doctor_name     TEXT,
    department      TEXT,
    report_date     TEXT NOT NULL,
    notes           TEXT,
    is_important    INTEGER NOT NULL DEFAULT 0,
    file_name       TEXT NOT NULL,
    stored_name     TEXT NOT NULL UNIQUE,
    file_type       TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    file_hash       TEXT NOT NULL,
    uploaded_at     TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports(patient_id, file_hash);

CREATE TABLE IF NOT EXISTS report_shares (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id  INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    message    TEXT,
    expires_at TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shares_doctor ON report_shares(doctor_id);
CREATE INDEX IF NOT EXISTS idx_shares_report ON report_shares(report_id);

CREATE TABLE IF NOT EXISTS activity_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action         TEXT NOT NULL,
    details        TEXT,
    report_id      INTEGER,
    ip_address     TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id);
"""

DEFAULT_CATEGORIES = [
    ("Blood Test", "droplet"),
    ("X-Ray", "image"),
    ("Scan", "layers"),
    ("ECG", "activity"),
    ("Prescription", "pill"),
    ("Discharge Summary", "clipboard"),
    ("Other", "file"),
]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    """Run a SELECT. Always use ? placeholders (protects from SQL injection)."""
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run INSERT / UPDATE / DELETE and commit. Returns the new row id."""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_schema():
    db = get_db()
    db.executescript(SCHEMA)
    ts = now_str()
    for name, icon in DEFAULT_CATEGORIES:
        db.execute(
            "INSERT OR IGNORE INTO report_categories (name, icon, created_at, updated_at) VALUES (?,?,?,?)",
            (name, icon, ts, ts),
        )
    db.commit()
