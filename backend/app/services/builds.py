import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


class BuildInfo(BaseModel):
    build_id: str
    created_at: str
    source_snapshots: dict[str, str]
    row_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class PublishedBuild:
    """One complete immutable build selected by current.json"""

    info: BuildInfo
    root: Path

    @property
    def processed_root(self) -> Path:
        return self.root / "processed"

    @property
    def frontend_root(self) -> Path:
        return self.root / "frontend"


def read_current_build(pointer: Path) -> BuildInfo | None:
    """Resolve the active build. Returns None when no build is published."""
    try:
        raw = pointer.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    return BuildInfo.model_validate(json.loads(raw))


def resolve_current_build(builds_root: Path) -> PublishedBuild | None:
    """Resolve and validate the immutable build selected by current.json."""
    try:
        info = read_current_build(builds_root / "current.json")
    except (OSError, ValueError):
        return None

    if info is None:
        return None

    resolved_builds_root = builds_root.resolve()
    build_root = (builds_root / info.build_id).resolve()

    # Reject traversal, nested paths, and symlinks escaping builds_root
    if build_root.parent != resolved_builds_root:
        return None

    if not build_root.is_dir():
        return None

    try:
        build_manifest = read_current_build(build_root / "manifest.json")
    except (OSError, ValueError):
        return None

    if build_manifest != info:
        return None

    return PublishedBuild(info=info, root=build_root)
