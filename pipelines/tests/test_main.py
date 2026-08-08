from collections.abc import Iterator
from pathlib import Path

import pytest

import app.main as pipeline_main
from app.config import override_settings, reset_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path) -> Iterator[None]:
    reset_settings()
    override_settings(
        data_root=tmp_path,
        log_level="WARNING",
        log_color=False,
    )

    yield

    reset_settings()


def test_canonical_build_runs_identity_then_exoplanets(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def record_identity():
        calls.append("identity")

    def record_exoplanets() -> dict[str, Path]:
        calls.append("exoplanets")
        return {}

    def record_gaia_host_manifest() -> Path:
        calls.append("gaia-host-manifest")
        return Path("gaia_host_ids.parquet")

    monkeypatch.setattr(pipeline_main, "build_identity", record_identity)
    monkeypatch.setattr(pipeline_main, "build_exoplanets", record_exoplanets)
    monkeypatch.setattr(pipeline_main, "build_gaia_host_manifest", record_gaia_host_manifest)

    pipeline_main.canonical_build()

    assert calls == ["identity", "exoplanets", "gaia-host-manifest"]
