import json
from collections.abc import Callable, Iterator
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.names import search_key
from app.main import app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    def override() -> Settings:
        return Settings(data_root=tmp_path)

    app.dependency_overrides[get_settings] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def write_search_tables(
    processed_root: Path,
    stars: list[dict],
    aliases: list[dict],
) -> None:
    """Write minimal stars/alias parquet for search tests."""
    processed_root.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(stars).write_parquet(processed_root / "stars.parquet")
    pl.DataFrame(aliases).write_parquet(processed_root / "alias.parquet")


@pytest.fixture
def search_dataset(published_build: Path) -> Path:
    """Canned stars/aliases: Sirius (exact + prefix) and Sirona (prefix rival)."""
    processed = published_build / "processed"
    write_search_tables(
        processed,
        stars=[
            {
                "star_id": "iau:sirius",
                "canonical_display_name": "Sirius",
                "ra_deg": 101.287,
                "dec_deg": -16.716,
            },
            {
                "star_id": "iau:sirona",
                "canonical_display_name": "Sirona",
                "ra_deg": 200.0,
                "dec_deg": 10.0,
            },
        ],
        aliases=[
            {
                "star_id": "iau:sirius",
                "alias": "Sirius",
                "alias_search_key": search_key("Sirius"),
                "catalogue": "IAU",
                "priority": 1,
            },
            {
                "star_id": "iau:sirius",
                "alias": "α CMa",
                "alias_search_key": search_key("α CMa"),
                "catalogue": "Bayer",
                "priority": 6,
            },
            {
                "star_id": "iau:sirona",
                "alias": "Sirona",
                "alias_search_key": search_key("Sirona"),
                "catalogue": "IAU",
                "priority": 1,
            },
        ],
    )
    return processed


@pytest.fixture
def publish_build(tmp_path: Path) -> Callable[[str], Path]:
    """Publish a minimal immutable build and point current.json at it."""

    def publish(build_id: str) -> Path:
        build_root = tmp_path / "builds" / build_id
        build_root.mkdir(parents=True, exist_ok=True)

        manifest = {
            "build_id": build_id,
            "created_at": "2026-08-28T12:00:00Z",
            "source_snapshots": {"gaia": "DR3"},
            "row_counts": {},
        }
        manifest_json = json.dumps(manifest)

        (build_root / "manifest.json").write_text(manifest_json, encoding="utf-8")
        (tmp_path / "builds" / "current.json").write_text(manifest_json, encoding="utf-8")

        return build_root

    return publish


@pytest.fixture
def published_build(publish_build: Callable[[str], Path]) -> Path:
    return publish_build("test-build")
