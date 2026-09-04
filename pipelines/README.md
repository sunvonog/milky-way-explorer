# Pipelines

Offline data pipelines for Milky Way Explorer. Transforms vendored naming
catalogues and committed external-source snapshots into canonical Parquet tables
and frontend Arrow files, then publishes immutable releases for the backend.
No orchestrator server — flows are plain Python functions with Prefect-style
`@flow` / `@task` decorators for run identity, timing, retries, and structured
logging.

## Setup

```bash
cd pipelines
uv sync --locked --all-groups
cp .env.example .env   # optional; defaults work from the repo root
```

## Run

```bash
uv run python -m app.main                      # full canonical build
uv run python -m app.main --strict             # fail on expectation misses
uv run python -m app.main --log-level DEBUG
uv run python -m app.main --log-json           # JSON on the console (CI)
uv run python -m app.main refresh-snapshots    # maintainer-only naming snapshot refresh
uv run python -m app.main refresh-pscomppars   # maintainer-only NASA PSCompPars refresh
uv run python -m app.main refresh-gaia-hosts   # maintainer-only Gaia host retrieval refresh
uv run python -m app.main refresh-gaia-background  # maintainer-only Gaia background refresh
uv run python -m app.main build-gaia-density   # density Parquet + milky-way-density.arrow
uv run python -m app.main publish-release --build-id local-001
```

### Canonical build vs release

`canonical_build` (default command / `build`) is offline and does **not**
contact external services. It runs:

1. identity tables (`stars`, `alias`, host links, review sinks);
2. PSCompPars domain tables;
3. Gaia host-ID retrieval manifest;
4. `gaia_host_sources.parquet`;
5. host visualization → `data/frontend/exoplanet_hosts.arrow`.

It does **not** run `build-gaia-density` or `publish-release`.

`refresh-snapshots`, `refresh-pscomppars`, `refresh-gaia-hosts`, and
`refresh-gaia-background` are maintainer-only operations. They replace
`data/raw/<source>/current/`. Review and commit vendored snapshot changes
before rebuilding.

### Density and publish

```bash
# Requires data/raw/gaia_background/current/ (not vendored in git)
uv run python -m app.main build-gaia-density
uv run python -m app.main publish-release --build-id local-001
```

`publish-release` validates the allowlist, copies artifacts into
`data/builds/{build_id}/`, writes `manifest.json`, and atomically updates
`data/builds/current.json`. The backend serves only that published build — see
[../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

**Release allowlist:**

| Relative path | Produced by |
| --- | --- |
| `processed/stars.parquet` | identity |
| `processed/alias.parquet` | identity |
| `frontend/exoplanet_hosts.arrow` | canonical build (host visualization) |
| `frontend/milky-way-density.arrow` | `build-gaia-density` |

Six source snapshots must exist under `data/raw/*/current/snapshot.json`
(including `gaia_background`). Naming catalogues, PSCompPars, and Gaia hosts are
vendored via `.gitignore` exceptions; the Gaia background snapshot is
maintainer-generated and must be refreshed or otherwise supplied before a full
release.

## Configuration

Settings live in [`app/config.py`](app/config.py) (`pydantic-settings`,
`MWE_` prefix — same vocabulary as the backend).

| Variable | Default | Meaning |
|---|---|---|
| `MWE_DATA_ROOT` | `<repo>/data` | Root for raw / processed / frontend / builds / logs |
| `MWE_LOG_LEVEL` | `INFO` | Console minimum level |
| `MWE_LOG_JSON` | `false` | JSON on the console |
| `MWE_LOG_COLOR` | `true` | Coloured console output |
| `MWE_LOG_DIR` | `<data_root>/logs` | Override log directory |
| `MWE_LOG_RETENTION` | `20` | Run log files kept per flow |
| `MWE_STRICT_CHECKS` | `false` | Raise when expectations miss |
| `MWE_GAIA_BACKGROUND_SOURCE_COUNT` | `5000000` | `random_index` candidates for background refresh |
| `MWE_GAIA_BACKGROUND_BATCH_SIZE` | `100000` | Async batch size for background refresh |
| `MWE_GAIA_DENSITY_EXTENT_KPC` | `20.0` | Half-extent of the Galactocentric density grid |

Density grid resolutions default to `(128,)` in `app/config.py`
(`gaia_density_grid_sizes`) and are not required in `.env`.

CLI flags (`--strict`, `--log-level`, `--log-json`) override env / `.env`.

## Logging

Each top-level flow run writes:

- coloured (or JSON) lines to stderr
- one JSON-lines file at `data/logs/<flow>/<run_id>.jsonl`

Subflows join the parent run (same `run_id`, same file). Structured fields
use logly's `bind()` — kwargs to `info()` are format-string substitutions only.

## Layout

```text
app/
├── main.py                 # CLI and canonical-build entry point
├── config.py               # pydantic settings
├── release.py              # immutable release allowlist and publication
├── artifacts.py            # processed / frontend filenames
├── domain/                 # pure transformations and domain contracts
│   ├── density.py
│   ├── exoplanets.py
│   ├── gaia.py
│   ├── identity.py
│   └── names.py
├── flows/                  # task and flow orchestration
├── loaders/                # raw source files → validated staging frames
├── sources/                # queries, downloads, and snapshot persistence
└── runtime/                # flow engine, logging, and expectations

tests/
├── unit/
│   ├── domain/
│   ├── loaders/
│   ├── runtime/
│   └── sources/
└── integration/
    ├── flows/
    └── test_main.py
```

### Identity outputs

`build-identity` (part of the canonical build) reads vendored naming snapshots
and writes under `data/processed/`:

| File | Contents |
|---|---|
| `stars.parquet` | Canonical named stars for search |
| `alias.parquet` | Alternate designations |
| `exoplanet_host_links.parquet` | Links from hosts into the identity catalogue |
| review sinks | Ambiguous / unresolved naming rows |

Exact schemas: [../docs/DATASET.md](../docs/DATASET.md).

### PSCompPars outputs

`build-exoplanets` reads `data/raw/nasa_pscomppars/current/pscomppars.csv` and
writes:

| File | Contents |
|---|---|
| `exoplanets.parquet` | One normalized planet per valid staging row |
| `exoplanet_hosts.parquet` | One host per exact host name |
| `exoplanet_systems.parquet` | One provisional system per exact host name |
| `review_invalid_exoplanet_rows.parquet` | Staging validation failures |
| `review_host_stellar_conflicts.parquet` | Conflicting stellar candidates |
| `review_system_planet_count_mismatches.parquet` | Archive vs recomputed planet counts |
| `gaia_host_ids.parquet` | Sorted, distinct Gaia DR3 IDs required for exact host retrieval |

All paths are under `data/processed/`.

### Gaia host outputs

`refresh-gaia-hosts` writes a multi-file snapshot under
`data/raw/gaia_hosts/current/` (`batches/gaia-host-*.csv` plus `snapshot.json`).
`build-gaia-hosts` (part of the canonical build) reads that snapshot and writes:

| File | Contents |
|---|---|
| `gaia_host_sources.parquet` | One validated Gaia DR3 source per host-ID manifest entry, with distance provenance plus heliocentric (pc) and Galactocentric (kpc, Astropy `v4.0`) coordinates |

Current expectations: 4,396 sources; 109 without an accepted distance (null spatial coordinates).

### Density outputs

`refresh-gaia-background` writes `data/raw/gaia_background/current/`.
`build-gaia-density` reads that snapshot and writes:

| File | Contents |
|---|---|
| `gaia_density_cells.parquet` | Occupied Galactocentric density cells, aggregated separately by distance-quality tier |
| `frontend/milky-way-density.arrow` | Visualization Arrow with cell geometry and distance-quality tier |

Host visualization (`build_host_visualization`, part of the canonical build)
additionally writes `frontend/exoplanet_hosts.arrow` with position-status
breakdown (`available` / `no_accepted_distance` / `no_exact_gaia_source`).

## Adding a flow

1. Put deterministic business logic in `app/domain/<subject>.py`.
2. Add source parsing under `app/loaders/` and external retrieval under
   `app/sources/`.
3. Wrap the operations with `@task` in `app/flows/<subject>.py`.
4. Compose tasks under a named `@flow`.
5. Add offline publication flows to `canonical_build()` only when they belong
   in every default build. External refreshes and optional density/release
   steps should receive explicit CLI commands.
6. Mirror the implementation under `tests/unit/` and `tests/integration/`.

For tasks repeated per source or batch, pass `key=` so run summaries identify
each instance (`resolve_snapshot[iau_csn]`, `fetch_chunk[12]`, and similar).

## Tests

```bash
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

CI uses the same commands with `uv sync --locked --all-groups` and an 85%
coverage gate. Pipelines CI also triggers on `data/raw/**` changes.
