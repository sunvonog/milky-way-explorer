"""Loader normalisation: placeholders and HIP format."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from app.config import REPO_ROOT
from app.loaders import iau_csn, wgsn_faints
from app.loaders.base import null_placeholders, strip_catalogue_prefix

IAU_CSV = REPO_ROOT / "data/raw/iau_csn/current/IAU-Catalog-of-Star-Names.csv"
FAINTS_CSV = REPO_ROOT / "data/raw/wgsn_faints/current/WGSN-Faints.csv"


def test_null_placeholders_nulls_known_tokens() -> None:
    frame = pl.DataFrame({"a": ["ok", "", "_", "-", "--", "  _  "], "n": [1, 2, 3, 4, 5, 6]})
    out = null_placeholders(frame)
    assert out["a"].to_list() == ["ok", None, None, None, None, None]
    assert out["n"].to_list() == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("HIP 1547", "1547"),
        ("hip 1547", "1547"),
        ("1547", "1547"),
        ("HIP1547", "1547"),
        ("-", "-"),
    ],
)
def test_strip_catalogue_prefix_hip(raw, expected) -> None:
    frame = pl.DataFrame({"hip": [raw]}).with_columns(hip=strip_catalogue_prefix("hip", "HIP"))
    assert frame["hip"][0] == expected


def test_iau_csn_nulls_empty_strings(tmp_path: Path) -> None:
    csv = tmp_path / "csn.csv"
    csv.write_text(
        '"<span>proper names</span>","<span>NEC+</span>","<span>Designation</span>",'
        '"<span>HIP</span>","<span>Bayer ID</span>","<span>Simbad spelling</span>",'
        '"<span>Constellation</span>","<span>Origin</span>","<span>Language</span>",'
        '"<span>Reference</span>","<span>Date of Adoption</span>"\n'
        '"StarA","","-","","","","Cygnus","","","--",""\n'
        '"","1","HR 1","1","α Cyg","StarB","","origin","lang","ref","2020/01/01"\n',
        encoding="utf-8",
    )
    frame = iau_csn.load(csv)
    row = frame.filter(pl.col("proper_name") == "StarA").row(0, named=True)
    assert row["hip"] is None
    assert row["designation"] is None
    assert row["bayer_raw"] is None
    assert row["reference"] is None
    assert row["is_valid"] is True
    assert frame.filter(pl.col("proper_name").is_null())["is_valid"][0] is False


def test_wgsn_faints_normalises_hip_and_placeholders(tmp_path: Path) -> None:
    csv = tmp_path / "faints.csv"
    csv.write_text(
        '"WGSN-ID","Name","HIP","RA2000","DE2000","Vmag","type","HR","HD",'
        '"Bayer/other","constellation","distance from Sun/ ly","B-V color","VmagMax","VmagMin"\n'
        '"1","Alpha","HIP 1547","10.0","5.0","8.0","","-","_","-","Pisces","","","",""\n'
        '"2","Beta","1548","20.0","-5.0","9.0","","12","1502","WASP-1","Aries","","","",""\n'
        '"3","Gamma","-","30.0","0.0","10.0","","","","","Taurus","","","",""\n',
        encoding="utf-8",
    )
    frame = wgsn_faints.load(csv)
    by_name = {r["name"]: r for r in frame.iter_rows(named=True)}

    assert by_name["Alpha"]["hip"] == "1547"
    assert by_name["Alpha"]["hd"] is None
    assert by_name["Alpha"]["hr"] is None
    assert by_name["Alpha"]["other_id"] is None

    assert by_name["Beta"]["hip"] == "1548"
    assert by_name["Beta"]["hd"] == "1502"
    assert by_name["Beta"]["other_id"] == "WASP-1"

    assert by_name["Gamma"]["hip"] is None


@pytest.mark.skipif(not IAU_CSV.is_file(), reason="vendored IAU-CSN snapshot missing")
def test_iau_csn_snapshot_has_no_empty_hip_strings() -> None:
    frame = iau_csn.load(IAU_CSV)
    assert frame.filter(pl.col("hip") == "").height == 0
    assert int(frame["is_valid"].sum()) == 605


@pytest.mark.skipif(not FAINTS_CSV.is_file(), reason="vendored WGSN_Faints snapshot missing")
def test_wgsn_faints_snapshot_hips_are_bare_digits() -> None:
    frame = wgsn_faints.load(FAINTS_CSV)
    hips = frame["hip"].drop_nulls()
    assert hips.len() == 83
    assert hips.str.contains(r"^\d+$").all()
    assert frame.filter(pl.col("hd").is_in(["_", "-"])).height == 0
    assert frame.filter(pl.col("hip") == "-").height == 0
