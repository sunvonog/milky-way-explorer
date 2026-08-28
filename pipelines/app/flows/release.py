"""Publish validated artifacts as one immutable deployment release."""

from __future__ import annotations

from datetime import UTC, datetime

from app.config import get_settings
from app.release import ReleaseManifest, publish_release
from app.runtime.flow import flow, task


def _generated_build_id(created_at: datetime) -> str:
    """Generate a filesystem-safe identifier for local publication."""
    return created_at.strftime("%Y%m%d%H%M%S%fZ")


@task(name="publish_release_bundle")
def publish_release_bundle(build_id: str, created_at: datetime) -> ReleaseManifest:
    """Publish the current allowlist artifacts under one build identifier"""
    return publish_release(get_settings().data_root, build_id=build_id, created_at=created_at)


@flow(name="publish-release")
def publish_current_release(*, build_id: str | None = None) -> ReleaseManifest:
    """Publish the already-built scientific and frontend artifacts.

    CI should supply a builder identifier derived from the deployment commit or
    workflow run. Local runs receive timestamp-based identifier.
    """
    created_at = datetime.now(UTC)
    resolved_build_id = build_id or _generated_build_id(created_at)

    return publish_release_bundle(resolved_build_id, created_at)
