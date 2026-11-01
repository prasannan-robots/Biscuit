import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from web.attendance import (  # noqa: E402
    RosterError, compare, guess_name_columns, normalize, parse_attendees, read_roster, roster_names,
)


def xlsx_bytes(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def test_numeric_ids_match_without_trailing_decimal():
    df = pd.DataFrame({"STUDENT NAME": ["AADHITHYA S", "BALAJI S"], "ID": [38633, 26622]})
    columns, rows = read_roster(xlsx_bytes(df), "class.xlsx")
    names = roster_names(rows, [0, 1])
    assert names == ["AADHITHYA S 38633", "BALAJI S 26622"]
    result = compare(names, parse_attendees("AADHITHYA S 38633\nBALAJI S 26622 locked\n"))
    assert result.absent == [] and len(result.present) == 2


def test_counts_and_unknowns():
    result = compare(["Asha K", "Ravi M", "Devi P.T"], parse_attendees("asha k\nDEVI .P.T\nGuest 42\n"))
    assert result.present == ["Asha K", "Devi P.T"]
    assert result.absent == ["Ravi M"]
    assert result.unknown == ["Guest 42"]
    text = result.as_text()
    assert "on roll: 3" in text and "present: 2" in text and "absent: 1" in text


def test_suggests_close_matches_for_absentees():
    result = compare(["Arjuna B"], ["Arjun B"])
    assert result.absent == ["Arjuna B"]
    assert result.maybe == {"Arjuna B": "Arjun B"}


def test_blank_cells_and_csv():
    csv = b"Name,Section\nAsha,A\n,\nRavi,\n"
    columns, rows = read_roster(csv, "list.csv")
    assert columns == ["Name", "Section"]
    assert roster_names(rows, [0, 1]) == ["Asha A", "Ravi"]


def test_rejects_bad_files():
    for data, name in [(b"hello", "x.txt"), (b"not a spreadsheet", "x.xlsx")]:
        try:
            read_roster(data, name)
        except RosterError:
            continue
        raise AssertionError(f"accepted {name}")


def test_helpers():
    assert normalize("  Devi .P.T  locked ") == "devipt"
    assert guess_name_columns(["S.NO", "STUDENT NAME", "CLASS"]) == [1]
    assert guess_name_columns(["A", "B"]) == [0]
    assert parse_attendees("2.26pm session2\n\nab\n Suganya  T Maths \n") == ["2.26pm session2", "Suganya T Maths"]
