from pathlib import Path

import polars as pl
import pytest

from app.exoplanets import (
    build_hosts,
    build_planets,
    review_host_stellar_conflicts,
    review_invalid_planet_rows,
)
from app.loaders.pscomppars import load

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"


@pytest.fixture(scope="module")
def staging() -> pl.DataFrame:
    return load(SNAPSHOT)


@pytest.fixture(scope="module")
def planets(staging: pl.DataFrame) -> pl.DataFrame:
    return build_planets(staging)


@pytest.fixture(scope="module")
def hosts(staging: pl.DataFrame) -> pl.DataFrame:
    return build_hosts(staging)


@pytest.fixture(scope="module")
def stellar_conflicts(staging: pl.DataFrame) -> pl.DataFrame:
    return review_host_stellar_conflicts(staging)


def test_builds_one_record_per_planet(planets: pl.DataFrame):
    assert planets.height == 6336
    assert planets["planet_id"].n_unique() == 6336
    assert planets["planet_name"].n_unique() == 6336


def test_planet_foreign_keys_are_present(planets: pl.DataFrame):
    assert planets["host_id"].null_count() == 0
    assert planets["system_id"].null_count() == 0

    assert planets["host_id"].str.starts_with("nea:host").all()
    assert planets["system_id"].str.starts_with("nea:system").all()


def test_known_planet_identity(planets: pl.DataFrame):
    planet = planets.filter(pl.col("planet_name") == "11 Com b").row(0, named=True)

    assert planet["planet_id"] == "nea:planet:11comb"
    assert planet["host_id"] == "nea:host:11com"
    assert planet["system_id"] == "nea:system:11com"
    assert planet["mass_provenance"] == "Msini"


def test_invalid_rows_are_excluded_and_retained_for_review(
    staging: pl.DataFrame,
):
    invalid = staging.head(1).with_columns(is_valid=pl.lit(False))

    planets = build_planets(invalid)
    review = review_invalid_planet_rows(invalid)

    assert planets.is_empty()
    assert review.height == 1
    assert review["review_reason"][0] == ("failed PSCompPars staging validation")


def test_builds_one_record_per_host(hosts: pl.DataFrame):
    assert hosts.height == 4749
    assert hosts["host_id"].n_unique() == 4749
    assert hosts["host_name"].n_unique() == 4749
    assert hosts["host_id"].str.starts_with("nea:host:").all()


def test_gaia_ids_remain_unique_per_host(hosts: pl.DataFrame):
    gaia_ids = hosts["gaia_source_id"].drop_nulls()

    assert gaia_ids.n_unique() == 4396


def test_stable_host_fields_do_not_vary(staging: pl.DataFrame):
    stable_fields = (
        "ra_deg",
        "dec_deg",
        "system_distance_pc",
        "star_count",
        "planet_count",
        "is_circumbinary",
        "hd_name",
        "hip_name",
        "tic_id",
        "gaia_source_id",
    )

    for field in stable_fields:
        variants = (
            staging.group_by("host_name")
            .agg(pl.col(field).drop_nulls().n_unique().alias("variants"))["variants"]
            .max()
        )

        assert isinstance(variants, int)
        assert variants <= 1


def test_conflicting_host_uses_deterministic_source(hosts: pl.DataFrame):
    host = hosts.filter(pl.col("host_name") == "55 Cnc").row(0, named=True)

    assert host["host_id"] == "nea:host:55cnc"
    assert host["stellar_source_planet_name"] == "55 Cnc b"
    assert host["stellar_selection_method"] == ("most_complete_then_planet_name")
    assert host["stellar_fields_available"] == 4
    assert host["stellar_values_conflict"] is True
    assert host["stellar_temperature_k"] == 5198.0
    assert host["stellar_mass_solar"] == 1.015


def test_stellar_conflicts_are_preserved_for_review(
    stellar_conflicts: pl.DataFrame,
):
    assert stellar_conflicts.height == 596
    assert stellar_conflicts["host_id"].n_unique() == 211
    assert int(stellar_conflicts["is_selected"].sum()) == 211

    fifty_five_cnc = stellar_conflicts.filter(pl.col("host_name") == "55 Cnc")

    assert fifty_five_cnc.height == 5
    assert fifty_five_cnc.filter(pl.col("is_selected"))["source_planet_name"][0] == "55 Cnc b"
