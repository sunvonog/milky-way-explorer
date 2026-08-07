"""Pure transformation from PSCompPars staging data to domain tables."""

from __future__ import annotations

import polars as pl

from app.names import search_key

_ID_PREFIX = "nea"


def _search_key_col(column: str) -> pl.Expr:
    return pl.col(column).map_elements(search_key, return_dtype=pl.String)


def _entity_id(kind: str, column: str) -> pl.Expr:
    return pl.lit(f"{_ID_PREFIX}:{kind}:") + _search_key_col(column)


def build_planets(staging: pl.DataFrame) -> pl.DataFrame:
    """Build one normalized planet record per valid PSCompPars row."""
    return (
        staging.filter(pl.col("is_valid"))
        .with_columns(
            planet_id=_entity_id("planet", "planet_name"),
            host_id=_entity_id("host", "host_name"),
            system_id=_entity_id("system", "host_name"),
        )
        .select(
            "planet_id",
            "system_id",
            "host_id",
            "planet_name",
            "planet_letter",
            "radius_earth",
            "mass_earth",
            "mass_provenance",
            "density_g_cm3",
            "equilibrium_temperature_k",
            "insolation_earth",
            "orbital_period_days",
            "semi_major_axis_au",
            "eccentricity",
            "inclination_deg",
            "discovery_method",
            "discovery_year",
            "discovery_facility",
            "is_controversial",
            "source",
        )
        .sort("planet_name")
    )


def review_invalid_planet_rows(staging: pl.DataFrame) -> pl.DataFrame:
    """Retain staging rows excluded from the normalized planet table."""
    return staging.filter(~pl.col("is_valid")).with_columns(
        review_reason=pl.lit("failed PSCompPars staging validation")
    )
