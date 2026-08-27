from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest

from app.artifacts import (
    EXOPLANET_HOSTS_FILENAME,
    EXOPLANET_SYSTEMS_FILENAME,
    GAIA_HOST_SOURCES_FILENAME,
    HOST_VISUALIZATION_FILENAME,
)
from app.config import override_settings, reset_settings
from app.flows.visualization import build_host_visualization


@pytest.fixture
def data_root(tmp_path: Path) -> Iterator[Path]:
    reset_settings()
    override_settings(
        data_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_level="WARNING",
        log_color=False,
        strict_checks=True,
    )

    processed = tmp_path / "processed"
    processed.mkdir(parents=True)

    pl.DataFrame(
        {
            "host_id": [
                "nea:host:gamma",
                "nea:host:alpha",
                "nea:host:beta",
            ],
            "host_name": ["Gamma", "Alpha", "Beta"],
            "gaia_source_id": [None, 101, 202],
            "is_circumbinary": [False, False, True],
        },
        schema_overrides={"gaia_source_id": pl.Int64},
    ).write_parquet(processed / EXOPLANET_HOSTS_FILENAME)

    pl.DataFrame(
        {
            "host_id": [
                "nea:host:beta",
                "nea:host:gamma",
                "nea:host:alpha",
            ],
            "planet_count": [1, 4, 2],
            "archive_planet_count": [1, 4, 3],
            "planet_count_matches_archive": [True, True, False],
        }
    ).write_parquet(processed / EXOPLANET_SYSTEMS_FILENAME)

    pl.DataFrame(
        {
            "gaia_source_id": [202, 101],
            "distance_pc": [None, 10.0],
            "distance_method": ["unavailable", "inverse_parallax"],
            "distance_quality": ["unavailable", "snr_ge_5_ruwe_acceptable"],
            "heliocentric_x_pc": [None, 10.0],
            "heliocentric_y_pc": [None, 0.0],
            "heliocentric_z_pc": [None, 0.0],
            "galactocentric_x_kpc": [None, -8.112],
            "galactocentric_y_kpc": [None, 0.0],
            "galactocentric_z_kpc": [None, 0.0208],
            "phot_g_mean_magnitude": [12.0, 7.2],
            "bp_rp_color": [None, 0.8],
        },
        schema_overrides={
            "gaia_source_id": pl.Int64,
            "distance_pc": pl.Float64,
            "heliocentric_x_pc": pl.Float64,
            "heliocentric_y_pc": pl.Float64,
            "heliocentric_z_pc": pl.Float64,
            "galactocentric_x_kpc": pl.Float64,
            "galactocentric_y_kpc": pl.Float64,
            "galactocentric_z_kpc": pl.Float64,
            "phot_g_mean_magnitude": pl.Float64,
            "bp_rp_color": pl.Float64,
        },
    ).write_parquet(processed / GAIA_HOST_SOURCES_FILENAME)

    yield tmp_path

    reset_settings()


def test_build_host_visualization_publishes_arrow(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.flows.visualization.EXPECTED_POSITION_STATUS_COUNTS",
        {"available": 1, "no_accepted_distance": 1, "no_exact_gaia_source": 1},
    )

    path = build_host_visualization()

    assert path == data_root / "frontend" / HOST_VISUALIZATION_FILENAME
    assert path.is_file()

    records = pl.read_ipc(path)

    assert records.height == 3
    assert records["host_id"].to_list() == ["nea:host:alpha", "nea:host:beta", "nea:host:gamma"]

    assert dict(records.group_by("position_status").len().iter_rows()) == {
        "available": 1,
        "no_accepted_distance": 1,
        "no_exact_gaia_source": 1,
    }


@pytest.mark.parametrize(
    "missing_filename",
    [EXOPLANET_HOSTS_FILENAME, EXOPLANET_SYSTEMS_FILENAME, GAIA_HOST_SOURCES_FILENAME],
)
def test_build_host_visualization_requires_all_processed_inputs(
    data_root: Path,
    missing_filename: str,
) -> None:
    (data_root / "processed" / missing_filename).unlink()

    with pytest.raises(FileNotFoundError, match=missing_filename):
        build_host_visualization()
