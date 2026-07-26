# Pipelines

Offline data pipelines for Milky Way Explorer. Transforms vendored naming
catalogues into canonical Parquet tables. No orchestrator server — flows are
plain Python functions with Prefect-style `@flow` / `@task` decorators for
run identity, timing, retries, and structured logging.

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
uv run python -m app.main refresh-snapshots    # maintainer-only snapshot refresh
```

`refresh-snapshots` is intentionally **not** part of the build. It overwrites
`data/raw/<source>/current/` from files in `pipelines/_inputs/` (or URLs).
Review `git diff --stat data/raw/` and commit before rebuilding.

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
  main.py              # single entry point
  config.py            # pydantic Settings
  flows/               # declared pipelines (@flow / @task wrappers)
  runtime/             # logging, flow/task decorators, expect()
  loaders/             # pure CSV → DataFrame loaders
  sources/             # snapshot write helpers
  names.py / resolve.py
```

## Adding a flow

1. Put pure domain logic in a library module (no logging / decorators).
2. Wrap steps with `@task` in `app/flows/<name>.py` and compose them under `@flow`.
   For tasks that run once per source or chunk, pass `key=` so the run summary
   labels each instance (`resolve_snapshot[iau_csn]`, `fetch_chunk[12]`, …).
3. Call the new flow from `canonical_build()` in `app/main.py` (or add a
   subcommand for maintainer-only work).

## Tests

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
