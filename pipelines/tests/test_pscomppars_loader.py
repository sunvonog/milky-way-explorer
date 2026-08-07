from pathlib import Path

import polars as pl

from app.loaders.pscomppars import RAW_SCHEMA, load, normalize

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"


def test_current_snapshot_contract():
    frame = load(SNAPSHOT)

    assert frame.height == 6336
    assert frame["planet_name"].n_unique() == 6336
    assert frame["host_name"].n_unique() == 4749
    assert int(frame["is_valid"].sum()) == 6336


def test_current_snapshot_gaia_ids_are_normalized():
    frame = load(SNAPSHOT)
    gaia_ids = frame["gaia_source_id"].drop_nulls()

    assert gaia_ids.len() == 5955
    assert gaia_ids.n_unique() == 4396
    assert gaia_ids.dtype == pl.Int64


def test_flags_are_boolean():
    frame = load(SNAPSHOT)

    assert frame.schema["is_circumbinary"] == pl.Boolean
    assert frame.schema["is_controversial"] == pl.Boolean


def test_malformed_gaia_designation_is_retained_but_invalid():
    raw = pl.read_csv(
        SNAPSHOT,
        schema=RAW_SCHEMA,
        null_values="",
    ).head(1)

    raw = raw.with_columns(gaia_dr3_id=pl.lit("not a GAIA DR3 designation"))

    frame = normalize(raw)

    assert frame.height == 1
    assert frame["gaia_source_id"][0] is None
    assert frame["is_valid"][0] is False
