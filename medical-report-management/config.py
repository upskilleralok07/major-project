"""Application configuration.

Everything that a student may want to change lives here.
"""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_secret_key():
    """Use SECRET_KEY from the environment; otherwise create one once and
    keep it in a local file so sessions survive restarts."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(key_file):
        with open(key_file) as fh:
            return fh.read().strip()
    key = secrets.token_hex(32)
    with open(key_file, "w") as fh:
        fh.write(key)
    return key


class Config:
    SECRET_KEY = _load_secret_key()
    DATABASE = os.path.join(BASE_DIR, "medical_reports.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # Maximum size of one uploaded report (in MB). Change it here or with
    # the MAX_FILE_MB environment variable.
    MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", 10))
    MAX_CONTENT_LENGTH = (MAX_FILE_MB + 1) * 1024 * 1024

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
