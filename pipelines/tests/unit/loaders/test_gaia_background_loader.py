from pathlib import Path

import polars as pl
import pytest

from app.loaders import gaia_background
from app.sources.gaia import GAIA_BACKGROUND_COLUMNS


def _raw_row(
    source_id: int,
    *,
    ra: float = 10.0,
    dec: float = 20.0,
    longitude: float = 100.0,
    latitude: float = 30.0,
) -> dict[str, object]:
    row: dict[str, object] = dict.fromkeys(GAIA_BACKGROUND_COLUMNS)

    row.update(
        {
            "source_id": source_id,
            "ra": ra,
            "dec": dec,
            "l": longitude,
            "b": latitude,
            "parallax": 5.0,
            "parallax_over_error": 50.0,
            "phot_g_mean_mag": 12.0,
            "bp_rp": 0.8,
            "ruwe": 1.0,
            "distance_gspphot": 200.0,
        }
    )

    return row


def _write_batch(snapshot: Path, batch_number: int, rows: list[dict[str, object]]) -> Path:
    path = snapshot / "batches" / f"gaia-background-{batch_number:04d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(rows).select(GAIA_BACKGROUND_COLUMNS).write_csv(path)

    return path


def test_load_combines_normalizes_and_sorts_background_batches(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 2, [_raw_row(42)])
    _write_batch(snapshot, 1, [_raw_row(7)])

    frame: pl.DataFrame = gaia_background.load(snapshot)

    assert frame["gaia_source_id"].to_list() == [7, 42]

    assert frame.select(
        "gaia_source_id",
        "ra_deg",
        "dec_deg",
        "galactic_longitude_deg",
        "galactic_latitude_deg",
        "parallax_mas",
        "phot_g_mean_magnitude",
        "bp_rp_color",
        "distance_gspphot_pc",
        "is_valid",
        "source",
    ).schema == pl.Schema(
        {
            "gaia_source_id": pl.Int64,
            "ra_deg": pl.Float64,
            "dec_deg": pl.Float64,
            "galactic_longitude_deg": pl.Float64,
            "galactic_latitude_deg": pl.Float64,
            "parallax_mas": pl.Float64,
            "phot_g_mean_magnitude": pl.Float64,
            "bp_rp_color": pl.Float64,
            "distance_gspphot_pc": pl.Float64,
            "is_valid": pl.Boolean,
            "source": pl.String,
        }
    )

    assert frame["is_valid"].to_list() == [True, True]
    assert frame["source"].unique().to_list() == ["gaia_background"]


def test_invalid_background_row_is_retained_but_flagged(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 1, [_raw_row(7), _raw_row(42, ra=400.0), _raw_row(99, latitude=100.0)])

    frame: pl.DataFrame = gaia_background.load(snapshot)

    assert frame.height == 3
    assert frame["gaia_source_id"].to_list() == [7, 42, 99]
    assert frame["is_valid"].to_list() == [True, False, False]


def test_duplicate_background_ids_are_retained_but_invalid(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 1, [_raw_row(7)])
    _write_batch(snapshot, 2, [_raw_row(7)])

    frame: pl.DataFrame = gaia_background.load(snapshot)

    assert frame.height == 2
    assert frame["gaia_source_id"].to_list() == [7, 7]
    assert frame["is_valid"].to_list() == [False, False]


def test_load_rejects_snapshot_without_background_batches(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"
    snapshot.mkdir()

    with pytest.raises(FileNotFoundError, match="Gaia background batch files"):
        gaia_background.load(snapshot)


def test_raw_schema_matches_background_query_columns() -> None:
    assert tuple(gaia_background.RAW_SCHEMA) == GAIA_BACKGROUND_COLUMNS
