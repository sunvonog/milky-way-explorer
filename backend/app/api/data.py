"""Serve explicitly published frontend data artifacts."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import SettingsDep
from app.data.paths import HOST_VISUALIZATION_FILE

ARROW_FILE_MEDIA_TYPE = "application/vnd.apache.arrow.file"

router = APIRouter(prefix="/data", tags=["data"])


@router.get(f"/{HOST_VISUALIZATION_FILE}")
def host_visualization(settings: SettingsDep) -> FileResponse:
    """Serve the published exoplanet-host Arrow artifact."""
    path = settings.frontend_root / HOST_VISUALIZATION_FILE

    if not path.is_file():
        raise HTTPException(status_code=503, detail="host visualization is not published")

    return FileResponse(path, media_type=ARROW_FILE_MEDIA_TYPE)
