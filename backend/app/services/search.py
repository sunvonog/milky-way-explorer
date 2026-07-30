"""Name resolution over the canonical alias table."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.names import search_key
from app.data.duckdb import open_views
from app.data.paths import ALIAS_FILE, STARS_FILE

_VIEWS = {"stars": STARS_FILE, "alias": ALIAS_FILE}

# DISTINCT ON collapses multiple alias matches per star to one row. The inner
# ORDER BY must lead with star_id - that decides which alias survives per group.
# The outer ORDER BY then ranks stars against each other.
_SQL = """
WITH q AS (SELECT ? AS KEY),
matches AS (
    SELECT DISTINCT ON (a.star_id)
        a.star_id                       AS star_id,
        s.canonical_display_name        AS display_name,
        a.alias                         AS matched_alias,
        a.catalogue                     AS catalogue,
        a.priority                      AS priority,
        (a.alias_search_key = q.key)    AS is_exact,
        length(a.alias_search_key)      AS alias_len,
        s.ra_deg                        AS ra_deg,
        s.dec_deg                       AS dec_deg,
    FROM alias AS a
    JOIN stars AS s USING (star_id)
    CROSS JOIN q
    WHERE a.alias_search_key = q.key
        OR a.alias_search_key LIKE q.key || '%'
    ORDER BY
        a.star_id,
        (a.alias_search_key = q.key) DESC,
        a.priority ASC,
        length(a.alias_search_key) ASC
)
SELECT star_id, display_name, matched_alias, catalogue, is_exact, ra_deg, dec_deg
FROM matches
ORDER BY is_exact DESC, priority ASC, alias_len ASC, display_name ASC
LIMIT ?
"""


@dataclass(frozen=True, slots=True)
class SearchHit:
    """Hit a star with the search."""

    star_id: str
    display_name: str
    matched_alias: str
    catalogue: str
    is_exact: bool
    ra_deg: float | None
    dec_deg: float | None


def search(
    processed_root: Path, query: str, limit: int = 20, memory_limit: str = "512MB"
) -> list[SearchHit]:
    """Resolve free text to canonical stars, best match first.

    Raises BuildNotPublishedError when the build files are absent.
    """
    key = search_key(query)
    if not key:
        return []

    with open_views(processed_root, _VIEWS, memory_limit) as con:
        rows = con.execute(_SQL, [key, limit]).fetchall()

    return [
        SearchHit(
            star_id=r[0],
            display_name=r[1],
            matched_alias=r[2],
            catalogue=r[3],
            is_exact=bool(r[4]),
            ra_deg=r[5],
            dec_deg=r[6],
        )
        for r in rows
    ]
