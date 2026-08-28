"""Alias / star resolution regressions for placeholder and HIP normalisation."""

from __future__ import annotations

import polars as pl

from app.config import REPO_ROOT
from app.domain.identity import build_aliases, build_stars

IAU_CSV = REPO_ROOT / "data/raw/iau_csn/current/IAU-Catalog-of-Star-Names.csv"
FAINTS_CSV = REPO_ROOT / "data/raw/wgsn_faints/current/WGSN-Faints.csv"


def _csn_row(
    *,
    proper_name: str = "Teststar",
    hip: str | None = None,
    designation: str | None = "HR 1",
    bayer_raw: str | None = None,
    constellation: str = "Cyg",
) -> dict:
    return {
        "proper_name": proper_name,
        "nec_plus": None,
        "designation": designation,
        "hip": hip,
        "bayer_raw": bayer_raw,
        "simbad_spelling": None,
        "constellation": constellation,
        "origin": None,
        "language": None,
        "reference": None,
        "adoption_date": None,
        "is_valid": True,
        "source": "iau_csn",
    }


def _faints_row(
    *,
    name: str = "Teststar",
    hip: str | None = None,
    hd: str | None = None,
    other_id: str | None = None,
) -> dict:
    return {
        "wgsn_id": "1",
        "name": name,
        "hip": hip,
        "ra_deg": 10.0,
        "dec_deg": 5.0,
        "vmag": 8.0,
        "spectral_type": None,
        "hr": None,
        "hd": hd,
        "other_id": other_id,
        "constellation": "Pisces",
        "distance_ly": None,
        "bv_color": None,
        "vmag_max": None,
        "vmag_min": None,
        "is_valid": True,
        "source": "wgsn_faints",
    }


def test_faints_only_hip_does_not_double_prefix() -> None:
    """Latent Bug 1: coalesced Faints HIP must become 'HIP nnnn', never 'HIP HIP nnnn'."""
    csn = pl.DataFrame([_csn_row(hip=None)])
    faints = pl.DataFrame([_faints_row(hip="1547")])

    stars = build_stars(csn, faints)
    assert stars["hip"][0] == "1547"

    aliases = build_aliases(stars)
    hip_aliases = aliases.filter(pl.col("catalogue") == "HIP")["alias"].to_list()
    assert hip_aliases == ["HIP 1547"]
    assert not any(a.startswith("HIP HIP") for a in hip_aliases)


def test_empty_search_key_aliases_are_dropped() -> None:
    """Guard against unsearchable aliases (e.g. bare '-') if any slip past loaders."""
    csn = pl.DataFrame([_csn_row(bayer_raw="")])
    faints = pl.DataFrame([_faints_row(other_id="-")])
    stars = build_stars(csn, faints).with_columns(
        bayer_raw=pl.lit(""),
        other_id=pl.lit("-"),
    )
    aliases = build_aliases(stars)
    assert aliases.filter(pl.col("alias_search_key") == "").height == 0
    assert aliases.filter(pl.col("alias") == "-").height == 0
