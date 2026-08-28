import json
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient


def test_health_is_independent_of_data(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_build_returns_503_when_unpublished(client: TestClient) -> None:
    assert client.get("/api/v1/build").status_code == 503


def test_build_reflects_pointer_without_restart(
    client: TestClient, publish_build: Callable[[str], Path]
) -> None:
    publish_build("build-001")
    assert client.get("/api/v1/build").json()["build_id"] == "build-001"

    publish_build("build-002")
    assert client.get("/api/v1/build").json()["build_id"] == "build-002"


def test_build_rejects_pointer_to_missing_build(client: TestClient, tmp_path: Path) -> None:
    pointer = tmp_path / "builds" / "current.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(
        json.dumps(
            {
                "build_id": "missing_build",
                "created_at": "2026-08-28T12:00:00Z",
                "source_snapshots": {},
                "row_counts": {},
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/v1/build")

    assert response.status_code == 503
    assert response.json() == {"detail": "no published build"}
