import io
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from web import create_app  # noqa: E402


def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def roster_xlsx():
    buf = io.BytesIO()
    pd.DataFrame({"S.NO": [1, 2, 3], "STUDENT NAME": ["Asha K", "Ravi M", "Devi P.T"], "ID": [101, 102, 103]}).to_excel(buf, index=False)
    return buf.getvalue()


def test_full_flow_is_stateless_and_correct():
    c = client()
    page = c.post("/columns", data={"basefile": (io.BytesIO(roster_xlsx()), "class.xlsx")}, content_type="multipart/form-data")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "3 students found" in html
    roster = re.search(r'name="roster" value="([^"]*)"', html).group(1)
    roster = roster.replace("&#34;", '"').replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
    # A *different* client finishes the flow: nothing is kept server-side.
    result = client().post("/result", data={
        "roster": roster,
        "column": ["1", "2"],
        "checkfile": (io.BytesIO(b"asha k 101\nDEVI .P.T 103 locked\nGuest\n"), "users.txt"),
    }, content_type="multipart/form-data")
    body = result.get_data(as_text=True)
    assert result.status_code == 200
    assert "Ravi M 102" in body and "Asha K 101" not in body.split("Absent")[1].split("Joined")[0]
    assert re.search(r'class="num text-danger">1<', body)
    assert "Guest" in body


def test_bad_inputs_get_friendly_errors():
    c = client()
    assert c.post("/columns", data={}, content_type="multipart/form-data").status_code == 400
    bad = c.post("/columns", data={"basefile": (io.BytesIO(b"junk"), "x.xlsx")}, content_type="multipart/form-data")
    assert bad.status_code == 400 and "valid spreadsheet" in bad.get_data(as_text=True)
    tampered = c.post("/result", data={"roster": "not json"}, content_type="multipart/form-data")
    assert tampered.status_code == 400


def test_no_old_shared_file_routes():
    c = client()
    assert c.get("/return-files/attendance.txt").status_code == 404
    assert c.get("/").status_code == 200 and c.get("/more").status_code == 200
