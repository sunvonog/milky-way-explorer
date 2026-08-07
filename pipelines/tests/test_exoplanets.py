from pathlib import Path

import polars as pl
import pytest

from app.exoplanets import build_planets, review_invalid_planet_rows
from app.loaders.pscomppars import load

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"


@pytest.fixture(scope="module")
def staging() -> pl.DataFrame:
    return load(SNAPSHOT)


@pytest.fixture(scope="module")
def planets(staging: pl.DataFrame) -> pl.DataFrame:
    return build_planets(staging)


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
