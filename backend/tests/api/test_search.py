from pathlib import Path

from fastapi.testclient import TestClient


def test_search_returns_503_when_unpublished(client: TestClient) -> None:
    assert client.get("/api/v1/search", params={"q": "Sirius"}).status_code == 503


def test_search_requires_query(client: TestClient, search_dataset: Path) -> None:
    assert client.get("/api/v1/search").status_code == 422


def test_search_rejects_empty_query(client: TestClient, search_dataset: Path) -> None:
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422


def test_search_rejects_limit_out_of_range(client: TestClient, search_dataset: Path) -> None:
    assert client.get("/api/v1/search", params={"q": "Si", "limit": 0}).status_code == 422
    assert client.get("/api/v1/search", params={"q": "Si", "limit": 51}).status_code == 422


def test_search_exact_match(client: TestClient, search_dataset: Path) -> None:
    response = client.get("/api/v1/search", params={"q": "Sirius"})
    assert response.status_code == 200
    hits = response.json()
    assert hits[0] == {
        "star_id": "iau:sirius",
        "display_name": "Sirius",
        "matched_alias": "Sirius",
        "catalogue": "IAU",
        "is_exact": True,
        "ra_deg": 101.287,
        "dec_deg": -16.716,
    }


def test_search_prefix_and_exact_ranking(client: TestClient, search_dataset: Path) -> None:
    hits = client.get("/api/v1/search", params={"q": "Sir"}).json()
    assert [h["star_id"] for h in hits] == ["iau:sirius", "iau:sirona"]
    assert all(h["is_exact"] is False for h in hits)

    exact = client.get("/api/v1/search", params={"q": "Sirius"}).json()
    assert exact[0]["is_exact"] is True
    assert exact[0]["star_id"] == "iau:sirius"


def test_search_folds_to_empty_returns_empty_list(client: TestClient, search_dataset: Path) -> None:
    assert client.get("/api/v1/search", params={"q": "!!!"}).json() == []
