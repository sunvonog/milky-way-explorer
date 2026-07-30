from pydantic import BaseModel

from app.services.search import SearchHit


class SearchResult(BaseModel):
    star_id: str
    display_name: str
    matched_alias: str
    catalogue: str
    is_exact: bool
    ra_deg: float | None = None
    dec_deg: float | None = None

    @classmethod
    def from_hit(cls, hit: SearchHit) -> "SearchResult":
        return cls(
            star_id=hit.star_id,
            display_name=hit.display_name,
            matched_alias=hit.matched_alias,
            catalogue=hit.catalogue,
            is_exact=hit.is_exact,
            ra_deg=hit.ra_deg,
            dec_deg=hit.dec_deg,
        )
