import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client(tmp_path):
    def override() -> Settings:
        return Settings(data_root=tmp_path)

    app.dependency_overrides[get_settings] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_is_independent_of_data(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_build_returns_503_when_unpublished(client):
    assert client.get("/api/v1/build").status_code == 503


def test_build_reflects_pointer_without_restart(client, tmp_path):
    pointer = tmp_path / "builds" / "current.json"
    pointer.parent.mkdir(parents=True)
    manifest = {
        "build_id": "2026-07-24T00:00:00Z-abc123",
        "created_at": "2026-07-24T00:00:00Z",
        "source_snapshots": {"gaia": "DR3"},
        "row_counts": {"named_stars": 451},
    }
    pointer.write_text(json.dumps(manifest))

    assert client.get("/api/v1/build").json()["build_id"] == manifest["build_id"]
