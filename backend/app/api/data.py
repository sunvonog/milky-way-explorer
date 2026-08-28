"""Serve explicitly published frontend data artifacts."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import FrontendRoot
from app.data.paths import DENSITY_VISUALIZATION_FILE, HOST_VISUALIZATION_FILE

ARROW_FILE_MEDIA_TYPE = "application/vnd.apache.arrow.file"

router = APIRouter(prefix="/data", tags=["data"])


@router.get(f"/{HOST_VISUALIZATION_FILE}")
def host_visualization(frontend_root: FrontendRoot) -> FileResponse:
    """Serve the published exoplanet-host Arrow artifact."""
    path = frontend_root / HOST_VISUALIZATION_FILE

    if not path.is_file():
        raise HTTPException(status_code=503, detail="host visualization is not published")

    return FileResponse(path, media_type=ARROW_FILE_MEDIA_TYPE)


@router.get(f"/{DENSITY_VISUALIZATION_FILE}")
def density_visualization(frontend_root: FrontendRoot) -> FileResponse:
    """Serve the published Milky Way density Arrow artifact."""
    path = frontend_root / DENSITY_VISUALIZATION_FILE

    if not path.is_file():
        raise HTTPException(status_code=503, detail="density visualization is not published")

    return FileResponse(path, media_type=ARROW_FILE_MEDIA_TYPE)
