"""Pure transformation from PSCompPars staging data to domain tables."""

from __future__ import annotations

import polars as pl

from app.domain.names import search_key

_ID_PREFIX = "nea"

_STELLAR_FIELDS = (
    "stellar_temperature_k",
    "stellar_mass_solar",
    "stellar_radius_solar",
    "stellar_luminosity_log_solar",
)

_STELLAR_COUNT_FIELDS = tuple(f"{field}_value_count" for field in _STELLAR_FIELDS)


def _search_key_col(column: str) -> pl.Expr:
    return pl.col(column).map_elements(search_key, return_dtype=pl.String)


def _entity_id(kind: str, column: str) -> pl.Expr:
    return pl.lit(f"{_ID_PREFIX}:{kind}:") + _search_key_col(column)


def _host_candidates(staging: pl.DataFrame) -> pl.DataFrame:
    """Rank valid source rows for deterministic host selection."""
    completeness = [pl.col(field).is_not_null().cast(pl.UInt8) for field in _STELLAR_FIELDS]

    return (
        staging.filter(pl.col("is_valid"))
        .with_columns(
            host_id=_entity_id("host", "host_name"),
            stellar_completeness=pl.sum_horizontal(*completeness),
        )
        .sort(
            ["host_name", "stellar_completeness", "planet_name"],
            descending=[False, True, False],
        )
    )


def _stellar_conflict_summary(candidates: pl.DataFrame) -> pl.DataFrame:
    """Count distinct non-null stellar values for every host."""
    value_counts = [
        pl.col(field).drop_nulls().n_unique().alias(f"{field}_value_count")
        for field in _STELLAR_FIELDS
    ]

    conflict_tests = [pl.col(field) > 1 for field in _STELLAR_COUNT_FIELDS]

    return (
        candidates.group_by(["host_id", "host_name"])
        .agg(value_counts)
        .with_columns(stellar_values_conflict=pl.any_horizontal(*conflict_tests))
    )


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


def build_hosts(staging: pl.DataFrame) -> pl.DataFrame:
    """Build one deterministic host record per valid host name."""
    candidates = _host_candidates(staging)
    conflicts = _stellar_conflict_summary(candidates)

    selected = candidates.unique(subset=["host_id"], keep="first", maintain_order=True)

    return (
        selected.join(
            conflicts.select("host_id", "stellar_values_conflict"),
            on="host_id",
            how="left",
        )
        .with_columns(
            stellar_source_planet_name=pl.col("planet_name"),
            stellar_fields_available=pl.col("stellar_completeness"),
            stellar_selection_method=pl.lit("most_complete_then_planet_name"),
        )
        .select(
            "host_id",
            "host_name",
            "hd_name",
            "hip_name",
            "tic_id",
            "gaia_dr3_designation",
            "gaia_source_id",
            "ra_deg",
            "dec_deg",
            "system_distance_pc",
            "star_count",
            "planet_count",
            "is_circumbinary",
            *_STELLAR_FIELDS,
            "stellar_fields_available",
            "stellar_source_planet_name",
            "stellar_selection_method",
            "stellar_values_conflict",
            "source",
        )
        .sort("host_name")
    )


def review_host_stellar_conflicts(
    staging: pl.DataFrame,
) -> pl.DataFrame:
    """Preserve every source candidate for hosts with conflicting values."""
    candidates = _host_candidates(staging)
    conflicts = _stellar_conflict_summary(candidates).filter(pl.col("stellar_values_conflict"))

    selected = candidates.unique(
        subset=["host_id"],
        keep="first",
        maintain_order=True,
    ).select(
        "host_id",
        pl.col("planet_name").alias("selected_source_planet_name"),
    )

    return (
        candidates.join(
            conflicts,
            on=["host_id", "host_name"],
            how="inner",
        )
        .join(selected, on="host_id", how="left")
        .with_columns(
            is_selected=(pl.col("planet_name") == pl.col("selected_source_planet_name")),
            review_reason=pl.lit("stellar properties differ between planet rows"),
        )
        .select(
            "host_id",
            "host_name",
            pl.col("planet_name").alias("source_planet_name"),
            "selected_source_planet_name",
            "is_selected",
            pl.col("stellar_completeness").alias("stellar_fields_available"),
            *_STELLAR_FIELDS,
            *_STELLAR_COUNT_FIELDS,
            "review_reason",
            "source",
        )
        .sort(["host_name", "source_planet_name"])
    )


def build_systems(
    hosts: pl.DataFrame,
    planets: pl.DataFrame,
) -> pl.DataFrame:
    """Build one provisional system per exact host name."""
    planet_counts = planets.group_by("host_id").agg(pl.len().cast(pl.Int16).alias("planet_count"))

    systems = (
        hosts.select(
            "host_id",
            "host_name",
            "system_distance_pc",
            "star_count",
            pl.col("planet_count").alias("archive_planet_count"),
            "is_circumbinary",
            "source",
        )
        .with_columns(system_id=_entity_id("system", "host_name"))
        .join(planet_counts, on="host_id", how="left")
        .with_columns(
            planet_count=(pl.col("planet_count").fill_null(0).cast(pl.Int16)),
            system_grouping_method=pl.lit("exact_host_name"),
        )
        .with_columns(
            planet_count_matches_archive=(pl.col("planet_count") == pl.col("archive_planet_count"))
        )
    )

    return systems.select(
        "system_id",
        "host_id",
        "host_name",
        "star_count",
        "planet_count",
        "archive_planet_count",
        "planet_count_matches_archive",
        "system_distance_pc",
        "is_circumbinary",
        "system_grouping_method",
        "source",
    ).sort("host_name")


def review_system_planet_count_mismatches(
    systems: pl.DataFrame,
) -> pl.DataFrame:
    """Retain systems whose exact-host rows differ from NASA's count."""
    return (
        systems.filter(~pl.col("planet_count_matches_archive"))
        .with_columns(
            planet_count_difference=(pl.col("planet_count") - pl.col("archive_planet_count")),
            review_reason=pl.lit(
                "archive system planet count differs from rows grouped by exact host name"
            ),
        )
        .select(
            "system_id",
            "host_id",
            "host_name",
            "star_count",
            "planet_count",
            "archive_planet_count",
            "planet_count_difference",
            "is_circumbinary",
            "system_grouping_method",
            "review_reason",
            "source",
        )
        .sort("host_name")
    )
