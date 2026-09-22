"""Application configuration."""
import os
import shutil
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def get_database_path():
    """On Vercel, copy the bundled database to /tmp (writable) on first use.
    If no bundled DB exists, return the /tmp path so init_schema() creates it fresh.
    """
    base_db = os.path.join(BASE_DIR, "medical_reports.db")
    if IS_VERCEL:
        tmp_db = "/tmp/medical_reports.db"
        if not os.path.exists(tmp_db):
            if os.path.exists(base_db):
                try:
                    shutil.copyfile(base_db, tmp_db)
                except Exception:
                    pass
        return tmp_db
    return base_db


def _load_secret_key():
    """Use SECRET_KEY from environment or a stable fallback.
    IMPORTANT: set the SECRET_KEY environment variable in Vercel dashboard
    so sessions remain valid across serverless invocations.
    """
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    if IS_VERCEL:
        # Stable fallback so sessions don't break between cold starts.
        # Override this with a real SECRET_KEY env var in Vercel for production.
        return "medivault-sih-2026-stable-secret-key-do-change-in-prod"
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

    # Maximum size of one uploaded report (in MB).
    MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", 10))
    MAX_CONTENT_LENGTH = (MAX_FILE_MB + 1) * 1024 * 1024

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # On Vercel (HTTPS), mark session cookie as Secure
    SESSION_COOKIE_SECURE = IS_VERCEL
