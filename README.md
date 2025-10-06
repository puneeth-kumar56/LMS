
# Simple LMS (Learning Management System)

This is a minimal LMS built with Flask, HTML and CSS. It provides a small API and simple web UI to:

- Create courses
- List courses
- Enroll students in courses
- View enrolled students

How to run

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app:

```powershell
python app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Notes

- This uses a simple SQLite database stored in `lms.db`.
- It's intentionally minimal for learning and extension.
