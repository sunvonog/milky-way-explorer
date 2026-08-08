import pytest

from app.gaia import GaiaHostBatch
from app.sources.gaia import GAIA_HOST_COLUMNS, GAIA_SOURCE_TABLE, gaia_host_query


def test_gaia_host_columns_match_enrichment_contract():
    assert GAIA_HOST_COLUMNS == (
        "source_id",
        "designation",
        "ref_epoch",
        "ra",
        "dec",
        "l",
        "b",
        "parallax",
        "parallax_error",
        "parallax_over_error",
        "pm",
        "pmra",
        "pmra_error",
        "pmdec",
        "pmdec_error",
        "radial_velocity",
        "radial_velocity_error",
        "phot_g_mean_mag",
        "phot_bp_mean_mag",
        "phot_rp_mean_mag",
        "bp_rp",
        "ruwe",
        "duplicated_source",
        "astrometric_params_solved",
        "visibility_periods_used",
        "phot_variable_flag",
        "non_single_star",
        "teff_gspphot",
        "distance_gspphot",
        "distance_gspphot_lower",
        "distance_gspphot_upper",
    )


def test_gaia_host_query_selects_one_exact_batch():
    batch = GaiaHostBatch(
        batch_number=3,
        source_ids=(7, 42),
    )

    query = gaia_host_query(batch)

    assert "SELECT *" not in query
    assert query.startswith("SELECT source_id,designation,ref_epoch")
    assert f"FROM {GAIA_SOURCE_TABLE}" in query
    assert "WHERE source_id IN (7,42)" in query
    assert query.endswith("ORDER BY source_id")


def test_gaia_host_query_has_no_duplicate_columns():
    assert len(GAIA_HOST_COLUMNS) == len(set(GAIA_HOST_COLUMNS))


def test_gaia_host_query_rejects_empty_batch():
    batch = GaiaHostBatch(batch_number=1, source_ids=())

    with pytest.raises(ValueError, match="Gaia host batch must not be empty"):
        gaia_host_query(batch)
