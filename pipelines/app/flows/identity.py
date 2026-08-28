"""Build canonical stars, aliases, and exoplanet-host links from naming snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from logly import Logger

from app.artifacts import ALIASES_FILENAME, STARS_FILENAME
from app.config import get_settings
from app.domain.identity import (
    build_aliases,
    build_stars,
    link_exoplanet_hosts,
    review_dropped_stars,
)
from app.loaders import exoplanet_names, iau_csn, wgsn_faints
from app.runtime.checks import expect
from app.runtime.flow import flow, get_run, get_task, task
from app.runtime.logging import bound_log
from app.sources.snapshot import snapshot_dir

# Verified against the current vendored snapshots (see resolve.py docstring notes).
EXPECT_STARS = 605
EXPECT_WITH_COORDS = 154
EXPECT_HOST_LINKS = 163
EXPECT_UNMATCHED = 1
EXPECT_DROPPED_STARS = 1
EXPECT_ALIASES = 2875


def _ctx_log(**fields: object) -> Logger:
    run = get_run()
    return bound_log(
        run_id=run.run_id if run else "-",
        flow=run.flow_name if run else "build-identity",
        task=get_task() or "-",
        **fields,
    )


@task(name="resolve_snapshot", key="source")
def resolve_snapshot(source: str) -> Path:
    """Return the CSV path inside data/raw/<source>/current/ and log its checksum."""
    settings = get_settings()
    directory = snapshot_dir(settings.raw_root, source)
    if not directory.is_dir():
        raise FileNotFoundError(f"missing snapshot directory: {directory}")

    csv_files = sorted(directory.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"no CSV in snapshot directory: {directory}")
    path = csv_files[0]

    meta_path = directory / "snapshot.json"
    sha256 = None
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sha256 = meta.get("sha256")

    _ctx_log(
        source=source,
        path=str(path),
        sha256=sha256 or "",
        bytes=path.stat().st_size,
    ).info("resolved snapshot")
    return path


@task(name="load_iau_csn")
def load_csn(path: Path) -> pl.DataFrame:
    frame = iau_csn.load(path)
    valid = int(frame["is_valid"].sum())
    _ctx_log(
        rows=frame.height,
        valid=valid,
        flagged=frame.height - valid,
    ).info("loaded iau_csn")
    return frame


@task(name="load_wgsn_faints")
def load_faints(path: Path) -> pl.DataFrame:
    frame = wgsn_faints.load(path)
    valid = int(frame["is_valid"].sum())
    _ctx_log(
        rows=frame.height,
        valid=valid,
        flagged=frame.height - valid,
    ).info("loaded wgsn_faints")
    return frame


@task(name="load_exoplanet_names")
def load_exo(path: Path) -> pl.DataFrame:
    frame = exoplanet_names.load(path)
    valid = int(frame["is_valid"].sum())
    _ctx_log(
        rows=frame.height,
        valid=valid,
        flagged=frame.height - valid,
    ).info("loaded exoplanet_names")
    return frame


@task(name="resolve_stars")
def resolve_stars_task(csn: pl.DataFrame, faints: pl.DataFrame) -> pl.DataFrame:
    stars = build_stars(csn, faints)
    _ctx_log(
        rows=stars.height,
        with_coords=int(stars["ra_deg"].is_not_null().sum()),
        with_hip=int(stars["hip"].is_not_null().sum()),
    ).info("built stars")
    return stars


@task(name="review_dropped")
def review_dropped_task(csn: pl.DataFrame) -> pl.DataFrame:
    dropped = review_dropped_stars(csn)
    _ctx_log(rows=dropped.height).info("collected dropped stars for review")
    return dropped


@task(name="resolve_aliases")
def resolve_aliases_task(stars: pl.DataFrame) -> pl.DataFrame:
    aliases = build_aliases(stars)
    mean = aliases.height / stars.height if stars.height else 0.0
    _ctx_log(
        rows=aliases.height,
        per_star_mean=round(mean, 2),
    ).info("built aliases")
    return aliases


@task(name="link_hosts")
def link_hosts_task(stars: pl.DataFrame, exo: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    linked, unmatched = link_exoplanet_hosts(stars, exo)
    _ctx_log(
        linked=linked.height,
        unmatched=unmatched.height,
    ).info("linked exoplanet hosts")
    return linked, unmatched


@task(name="write_outputs")
def write_outputs(
    stars: pl.DataFrame,
    aliases: pl.DataFrame,
    linked: pl.DataFrame,
    unmatched: pl.DataFrame,
    dropped: pl.DataFrame,
) -> dict[str, Path]:
    out = get_settings().processed_root
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "stars": out / STARS_FILENAME,
        "aliases": out / ALIASES_FILENAME,
        "linked": out / "exoplanet_host_links.parquet",
        "unmatched": out / "review_unmatched_hosts.parquet",
        "dropped": out / "review_dropped_stars.parquet",
    }
    frames = {
        "stars": stars,
        "aliases": aliases,
        "linked": linked,
        "unmatched": unmatched,
        "dropped": dropped,
    }
    for key, path in paths.items():
        frames[key].write_parquet(path)
        _ctx_log(
            output=key,
            path=str(path),
            rows=frames[key].height,
            bytes=path.stat().st_size,
        ).info("wrote parquet")
    return paths


@task(name="check_expectations")
def check_expectations(
    stars: pl.DataFrame,
    aliases: pl.DataFrame,
    linked: pl.DataFrame,
    unmatched: pl.DataFrame,
    dropped: pl.DataFrame,
) -> None:
    expect("stars", stars.height, EXPECT_STARS)
    expect(
        "stars_with_coordinates",
        int(stars["ra_deg"].is_not_null().sum()),
        EXPECT_WITH_COORDS,
    )
    expect("host_links", linked.height, EXPECT_HOST_LINKS)
    expect("unmatched_hosts", unmatched.height, EXPECT_UNMATCHED)
    expect("dropped_stars", dropped.height, EXPECT_DROPPED_STARS)
    expect("aliases", aliases.height, EXPECT_ALIASES)


@flow(name="build-identity")
def build_identity() -> None:
    """Resolve naming sources into canonical star / alias / host-link tables."""
    csn = load_csn(resolve_snapshot("iau_csn"))
    faints = load_faints(resolve_snapshot("wgsn_faints"))
    exo = load_exo(resolve_snapshot("exoplanet_names"))

    stars = resolve_stars_task(csn, faints)
    dropped = review_dropped_task(csn)
    aliases = resolve_aliases_task(stars)
    linked, unmatched = link_hosts_task(stars, exo)
    write_outputs(stars, aliases, linked, unmatched, dropped)
    check_expectations(stars, aliases, linked, unmatched, dropped)
