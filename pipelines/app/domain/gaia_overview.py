from dataclasses import dataclass
from hashlib import blake2b
from math import isfinite

import polars as pl

GAIA_OVERVIEW_SAMPLING_METHOD = "blake2b-64-v1"

GAIA_OVERVIEW_COLUMNS = (
    "gaia_source_id",
    "galactocentric_x_kpc",
    "galactocentric_y_kpc",
    "galactocentric_z_kpc",
    "phot_g_mean_magnitude",
    "bp_rp_color",
    "distance_pc",
    "distance_method",
    "distance_quality",
    "distance_tier",
)


@dataclass(frozen=True, slots=True)
class GaiaOverviewResult:
    """Selected records and counts from the processed-source input."""

    records: pl.DataFrame
    input_count: int
    eligible_count: int

    @property
    def selected_count(self) -> int:
        return self.records.height

    @property
    def excluded_count(self) -> int:
        return self.input_count - self.eligible_count

    @property
    def sampled_out_count(self) -> int:
        return self.eligible_count - self.selected_count


# Use an explicit hash rule so sampling does not depend on input row order
# or Polars' random-sampling implementation. For the same eligible IDs and
# seed, taking more ranked records extends the existing sample.
# Keep the payload encoding, digest size, and byte order stable.
def _sample_rank(source_id: int, seed: int) -> int:
    payload = f"{seed}:{source_id}".encode("ascii")
    digest = blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big")


def select_gaia_overview_sources(sources: pl.DataFrame, *, extent_kpc: float) -> pl.DataFrame:
    """Keep supported sources inside the half-open x-y map extent."""
    if not isfinite(extent_kpc) or extent_kpc <= 0:
        raise ValueError("extent_kpc must be finite and positive")

    x = pl.col("galactocentric_x_kpc")
    y = pl.col("galactocentric_y_kpc")

    valid_position = pl.all_horizontal(
        pl.col("galactocentric_x_kpc", "galactocentric_y_kpc", "galactocentric_z_kpc").is_finite()
    )

    within_extent = (x >= -extent_kpc) & (x < extent_kpc) & (y >= -extent_kpc) & (y < extent_kpc)

    supported_tier = pl.col("distance_tier").is_in(["baseline", "exploratory"])

    return sources.filter((valid_position & within_extent & supported_tier).fill_null(False))


def sample_gaia_overview(sources: pl.DataFrame, *, max_points: int, seed: int) -> pl.DataFrame:
    """Sample eligible sources with unique, non-null Int64 Gaia IDs."""
    if max_points <= 0:
        raise ValueError("max_points must be positive")

    if seed < 0:
        raise ValueError("seed must be non-negative")

    ranks = pl.Series(
        "_sample_rank",
        (_sample_rank(source_id, seed) for source_id in sources["gaia_source_id"]),
        dtype=pl.UInt64,
    )

    return (
        sources.with_columns(ranks)
        .sort("_sample_rank", "gaia_source_id")
        .head(max_points)
        .drop("_sample_rank")
    )


def build_gaia_overview(
    sources: pl.DataFrame, *, extent_kpc: float, max_points: int, seed: int
) -> GaiaOverviewResult:
    """Filter processed sources, sample eligible rows, and retain counts."""
    eligible = select_gaia_overview_sources(sources, extent_kpc=extent_kpc)
    records = sample_gaia_overview(eligible, max_points=max_points, seed=seed)

    return GaiaOverviewResult(
        records=records, input_count=sources.height, eligible_count=eligible.height
    )
