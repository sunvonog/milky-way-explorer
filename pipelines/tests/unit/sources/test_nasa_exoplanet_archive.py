from urllib.parse import parse_qs, urlparse

from app.sources.nasa_exoplanet_archive import (
    PSCOMPPARS_COLUMNS,
    pscomppars_query,
    pscomppars_url,
)


def test_query_selects_explicit_columns():
    """Test query selects explicit columns."""
    query = pscomppars_query()

    assert "SELECT *" not in query
    assert query.startswith("SELECT pl_name,hostname")
    assert "gaia_dr3_id" in query
    assert "pl_bmassprov" in query
    assert query.endswith("FROM pscomppars ORDER BY pl_name")


def test_query_columns_are_unique():
    assert len(PSCOMPPARS_COLUMNS) == len(set(PSCOMPPARS_COLUMNS))


def test_url_contains_encoded_query_and_csv_format():
    parsed = urlparse(pscomppars_url())
    parameters = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "exoplanetarchive.ipac.caltech.edu"
    assert parameters["format"] == ["csv"]
    assert parameters["query"] == [pscomppars_query()]


def test_required_scientific_columns_are_present():
    required = {
        "sy_snum",
        "sy_pnum",
        "pl_insol",
        "pl_orbper",
        "pl_orbsmax",
    }

    assert required <= set(PSCOMPPARS_COLUMNS)
