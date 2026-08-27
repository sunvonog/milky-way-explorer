from pathlib import Path

import polars as pl
import pytest

from app.config import REPO_ROOT
from app.loaders import gaia
from app.sources.gaia import GAIA_HOST_COLUMNS

CURRENT_SNAPSHOT = REPO_ROOT / "data" / "raw" / "gaia_hosts" / "current"


def _raw_row(
    source_id: int, *, designation: str | None = None, ra: float = 10.0, dec: float = 20.0
) -> dict[str, object]:
    row: dict[str, object] = dict.fromkeys(GAIA_HOST_COLUMNS)

    row.update(
        {
            "source_id": source_id,
            "designation": designation or f"Gaia DR3 {source_id}",
            "ref_epoch": 2016.0,
            "ra": ra,
            "dec": dec,
            "l": 100.0,
            "b": 30.0,
            "parallax": 5.0,
            "parallax_error": 0.1,
            "parallax_over_error": 50.0,
            "duplicated_source": False,
            "astrometric_params_solved": 31,
            "visibility_periods_used": 12,
            "phot_variable_flag": "NOT_AVAILABLE",
            "non_single_star": 0,
        }
    )

    return row


def _write_batch(
    snapshot: Path,
    batch_number: int,
    rows: list[dict[str, object]],
) -> Path:
    path = snapshot / "batches" / f"gaia-host-{batch_number:04d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(rows).select(GAIA_HOST_COLUMNS).write_csv(path)

    return path


def test_load_combines_normalizes_and_sorts_batches(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 2, [_raw_row(42)])
    _write_batch(snapshot, 1, [_raw_row(7)])

    frame = gaia.load(snapshot)

    assert frame["gaia_source_id"].to_list() == [7, 42]

    assert frame.select(
        [
            "gaia_source_id",
            "gaia_dr3_designation",
            "ra_deg",
            "dec_deg",
            "duplicated_source",
            "is_valid",
            "source",
        ]
    ).schema == pl.Schema(
        {
            "gaia_source_id": pl.Int64,
            "gaia_dr3_designation": pl.String,
            "ra_deg": pl.Float64,
            "dec_deg": pl.Float64,
            "duplicated_source": pl.Boolean,
            "is_valid": pl.Boolean,
            "source": pl.String,
        }
    )

    assert frame["is_valid"].to_list() == [True, True]
    assert frame["source"].unique().to_list() == ["gaia_hosts"]


def test_invalid_gaia_row_is_retained_but_flagged(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 1, [_raw_row(7), _raw_row(42, designation="Gaia DR3 999", ra=400.0)])

    frame = gaia.load(snapshot)

    assert frame.height == 2
    assert frame["gaia_source_id"].to_list() == [7, 42]
    assert frame["is_valid"].to_list() == [True, False]


def test_duplicate_gaia_ids_are_retained_but_invalid(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot, 1, [_raw_row(7)])
    _write_batch(snapshot, 2, [_raw_row(7)])

    frame = gaia.load(snapshot)

    assert frame.height == 2
    assert frame["gaia_source_id"].to_list() == [7, 7]
    assert frame["is_valid"].to_list() == [False, False]


def test_load_rejects_snapshot_without_batches(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"
    snapshot.mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="Gaia batch files",
    ):
        gaia.load(snapshot)


def test_raw_schema_matches_gaia_query_columns() -> None:
    assert tuple(gaia.RAW_SCHEMA) == GAIA_HOST_COLUMNS


def test_current_gaia_host_snapshot_contract() -> None:
    frame = gaia.load(CURRENT_SNAPSHOT)

    assert len(list((CURRENT_SNAPSHOT / "batches").glob("gaia-host-*.csv"))) == 9
    assert frame.height == 4396
    assert frame["gaia_source_id"].n_unique() == 4396
    assert int(frame["is_valid"].sum()) == 4396
