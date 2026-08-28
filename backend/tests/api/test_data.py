from pathlib import Path

import pytest
from fastapi.testclient import TestClient

HOST_VISUALIZATION_PATH = "/data/exoplanet_hosts.arrow"
DENSITY_VISUALIZATION_PATH = "/data/milky-way-density.arrow"


def test_serves_host_visualization_arrow(client: TestClient, published_build: Path) -> None:
    artifact = published_build / "frontend" / "exoplanet_hosts.arrow"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"example Arrow bytes")

    response = client.get(HOST_VISUALIZATION_PATH)

    assert response.status_code == 200
    assert response.content == b"example Arrow bytes"
    assert response.headers["content-type"] == ("application/vnd.apache.arrow.file")


def test_serves_density_visualization_arrow(client: TestClient, published_build: Path) -> None:
    artifact = published_build / "frontend" / "milky-way-density.arrow"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"example density Arrow bytes")

    response = client.get(DENSITY_VISUALIZATION_PATH)

    assert response.status_code == 200
    assert response.content == b"example density Arrow bytes"
    assert response.headers["content-type"] == ("application/vnd.apache.arrow.file")


@pytest.mark.parametrize("path", [HOST_VISUALIZATION_PATH, DENSITY_VISUALIZATION_PATH])
def test_returns_503_when_no_build_is_published(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": "no published build"}


def test_returns_503_when_host_visualization_is_unpublished(
    client: TestClient,
    published_build: Path,
) -> None:
    response = client.get(HOST_VISUALIZATION_PATH)

    assert response.status_code == 503
    assert response.json() == {"detail": "host visualization is not published"}


def test_returns_503_when_density_visualization_is_unpublished(
    client: TestClient,
    published_build: Path,
) -> None:
    response = client.get(DENSITY_VISUALIZATION_PATH)

    assert response.status_code == 503
    assert response.json() == {"detail": "density visualization is not published"}


def test_data_route_does_not_expose_arbitrary_files(
    client: TestClient, published_build: Path
) -> None:
    private_file = published_build / "frontend" / "private.txt"
    private_file.parent.mkdir(parents=True)
    private_file.write_text("must not be served", encoding="utf-8")

    response = client.get("/data/private.txt")

    assert response.status_code == 404
