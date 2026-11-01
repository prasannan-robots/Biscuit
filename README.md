# Biscuit 🍪

An online attendance helper for teachers using **BigBlueButton**: compare the user list you save
during class with your class list, and get the absentees in seconds.

1. Upload your class list (`.xlsx` or `.csv`, one student per row).
2. Pick the columns students use as their name (e.g. name + roll number) and upload the
   BigBlueButton user list (`.txt`).
3. See who's absent, who joined with an unknown name, and likely matches — then copy or
   download the report.

Names are matched ignoring case, spaces and punctuation. Files are processed in memory and
never stored on the server.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                       # http://127.0.0.1:5000
```

Production: `gunicorn app:app` (see `Procfile`). Set `SECRET_KEY` in the environment.

## Tests

```bash
pip install pytest && pytest
```
