# Backend

FastAPI metadata and data service for Milky Way Explorer. Serves health and
build status, star/alias search over published Parquet, and allowlisted Arrow
visualization files from the immutable build selected by
`data/builds/current.json`.

In production, static Arrow files are intended to move behind Caddy or Nginx;
FastAPI currently serves them for local development. See
[../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) and
[../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A published build under `{data_root}/builds/` (see pipelines `publish-release`)

## Setup

```sh
cd backend
uv sync --locked --group dev
cp .env.example .env   # optional; defaults work for local dev
```

The project is installed as an editable package so `app` is importable for the
server and tests.

## Configuration

Settings use the `MWE_` prefix (see `app/core/config.py`). Copy `.env.example`
or export variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MWE_ENV` | `development` | Environment label |
| `MWE_DATA_ROOT` | `../data` | Root for published builds |
| `MWE_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed browser origins (GET) |
| `MWE_DUCKDB_MEMORY_LIMIT` | `1GB` | DuckDB memory cap for search |

The active build is resolved from `{data_root}/builds/current.json`. That file
is a full release manifest matching `{data_root}/builds/{build_id}/manifest.json`.
If the pointer is missing or invalid, `GET /api/v1/build`,
`GET /api/v1/search`, and `GET /data/*` return `503` with
`"no published build"`. Health remains `200` regardless of data.

Share the same `MWE_DATA_ROOT` used by the pipelines package when publishing
and serving.

## Run

```sh
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## API (current)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness; independent of data |
| `GET` | `/api/v1/build` | Active build manifest subset from `current.json` |
| `GET` | `/api/v1/search?q=&limit=` | Prefix/exact search over `stars.parquet` + `alias.parquet` in the published build (`limit` default 20, max 50) |
| `GET` | `/data/exoplanet_hosts.arrow` | Host visualization Arrow from the active build |
| `GET` | `/data/milky-way-density.arrow` | Density visualization Arrow from the active build |

Still planned: source / system / planet detail endpoints and exoplanet-name
search beyond the identity catalogue. Arbitrary paths under `/data/` return
`404`.

Search and Arrow routes read only from
`{data_root}/builds/{build_id}/processed/` and
`{data_root}/builds/{build_id}/frontend/` — never from the mutable
`data/processed/` or `data/frontend/` staging trees.

## Layout

```text
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS
│   ├── core/
│   │   └── config.py        # pydantic-settings
│   ├── api/
│   │   ├── data.py          # /data/*.arrow
│   │   ├── deps.py          # published-build dependencies
│   │   └── v1/
│   │       ├── meta.py      # /api/v1/health, /build
│   │       └── search.py    # /api/v1/search
│   ├── data/                # path constants
│   └── services/
│       ├── builds.py        # current-build pointer resolution
│       └── search.py        # DuckDB search
├── tests/
├── pyproject.toml
└── uv.lock
```

## Develop

```sh
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

CI uses `uv sync --locked --all-extras --dev` (no optional extras today) with
an 85% coverage gate. Prefer `ruff format --check` for CI parity; use
`uv run ruff format .` locally when rewriting files.
