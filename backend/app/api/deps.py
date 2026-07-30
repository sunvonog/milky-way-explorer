from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_processed_root(settings: SettingsDep) -> Path:
    return settings.processed_root


ProcessedRoot = Annotated[Path, Depends(get_processed_root)]
