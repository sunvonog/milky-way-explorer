"""Pure transformations supporting Gaia host enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import astropy.units as u
import polars as pl
from astropy.coordinates import Galactocentric, SkyCoord, galactocentric_frame_defaults

_DEGREES_TO_RADIANS = pi / 180.0

GALACTOCENTRIC_PARAMETER_SET = "v4.0"

GAIA_HOST_SOURCE_COLUMNS = (
    "gaia_source_id",
    "gaia_dr3_designation",
    "reference_epoch",
    "ra_deg",
    "dec_deg",
    "galactic_longitude_deg",
    "galactic_latitude_deg",
    "parallax_mas",
    "parallax_error_mas",
    "parallax_over_error",
    "proper_motion_mas_per_year",
    "proper_motion_ra_mas_per_year",
    "proper_motion_ra_error_mas_per_year",
    "proper_motion_dec_mas_per_year",
    "proper_motion_dec_error_mas_per_year",
    "radial_velocity_km_per_s",
    "radial_velocity_error_km_per_s",
    "phot_g_mean_magnitude",
    "phot_bp_mean_magnitude",
    "phot_rp_mean_magnitude",
    "bp_rp_color",
    "ruwe",
    "duplicated_source",
    "astrometric_params_solved",
    "visibility_periods_used",
    "phot_variable_flag",
    "non_single_star",
    "temperature_gspphot_k",
    "distance_gspphot_pc",
    "distance_gspphot_lower_pc",
    "distance_gspphot_upper_pc",
    "distance_pc",
    "distance_lower_pc",
    "distance_upper_pc",
    "distance_method",
    "distance_quality",
    "heliocentric_x_pc",
    "heliocentric_y_pc",
    "heliocentric_z_pc",
    "galactocentric_x_kpc",
    "galactocentric_y_kpc",
    "galactocentric_z_kpc",
    "source",
)

GAIA_BACKGROUND_SOURCE_COLUMNS = (
    "gaia_source_id",
    "distance_pc",
    "distance_method",
    "distance_quality",
    "galactocentric_x_kpc",
    "galactocentric_y_kpc",
    "galactocentric_z_kpc",
    "phot_g_mean_magnitude",
    "bp_rp_color",
    "source",
)


@dataclass(frozen=True, slots=True)
class GaiaHostBatch:
    """One deterministic unit of exact Gaia source retrieval."""

    batch_number: int
    source_ids: tuple[int, ...]


def build_gaia_host_ids(hosts: pl.DataFrame) -> pl.DataFrame:
    """Build the distinct Gaia source-ID manifest for exoplanet hosts."""
    return (
        hosts.select(pl.col("gaia_source_id").cast(pl.Int64))
        .drop_nulls()
        .unique()
        .sort("gaia_source_id")
    )


def plan_gaia_host_batches(host_ids: pl.DataFrame, *, batch_size: int) -> list[GaiaHostBatch]:
    """Split canonical Gaia host IDs into stable, bounded batches."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    source_ids: list[int] = build_gaia_host_ids(host_ids).get_column("gaia_source_id").to_list()

    return [
        GaiaHostBatch(
            batch_number=batch_number, source_ids=tuple(source_ids[start : start + batch_size])
        )
        for batch_number, start in enumerate(
            range(0, len(source_ids), batch_size),
            start=1,
        )
    ]


def _has_positive_gspphot_distance() -> pl.Expr:
    return (
        pl.col("distance_gspphot_pc").is_not_null() & (pl.col("distance_gspphot_pc") > 0)
    ).fill_null(False)


def _has_qualified_parallax() -> pl.Expr:
    return (
        (pl.col("parallax_mas") > 0)
        & (pl.col("parallax_over_error") >= 5)
        & (pl.col("ruwe").is_null() | (pl.col("ruwe") < 1.4))
    ).fill_null(False)


def _add_gaia_selected_distance(frame: pl.DataFrame) -> pl.DataFrame:
    """Select a distance with shared method and quality provenance."""
    has_gspphot = _has_positive_gspphot_distance()
    has_qualified_parallax = _has_qualified_parallax()

    return frame.with_columns(
        distance_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_pc"))
            .when(has_qualified_parallax)
            .then(1000.0 / pl.col("parallax_mas"))
            .otherwise(None)
        ),
        distance_method=(
            pl.when(has_gspphot)
            .then(pl.lit("gaia_gspphot"))
            .when(has_qualified_parallax)
            .then(pl.lit("inverse_parallax"))
            .otherwise(pl.lit("unavailable"))
        ),
        distance_quality=(
            pl.when(has_gspphot)
            .then(pl.lit("positive_gspphot_estimate"))
            .when(has_qualified_parallax)
            .then(pl.lit("snr_ge_5_ruwe_acceptable"))
            .otherwise(pl.lit("unavailable"))
        ),
    )


def add_gaia_distance(frame: pl.DataFrame) -> pl.DataFrame:
    """Select a host distance and add available uncertainty bounds."""
    has_gspphot = _has_positive_gspphot_distance()
    has_qualified_parallax = _has_qualified_parallax()

    has_parallax_bounds = (
        has_qualified_parallax
        & (pl.col("parallax_error_mas") > 0)
        & (pl.col("parallax_mas") - pl.col("parallax_error_mas") > 0)
    ).fill_null(False)

    return _add_gaia_selected_distance(frame).with_columns(
        distance_lower_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_lower_pc"))
            .when(has_parallax_bounds)
            .then(1000.0 / (pl.col("parallax_mas") + pl.col("parallax_error_mas")))
            .otherwise(None)
        ),
        distance_upper_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_upper_pc"))
            .when(has_parallax_bounds)
            .then(1000.0 / (pl.col("parallax_mas") - pl.col("parallax_error_mas")))
            .otherwise(None)
        ),
    )


def build_gaia_host_sources(staging: pl.DataFrame) -> pl.DataFrame:
    """Build one published Gaia source record per valid host source ID."""
    return (
        staging.filter(pl.col("is_valid"))
        .pipe(add_gaia_distance)
        .pipe(add_heliocentric_coordinates)
        .pipe(add_galactocentric_coordinates)
        .select(*GAIA_HOST_SOURCE_COLUMNS)
        .sort("gaia_source_id")
    )


def build_gaia_background_sources(staging: pl.DataFrame) -> pl.DataFrame:
    """Build density-ready Gaia sources from valid background rows."""
    return (
        staging.filter(pl.col("is_valid"))
        .pipe(_add_gaia_selected_distance)
        .pipe(add_galactocentric_coordinates)
        .select(*GAIA_BACKGROUND_SOURCE_COLUMNS)
        .sort("gaia_source_id")
    )


def add_heliocentric_coordinates(frame: pl.DataFrame) -> pl.DataFrame:
    """Add sun-centred Galactic Cartesian coordinates in parsecs."""
    longitude_rad = pl.col("galactic_longitude_deg") * _DEGREES_TO_RADIANS
    latitude_rad = pl.col("galactic_latitude_deg") * _DEGREES_TO_RADIANS
    distance = pl.col("distance_pc")

    return frame.with_columns(
        heliocentric_x_pc=(distance * latitude_rad.cos() * longitude_rad.cos()),
        heliocentric_y_pc=(distance * latitude_rad.cos() * longitude_rad.sin()),
        heliocentric_z_pc=(distance * latitude_rad.sin()),
    )


def add_galactocentric_coordinates(frame: pl.DataFrame) -> pl.DataFrame:
    """Add Milky-Way-centred Cartesian positions in kiloparsecs.

    The origin is the centre of the Milky Way. Astropy's right-handed
    Galactocentric convention places the sun near
    ``(-8.122, 0, 0.0208)`` kpc. The positive x-axis points from the
    Sun's projected position toward the Galactic centre, positive y
    points approximately toward Galactic longitude 90 degrees, and
    positive z points approximately toward the north Galactic pole.

    The transformation explicitly uses Astropy's named ``v4.0``
    parameter set instead of the library's ambient default:

        - Galactic-centre ICRS coordinates come from Reid & Brunthaler
              (2004): https://ui.adsabs.harvard.edu/abs/2004ApJ...616..872R
        - Sun–Galactic-centre distance, 8.122 kpc, comes from the GRAVITY
            Collaboration (2018):
            https://ui.adsabs.harvard.edu/abs/2018A%26A...615L..15G
        - Solar height, 20.8 pc, comes from Bennett & Bovy (2019):
            https://ui.adsabs.harvard.edu/abs/2019MNRAS.482.1417B

    Astropy exposes these references through
    ``galactocentric_frame_defaults.get_from_registry("v4.0")``.
    Freezing the named set prevents library-default changes from
    silently moving published positions.
    """
    indexed = frame.with_row_index("_coordinate_row")

    valid = indexed.filter(
        pl.all_horizontal(
            pl.col("galactic_longitude_deg", "galactic_latitude_deg", "distance_pc").is_not_null()
        )
    )

    if valid.is_empty():
        return frame.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("galactocentric_x_kpc"),
            pl.lit(None, dtype=pl.Float64).alias("galactocentric_y_kpc"),
            pl.lit(None, dtype=pl.Float64).alias("galactocentric_z_kpc"),
        )

    coordinates = SkyCoord(
        l=valid["galactic_longitude_deg"].to_numpy() * u.deg,
        b=valid["galactic_latitude_deg"].to_numpy() * u.deg,
        distance=valid["distance_pc"].to_numpy() * u.pc,
        frame="galactic",
    )

    with galactocentric_frame_defaults.set(GALACTOCENTRIC_PARAMETER_SET):
        transformed = coordinates.transform_to(Galactocentric())

    cartesian = transformed.cartesian

    positions = valid.select("_coordinate_row").with_columns(
        pl.Series("galactocentric_x_kpc", cartesian.x.to_value(u.kpc)),
        pl.Series("galactocentric_y_kpc", cartesian.y.to_value(u.kpc)),
        pl.Series("galactocentric_z_kpc", cartesian.z.to_value(u.kpc)),
    )

    return (
        indexed.join(positions, on="_coordinate_row", how="left")
        .sort("_coordinate_row")
        .drop("_coordinate_row")
    )
