from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ProcessedRoot, SettingsDep
from app.data.paths import BuildNotPublishedError
from app.schemas.search import SearchResult
from app.services.search import search as run_search

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResult])
def search_endpoint(
    processed_root: ProcessedRoot,
    settings: SettingsDep,
    q: str = Query(min_length=1, max_length=100, description="Name, alias, or catalogue ID"),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[SearchResult]:
    try:
        hits = run_search(processed_root, q, limit, settings.duckdb_memory_limit)
    except BuildNotPublishedError as exc:
        raise HTTPException(status_code=503, detail="no published build") from exc

    return [SearchResult.from_hit(hit) for hit in hits]
