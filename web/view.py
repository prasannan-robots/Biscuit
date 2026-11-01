import json

from flask import Blueprint, render_template, request

from .attendance import (
    RosterError,
    compare,
    guess_name_columns,
    parse_attendees,
    read_roster,
    roster_names,
)

view = Blueprint("view", __name__)


@view.get("/")
def home():
    return render_template("home.html")


@view.post("/columns")
def columns():
    upload = request.files.get("basefile")
    if not upload or not upload.filename:
        return render_template("home.html", error="Choose your class list first."), 400
    try:
        cols, rows = read_roster(upload.read(), upload.filename)
    except RosterError as exc:
        return render_template("home.html", error=str(exc)), 400
    return render_template(
        "basefilewanted.html",
        columns=cols,
        preview=rows[:3],
        selected=guess_name_columns(cols),
        row_count=len(rows),
        # The roster rides along in the form instead of being stored server-side.
        roster=json.dumps({"columns": cols, "rows": rows}),
    )


def _load_roster(raw: str):
    data = json.loads(raw)
    cols, rows = data["columns"], data["rows"]
    if not (isinstance(cols, list) and isinstance(rows, list)):
        raise ValueError
    return cols, [[str(c) for c in row] for row in rows if isinstance(row, list)]


@view.post("/result")
def result():
    try:
        cols, rows = _load_roster(request.form.get("roster", ""))
    except (ValueError, KeyError, TypeError):
        return render_template("home.html", error="Please start again by uploading the class list."), 400

    picked = sorted({int(c) for c in request.form.getlist("column") if c.isdigit() and int(c) < len(cols)})
    attendee_file = request.files.get("checkfile")
    error = None
    if not picked:
        error = "Pick at least one column that contains student names."
    elif not attendee_file or not attendee_file.filename:
        error = "Choose the user list you saved from BigBlueButton."
    if error:
        return render_template(
            "basefilewanted.html", columns=cols, preview=rows[:3], selected=picked,
            row_count=len(rows), roster=request.form["roster"], error=error,
        ), 400

    attendees = parse_attendees(attendee_file.read().decode("utf-8", errors="replace"))
    outcome = compare(roster_names(rows, picked), attendees)
    return render_template("answer.html", result=outcome, report=outcome.as_text())


@view.get("/more")
def more():
    return render_template("more.html")


@view.app_errorhandler(413)
def too_large(_error):
    return render_template("home.html", error="That file is too large (max 8 MB)."), 413
