from pathlib import Path

import pytest

import app.main as pipeline_main

pytestmark = pytest.mark.usefixtures("isolated_data_root")


def test_canonical_build_runs_publication_flows_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def record_identity() -> None:
        calls.append("identity")

    def record_exoplanets() -> dict[str, Path]:
        calls.append("exoplanets")
        return {}

    def record_gaia_host_manifest() -> Path:
        calls.append("gaia-host-manifest")
        return Path("gaia_host_ids.parquet")

    def record_gaia_hosts() -> Path:
        calls.append("gaia-hosts")
        return Path("gaia_host_sources.parquet")

    def record_host_visualization() -> Path:
        calls.append("host-visualization")
        return Path("exoplanet_hosts.arrow")

    monkeypatch.setattr(pipeline_main, "build_identity", record_identity)
    monkeypatch.setattr(pipeline_main, "build_exoplanets", record_exoplanets)
    monkeypatch.setattr(pipeline_main, "build_gaia_host_manifest", record_gaia_host_manifest)
    monkeypatch.setattr(pipeline_main, "build_gaia_hosts", record_gaia_hosts)
    monkeypatch.setattr(pipeline_main, "build_host_visualization", record_host_visualization)

    pipeline_main.canonical_build()

    assert calls == [
        "identity",
        "exoplanets",
        "gaia-host-manifest",
        "gaia-hosts",
        "host-visualization",
    ]


def test_main_runs_gaia_host_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def record_gaia_host_refresh() -> Path:
        calls.append("gaia-host-refresh")
        return Path("data/raw/gaia_hosts/current")

    monkeypatch.setattr(pipeline_main, "refresh_gaia_hosts", record_gaia_host_refresh)

    result = pipeline_main.main(["refresh-gaia-hosts"])

    assert result == 0
    assert calls == ["gaia-host-refresh"]


def test_main_runs_gaia_background_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def record_gaia_background_refresh() -> Path:
        calls.append("gaia-background-refresh")
        return Path("data/raw/gaia_background/current")

    monkeypatch.setattr(pipeline_main, "refresh_gaia_background", record_gaia_background_refresh)

    result = pipeline_main.main(["refresh-gaia-background"])

    assert result == 0
    assert calls == ["gaia-background-refresh"]


def test_main_runs_gaia_density_build(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def record_gaia_density_build() -> Path:
        calls.append("gaia-density")
        return Path("data/processed/gaia_density_cells.parquet")

    monkeypatch.setattr(pipeline_main, "build_gaia_density", record_gaia_density_build)

    result = pipeline_main.main(["build-gaia-density"])

    assert result == 0
    assert calls == ["gaia-density"]


def test_main_runs_release_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def record_release_publication(*, build_id: str | None = None) -> object:
        calls.append(build_id)
        return object()

    monkeypatch.setattr(pipeline_main, "publish_current_release", record_release_publication)

    result = pipeline_main.main(["publish-release", "--build-id", "release-123"])

    assert result == 0
    assert calls == ["release-123"]
