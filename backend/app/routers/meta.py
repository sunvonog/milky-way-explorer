from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.builds import BuildInfo, read_current_build
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["meta"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/build", response_model=BuildInfo)
def build(settings: SettingsDep) -> BuildInfo:
    info = read_current_build(settings.current_pointer)
    if info is None:
        raise HTTPException(status_code=503, detail="no published build")

    return info
