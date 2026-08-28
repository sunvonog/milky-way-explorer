# Release and deployment lifecycle

Milky Way Explorer separates mutable pipeline workspaces from immutable
application releases.

The pipelines write intermediate and canonical outputs under `data/raw/`,
`data/processed/`, and `data/frontend/`. The backend does not serve these
mutable paths directly. It only reads the immutable build selected by
`data/builds/current.json`.

## Build a release locally

Run the canonical pipelines:

```bash
cd pipelines
uv sync --all-groups
uv run python -m app.main
```

That offline build writes identity and exoplanet Parquet tables, Gaia host
sources, and the host visualization Arrow file under `data/processed/` and
`data/frontend/`. It does **not** build the density artifact or publish a
release.

Build the density visualization (requires a `data/raw/gaia_background/current/`
snapshot — not vendored in git; run `refresh-gaia-background` as a maintainer
when the snapshot is missing):

```bash
uv run python -m app.main build-gaia-density
```

Publish an immutable release:

```bash
uv run python -m app.main publish-release --build-id local-001
```

Omit `--build-id` to use a UTC timestamp identifier. Publication copies the
release allowlist into `data/builds/{build_id}/`, writes `manifest.json`, and
atomically replaces `data/builds/current.json`.

### Release allowlist

| Relative path | Role |
| --- | --- |
| `processed/stars.parquet` | Named-star catalogue for search |
| `processed/alias.parquet` | Aliases for search |
| `frontend/exoplanet_hosts.arrow` | Host scatter visualization |
| `frontend/milky-way-density.arrow` | Density-grid visualization |

The publish step also records SHA-256 digests of the six source snapshots under
`data/raw/*/current/snapshot.json`:

- `exoplanet_names`
- `iau_csn`
- `wgsn_faints`
- `nasa_pscomppars`
- `gaia_hosts`
- `gaia_background`

Review and other processed tables stay in the mutable workspace and are not
copied into the immutable build.

### `current.json` semantics

`data/builds/current.json` is a full release manifest (the same JSON as
`data/builds/{build_id}/manifest.json`), not a minimal `{ "build_id": ... }`
pointer. The backend requires the referenced `builds/{build_id}/` directory to
exist as a direct child of `builds/`. It parses both manifests into the
`BuildInfo` subset (`build_id`, `created_at`, `source_snapshots`, and
`row_counts`) and compares that subset. It does not compare the complete raw
JSON or artifact checksums.

Failed publishes leave the previous `current.json` untouched.

## Run the application against a published build

Use the **same** `data/` tree for pipelines and the backend. Prefer an explicit
`MWE_DATA_ROOT` (pipeline default is `<repo>/data`; backend default is
`../data` relative to the backend working directory).

```bash
# Backend
cd backend
uv sync --locked --group dev
export MWE_DATA_ROOT=../data   # or an absolute path to the repo data/ tree
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Frontend env (build-time Vite variables):

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DATA_BASE_URL=http://localhost:8000/data
```

The Vue prototype fetches both Arrow files in parallel. A missing density or
host artifact fails the page load.

### Runtime checks

| Endpoint | Behavior |
| --- | --- |
| `GET /api/v1/health` | Always `200`; does not verify datasets |
| `GET /api/v1/build` | Active manifest subset; `503` without a published build |
| `GET /api/v1/search?q=&limit=` | Star/alias search over published Parquet |
| `GET /data/exoplanet_hosts.arrow` | Host Arrow from the active build |
| `GET /data/milky-way-density.arrow` | Density Arrow from the active build |

Missing or invalid builds return `503` with `"no published build"` on build,
search, and data routes.

## Atomic publication and rollback

Publication stages under `data/builds/.{build_id}.staging-*`, promotes the
complete directory to `data/builds/{build_id}/`, then replaces `current.json`
via a temporary pointer file. Incomplete releases never become active.

Operational rollback is not automated yet. Retain the previous immutable build
so future rollback tooling can atomically restore its manifest as
`current.json`. Re-running `publish-release` creates a new release from the
current mutable workspace and is not a rollback.

## Environment variables

| Variable | Package | Default | Notes |
| --- | --- | --- | --- |
| `MWE_DATA_ROOT` | pipelines / backend | `<repo>/data` / `../data` | Set explicitly in shared or production layouts |
| `MWE_ENV` | both | `development` | Label only |
| `MWE_CORS_ORIGINS` | backend | `http://localhost:5173` | Browser origins for GET |
| `MWE_DUCKDB_MEMORY_LIMIT` | backend | `1GB` | Search queries |
| `VITE_DATA_BASE_URL` | frontend | (required) | Base URL for Arrow files |
| `VITE_API_BASE_URL` | frontend | (reserved) | Metadata/search client; UI wiring pending |

Pipeline logging and Gaia/density tuning use additional `MWE_*` settings; see
[../pipelines/README.md](../pipelines/README.md).

## CI quality gates

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs path-filtered
lint, type, test, and frontend production build jobs on pushes to `main` and on
pull requests. There is **no** release or deploy job yet.

Backend and pipeline coverage gates are 85%. Frontend thresholds are 85% for
statements, functions, and lines, and 80% for branches.

## Production topology (planned, not implemented)

There is currently no `Dockerfile`, Compose file, reverse-proxy config, or
deploy workflow in the repository. The intended production layout is:

```text
Internet
  → Caddy or Nginx
      → frontend/dist (static SPA)
      → future static artifact routes (URL contract undecided)
      → /api/v1/* → Uvicorn/FastAPI (two workers)
```

Operational rules for that target:

- example VPS capacity of 4 vCPU / 8 GB RAM / 80 GB disk;
- static data served by the reverse proxy when possible (FastAPI currently
  serves Arrow in local/dev);
- retain current and at least one rollback build;
- keep substantial free disk (target ≥ 25 GB free);
- define the future reverse-proxy URL and cache contract before static serving
  is implemented.

Until that topology lands, treat `publish-release` plus the local backend and
frontend commands above as the supported release path. See also
[ARCHITECTURE.md](ARCHITECTURE.md) §10 and the package READMEs.
