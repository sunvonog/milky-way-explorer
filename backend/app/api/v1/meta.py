from fastapi import APIRouter, HTTPException

from app.api.deps import SettingsDep
from app.schemas.meta import BuildResponse, HealthResponse
from app.services.builds import read_current_build

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness only - deliberately does not touch the filesystem, so a missing
    data build never triggers a deployment rollback."""
    return HealthResponse(status="ok")


@router.get("/build", response_model=BuildResponse)
def build(settings: SettingsDep) -> BuildResponse:
    info = read_current_build(settings.current_pointer)
    if info is None:
        raise HTTPException(status_code=503, detail="no published build")

    return BuildResponse(
        build_id=info.build_id,
        created_at=info.created_at,
        source_snapshots=info.source_snapshots,
        row_counts=info.row_counts,
    )
