"""Upload validation, safe storage and demo-file generators."""
import hashlib
import math
import os
import struct
import uuid
import zlib

from flask import current_app
from werkzeug.utils import secure_filename

MIME_BY_EXT = {
    "pdf": {"application/pdf"},
    "jpg": {"image/jpeg", "image/pjpeg"},
    "jpeg": {"image/jpeg", "image/pjpeg"},
    "png": {"image/png"},
}
SIGNATURES = {
    "pdf": (b"%PDF",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}
SERVE_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


def validate_upload(file_storage, max_mb):
    """Return (ok, error_message, info). Checks name, extension, MIME type, real content and size."""
    original = secure_filename(file_storage.filename or "")
    if not original or "." not in original:
        return False, "Invalid file type. Please upload a PDF, JPG, JPEG or PNG file.", None
    ext = original.rsplit(".", 1)[1].lower()
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return False, "Invalid file type. Please upload a PDF, JPG, JPEG or PNG file.", None
    if (file_storage.mimetype or "").lower() not in MIME_BY_EXT[ext]:
        return False, "Invalid file type. The file content type does not match its extension.", None
    data = file_storage.read()
    file_storage.seek(0)
    if len(data) == 0:
        return False, "The selected file is empty.", None
    if len(data) > max_mb * 1024 * 1024:
        return False, f"File size exceeds the allowed limit of {max_mb} MB.", None
    if not any(data.startswith(sig) for sig in SIGNATURES[ext]):
        return False, "Invalid file type. The file content does not look like a real " + ext.upper() + ".", None
    return True, None, {
        "ext": ext,
        "size": len(data),
        "hash": hashlib.sha256(data).hexdigest(),
        "data": data,
        "original_name": original,
    }


def _patient_dir(patient_id):
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], str(int(patient_id)))
    os.makedirs(path, exist_ok=True)
    return path


def save_file(patient_id, data, ext):
    """Save bytes with a random name (never the user's file name). Returns stored_name."""
    stored = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(_patient_dir(patient_id), stored), "wb") as fh:
        fh.write(data)
    return stored


def file_path(patient_id, stored_name):
    return os.path.join(_patient_dir(patient_id), os.path.basename(stored_name))


def delete_file(patient_id, stored_name):
    try:
        os.remove(file_path(patient_id, stored_name))
    except OSError:
        pass


# ------------------------------------------------------------ demo generators

def make_sample_pdf(title, lines):
    """Build a tiny valid one-page PDF (no libraries needed). Returns bytes."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    parts = ["0.05 0.58 0.53 rg 0 780 595 62 re f",
             "1 1 1 rg BT /F1 22 Tf 40 803 Td (%s) Tj ET" % esc(title),
             "0.1 0.15 0.25 rg"]
    y = 730
    for line in lines:
        parts.append("BT /F1 12 Tf 40 %d Td (%s) Tj ET" % (y, esc(line)))
        y -= 24
    parts.append("0.5 0.5 0.5 rg BT /F1 9 Tf 40 40 Td (DEMO DOCUMENT - FAKE DATA FOR COLLEGE PROJECT) Tj ET")
    stream = "\n".join(parts)
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (i, obj)).encode("latin-1")
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode()
    return out


def make_sample_png(kind="xray", w=480, h=360):
    """Generate a simple PNG picture (gradient / ECG grid). Returns bytes."""
    rows = []
    cx, cy = w / 2, h / 2
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            if kind == "ecg":
                on_grid = (x % 20 == 0) or (y % 20 == 0)
                r, g, b = (255, 205, 210) if on_grid else (255, 244, 245)
                phase = (x % 120) - 60
                wave = cy
                if -6 <= phase <= 6:
                    wave = cy - 90 * (1 - abs(phase) / 6)
                elif 6 < phase <= 12:
                    wave = cy + 30 * (1 - (phase - 6) / 6)
                elif 24 <= phase <= 44:
                    wave = cy - 22 * math.sin((phase - 24) / 20 * math.pi)
                if abs(y - wave) < 2:
                    r, g, b = 30, 30, 40
            else:
                dist = math.hypot((x - cx) / (w * 0.5), (y - cy) / (h * 0.5))
                v = int(25 + 170 * max(0.0, 1 - dist) ** 1.5)
                if kind == "scan":
                    v = int(v * (0.75 + 0.25 * math.sin(dist * 18)))
                r, g, b = int(v * 0.8), int(v * 0.92), min(255, v + 20)
            row += bytes((r, g, b))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
