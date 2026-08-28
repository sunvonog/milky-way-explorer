import polars as pl

from app.config import REPO_ROOT
from app.domain.identity import build_aliases, build_stars
from app.loaders import iau_csn, wgsn_faints

IAU_CSV = REPO_ROOT / "data/raw/iau_csn/current/IAU-Catalog-of-Star-Names.csv"
FAINTS_CSV = REPO_ROOT / "data/raw/wgsn_faints/current/WGSN-Faints.csv"


def test_iau_csn_snapshot_has_no_empty_hip_strings() -> None:
    frame = iau_csn.load(IAU_CSV)
    assert frame.filter(pl.col("hip") == "").height == 0
    assert int(frame["is_valid"].sum()) == 605


def test_wgsn_faints_snapshot_hips_are_bare_digits() -> None:
    frame = wgsn_faints.load(FAINTS_CSV)
    hips = frame["hip"].drop_nulls()
    assert hips.len() == 83
    assert hips.str.contains(r"^\d+$").all()
    assert frame.filter(pl.col("hd").is_in(["_", "-"])).height == 0
    assert frame.filter(pl.col("hip") == "-").height == 0


def test_snapshot_aliases_have_no_junk() -> None:
    csn = iau_csn.load(IAU_CSV)
    faints = wgsn_faints.load(FAINTS_CSV)
    stars = build_stars(csn, faints)
    aliases = build_aliases(stars)

    assert aliases.height == 2875
    assert aliases.filter(pl.col("alias_search_key") == "").height == 0
    assert aliases.filter(pl.col("alias").str.starts_with("HIP HIP")).height == 0
    assert aliases.filter(pl.col("alias").is_in(["HD _", "HD -", "HIP ", "-"])).height == 0
    assert stars.filter(pl.col("hip").is_not_null()).height == 532
    assert stars["hip"].drop_nulls().str.contains(r"^\d+$").all()
