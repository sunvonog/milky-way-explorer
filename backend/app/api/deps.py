from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

from app.core.config import Settings, get_settings
from app.services.builds import PublishedBuild, resolve_current_build

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_published_build(settings: SettingsDep) -> PublishedBuild:
    """Resolve the immutable build selected for the current request."""
    published_build = resolve_current_build(settings.builds_root)

    if published_build is None:
        raise HTTPException(status_code=503, detail="no published build")

    return published_build


PublishedBuildDep = Annotated[PublishedBuild, Depends(get_published_build)]


def get_processed_root(published_build: PublishedBuildDep) -> Path:
    return published_build.processed_root


ProcessedRoot = Annotated[Path, Depends(get_processed_root)]


def get_frontend_root(published_build: PublishedBuildDep) -> Path:
    return published_build.frontend_root


FrontendRoot = Annotated[Path, Depends(get_frontend_root)]
