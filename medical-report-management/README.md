# MediVault – Medical Report Management

A complete college project built with **HTML5 + CSS3 + Vanilla JavaScript**, **Python Flask (Jinja templates)** and **SQLite**.
Patients keep every report from every hospital, laboratory and doctor in one place, and can share single reports with doctors for a limited time.

## 1. Project introduction
MediVault is a web application with three roles – **Patient**, **Doctor** and **Admin**. Patients upload, organise, search, compare and share their medical reports. Doctors can open only what a patient has explicitly shared (and only until the share expires). Admins manage users, categories and see system statistics and logs.

## 2. Problem statement
Patients may have medical reports from different hospitals, laboratories, and doctors stored in different places. Finding an older report when it is needed can be difficult and time-consuming. A better way of organizing and accessing a patient's medical reports is needed.

## 3. Features
**Patient** – register/login, profile, drag-and-drop upload (PDF/JPG/JPEG/PNG) with progress, validation and preview, duplicate detection (SHA-256), search + filters + sorting (live, via Flask JSON endpoint), report details, edit/delete, download, print, modal preview (zoom, full screen), important (star) reports, medical timeline, compare two reports of the same category, share with doctors with message and expiry date/time, revoke, activity history, dashboard with animated statistics and Chart.js charts.
**Doctor** – dashboard (total / active / expired / revoked shares), list of shared reports, preview and download of *active* shares only.
**Admin** – dashboard statistics, search/filter users, activate/deactivate, user details, manage report categories, system activity logs.
**Security** – Werkzeug password hashing, session login, role-based authorisation, ownership checks on every report route, secure random file names, extension + MIME + file-signature validation, size limit, CSRF tokens on all POST requests, parameterised SQL, share expiry checked **in Flask** on every doctor request, secret key from environment/local file.
**UI** – responsive healthcare SaaS design, collapsible sidebar, mobile slide-in menu, toasts, skeleton loaders, empty/error states, scroll-reveal timeline, count-up numbers, `prefers-reduced-motion` respected.

## 4. Technology stack
| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3 (variables, grid, flexbox), Vanilla JavaScript, Jinja2 templates |
| Charts | Chart.js via CDN (only for the dashboard charts) |
| Backend | Python 3.9+, Flask |
| Database | SQLite (`medical_reports.db`) using Python's built-in `sqlite3` |
| File storage | Local `uploads/` folder |

## 5. Folder structure
```
medical-report-management/
├── app.py                 # creates the Flask app, security, error pages, DB init
├── config.py              # settings (MAX_FILE_MB, secret key, paths)
├── requirements.txt
├── medical_reports.db     # SQLite database (with demo data)
├── models/                # database code: schema + queries (user, patient, doctor, report, activity)
├── routes/                # auth.py, patient.py, doctor.py, admin.py (Flask blueprints)
├── utils/                 # auth decorators, file validation/storage, activity logger, demo data
├── uploads/               # uploaded report files (uploads/<patient_id>/<random>.pdf)
├── templates/             # Jinja2 pages (+ doctor/ and admin/ folders, shared partials starting with _)
└── static/                # css/ (style, dashboard, animations), js/ (main, animations, dashboard, upload, reports), images/
```

## 6. Database schema
`users`, `patients`, `doctors`, `report_categories`, `reports`, `report_shares`, `activity_logs` – with primary keys, foreign keys, UNIQUE / NOT NULL / CHECK constraints and `created_at` / `updated_at` columns.
One patient → many reports · one report → many shares · one doctor → many shares · one user → many activity logs.
A share is *active* only if its status is `active` **and** `expires_at` is in the future; otherwise it is *expired* or *revoked*.

## 7. Installation
```bash
# 1) go into the project folder
cd medical-report-management

# 2) create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 3) install the packages (only Flask + Werkzeug)
pip install -r requirements.txt
```

## 8. Database initialisation
The database and demo data are created **automatically** the first time you run the app if `medical_reports.db` is missing.
Manual commands:
```bash
python app.py --init-db     # create tables + demo data (keeps existing data)
python app.py --reset-db    # delete database and uploads, then recreate demo data
```

## 9. Run
```bash
python app.py
```
Open **http://127.0.0.1:5000**

Optional environment variables: `SECRET_KEY`, `MAX_FILE_MB` (default 10), `FLASK_DEBUG=0`.

## 10. Demo credentials (fake data)
| Role | Email | Password |
|---|---|---|
| Patient | patient@example.com | Patient@123 |
| Doctor | doctor@example.com | Doctor@123 |
| Admin | admin@example.com | Admin@123 |

Extra demo users: `priya@example.com` (patient, Patient@123) and `doctor2@example.com` (doctor, Doctor@123).
The demo patient already has 10 reports (two blood tests for comparison), and shares in all states: **active**, **expired** and **revoked**.

## 11. Pages explained
| Page | URL |
|---|---|
| Landing page | `/` |
| Register / Login / Logout | `/register`, `/login`, `/logout` |
| Patient dashboard | `/dashboard` |
| My reports (search & filter) | `/reports` · JSON: `/reports/search` |
| Upload | `/reports/upload` |
| Report details / edit / delete | `/reports/<id>`, `/reports/<id>/edit`, `/reports/<id>/delete` |
| Download / preview / important | `/reports/<id>/download`, `/preview`, `/important` |
| Important reports | `/important` |
| Timeline · Compare | `/timeline`, `/compare` |
| Share · Shared list · Revoke | `/reports/<id>/share`, `/shared-reports`, `/shares/<id>/revoke` |
| Activity history | `/activities` |
| Profile · Settings | `/profile`, `/profile/edit`, `/settings` |
| Doctor | `/doctor/dashboard`, `/doctor/reports`, `/doctor/reports/<share_id>` |
| Admin | `/admin/dashboard`, `/admin/users`, `/admin/users/<id>/status`, `/admin/categories`, `/admin/activity` |

## 12. Demo script (2 minutes)
1. Login as patient → dashboard → search/filter reports → open a report → preview.
2. Upload a PDF, then upload the same file again → duplicate warning.
3. Timeline → Compare the two blood tests.
4. Share a report with Dr. Meena for a short time → Shared Reports.
5. Login as doctor (another browser/private window) → open the shared report; try an expired one.
6. Back as patient → Revoke → doctor can no longer open it.
7. Login as admin → users, categories, logs.

## 13. Future enhancements
Email/SMS reminders for share expiry, OCR to search inside reports, two-factor login, family accounts, cloud storage, audit export, dark mode.

> MediVault does not give medical advice or diagnosis. All demo data is fake.
