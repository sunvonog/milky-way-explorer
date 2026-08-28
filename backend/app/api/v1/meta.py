from fastapi import APIRouter

from app.api.deps import PublishedBuildDep
from app.schemas.meta import BuildResponse, HealthResponse

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness only - deliberately does not touch the filesystem, so a missing
    data build never triggers a deployment rollback."""
    return HealthResponse(status="ok")


@router.get("/build", response_model=BuildResponse)
def build(published_build: PublishedBuildDep) -> BuildResponse:
    info = published_build.info

    return BuildResponse(
        build_id=info.build_id,
        created_at=info.created_at,
        source_snapshots=info.source_snapshots,
        row_counts=info.row_counts,
    )
