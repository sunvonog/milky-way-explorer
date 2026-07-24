import json
from pathlib import Path

from pydantic import BaseModel


class BuildInfo(BaseModel):
    build_id: str
    created_at: str
    source_snapshots: dict[str, str]
    row_counts: dict[str, int]


def read_current_build(pointer: Path) -> BuildInfo | None:
    """Resolve the active build. Returns None when no build is published."""
    try:
        raw = pointer.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return BuildInfo.model_validate(json.loads(raw))
