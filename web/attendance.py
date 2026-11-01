"""Attendance matching: compare a class roster with a BigBlueButton user list.

Everything here is pure and in-memory: nothing about students is written to
disk, and each request is independent of every other teacher's.
"""

import difflib
import io
import math
import re
from dataclasses import dataclass, field

import pandas as pd

MAX_ROSTER_ROWS = 5000


class RosterError(ValueError):
    """The uploaded roster couldn't be read. The message is safe to show."""


def _cell(value) -> str:
    """Spreadsheet cell -> clean text. 38633.0 -> "38633", NaN -> ""."""
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def read_roster(data: bytes, filename: str) -> tuple[list[str], list[list[str]]]:
    """Returns (column names, rows of cell text) from an .xlsx/.xls/.csv file."""
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data), dtype=object)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(data), dtype=object)
        else:
            raise RosterError("Upload the class list as an .xlsx or .csv file.")
    except RosterError:
        raise
    except Exception as exc:  # pandas raises many different errors for bad files
        raise RosterError("Couldn't read that file. Is it a valid spreadsheet?") from exc

    df = df.dropna(how="all")
    if df.empty:
        raise RosterError("The class list is empty.")
    if len(df) > MAX_ROSTER_ROWS:
        raise RosterError(f"The class list has more than {MAX_ROSTER_ROWS} rows.")
    columns = [_cell(c) or f"Column {i + 1}" for i, c in enumerate(df.columns)]
    rows = [[_cell(v) for v in row] for row in df.itertuples(index=False)]
    return columns, rows


def guess_name_columns(columns: list[str]) -> list[int]:
    """Columns that look like they hold names, to pre-select in the form."""
    picks = [i for i, c in enumerate(columns) if re.search(r"name|student", c, re.I)]
    return picks or [0]


def normalize(name: str) -> str:
    """Case-, space- and punctuation-insensitive key; drops BBB's 'locked' tag."""
    text = re.sub(r"\blocked\b", "", name, flags=re.I)
    return re.sub(r"[^0-9a-z]", "", text.lower())


def parse_attendees(text: str) -> list[str]:
    """Names from a BigBlueButton 'save user list' export, one per line."""
    attendees = []
    for line in text.splitlines():
        line = line.strip()
        if len(normalize(line)) > 2:
            attendees.append(re.sub(r"\s+", " ", re.sub(r"\blocked\b", "", line, flags=re.I)).strip())
    return attendees


@dataclass
class Result:
    present: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)
    # Attendees that matched nobody on the roster (e.g. joined with a nickname).
    unknown: list[str] = field(default_factory=list)
    # Absentee -> attendee name that looks like them.
    maybe: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.present) + len(self.absent)

    def as_text(self) -> str:
        lines = ["Absent:"] + [f"  {name}" for name in self.absent]
        lines += [
            "",
            f"Number of students on roll: {self.total}",
            f"Number of students present: {len(self.present)}",
            f"Number of students absent: {len(self.absent)}",
        ]
        if self.unknown:
            lines += ["", "Joined but not on the class list:"] + [f"  {n}" for n in self.unknown]
        return "\n".join(lines) + "\n"


def roster_names(rows: list[list[str]], columns: list[int]) -> list[str]:
    names = []
    for row in rows:
        parts = [row[c] for c in columns if c < len(row) and row[c]]
        if parts:
            names.append(" ".join(parts))
    return names


def compare(roster: list[str], attendees: list[str]) -> Result:
    attendee_keys = {normalize(a): a for a in attendees}
    roster_keys = {normalize(r) for r in roster}
    result = Result()
    for name in roster:
        (result.present if normalize(name) in attendee_keys else result.absent).append(name)
    result.unknown = [a for key, a in attendee_keys.items() if key not in roster_keys]
    unknown_keys = {normalize(a): a for a in result.unknown}
    for name in result.absent:
        close = difflib.get_close_matches(normalize(name), unknown_keys, n=1, cutoff=0.8)
        if close:
            result.maybe[name] = unknown_keys[close[0]]
    return result
