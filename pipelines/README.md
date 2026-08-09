# Pipelines

Offline data pipelines for Milky Way Explorer. Transforms vendored naming
catalogues and committed external-source snapshots into canonical Parquet tables.
No orchestrator server — flows are plain Python functions with Prefect-style
`@flow` / `@task` decorators for run identity, timing, retries, and structured
logging.

## Setup

```bash
cd pipelines
uv sync --all-groups
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
uv run python -m app.main refresh-gaia-hosts   # maintainer-only Gaia retrieval refresh
```

`canonical_build` builds the identity tables, PSCompPars domain tables, and the
Gaia host-ID retrieval manifest. It consumes committed snapshots and does not
contact external services.

`refresh-snapshots` and `refresh-pscomppars` are intentionally **not** part of
the build. They overwrite `data/raw/<source>/current/`. Review
`git diff --stat data/raw/` and commit before rebuilding.

## Configuration

Settings live in [`app/config.py`](app/config.py) (`pydantic-settings`,
`MWE_` prefix — same vocabulary as the backend).

| Variable | Default | Meaning |
|---|---|---|
| `MWE_DATA_ROOT` | `<repo>/data` | Root for raw / processed / logs |
| `MWE_LOG_LEVEL` | `INFO` | Console minimum level |
| `MWE_LOG_JSON` | `false` | JSON on the console |
| `MWE_LOG_COLOR` | `true` | Coloured console output |
| `MWE_LOG_DIR` | `<data_root>/logs` | Override log directory |
| `MWE_LOG_RETENTION` | `20` | Run log files kept per flow |
| `MWE_STRICT_CHECKS` | `false` | Raise when expectations miss |

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
├── domain/                 # pure transformations and domain contracts
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

## Adding a flow

1. Put deterministic business logic in `app/domain/<subject>.py`.
2. Add source parsing under `app/loaders/` and external retrieval under
   `app/sources/`.
3. Wrap the operations with `@task` in `app/flows/<subject>.py`.
4. Compose tasks under a named `@flow`.
5. Add offline publication flows to `canonical_build()`. External refreshes
   should instead receive an explicit maintainer-only CLI command.
6. Mirror the implementation under `tests/unit/` and `tests/integration/`.

For tasks repeated per source or batch, pass `key=` so run summaries identify
each instance (`resolve_snapshot[iau_csn]`, `fetch_chunk[12]`, and similar).

## Tests

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
