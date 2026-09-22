"""Application configuration.

Everything that a student may want to change lives here.
"""
import os
import shutil
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def get_database_path():
    """On Vercel, copy database to /tmp so SQLite can perform INSERT/UPDATE queries on a writable filesystem."""
    base_db = os.path.join(BASE_DIR, "medical_reports.db")
    if IS_VERCEL:
        tmp_db = "/tmp/medical_reports.db"
        if not os.path.exists(tmp_db) and os.path.exists(base_db):
            try:
                shutil.copyfile(base_db, tmp_db)
            except Exception:
                pass
        return tmp_db
    return base_db


def _load_secret_key():
    """Use SECRET_KEY from environment or local fallback without crashing on read-only file systems."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    if IS_VERCEL:
        return "medivault-secret-key-vercel-production-2026"
    key_file = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(key_file):
        try:
            with open(key_file) as fh:
                return fh.read().strip()
        except Exception:
            pass
    key = secrets.token_hex(32)
    try:
        with open(key_file, "w") as fh:
            fh.write(key)
    except Exception:
        pass
    return key


class Config:
    SECRET_KEY = _load_secret_key()
    DATABASE = get_database_path()
    UPLOAD_FOLDER = "/tmp/uploads" if IS_VERCEL else os.path.join(BASE_DIR, "uploads")

    # Maximum size of one uploaded report (in MB). Change it here or with
    # the MAX_FILE_MB environment variable.
    MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", 10))
    MAX_CONTENT_LENGTH = (MAX_FILE_MB + 1) * 1024 * 1024

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
