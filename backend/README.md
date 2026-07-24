# Backend

FastAPI metadata service for Milky Way Explorer. Serves health/build status and, later, search and object detail queries over published Parquet builds. Static Arrow/render files are intended to be served by the reverse proxy, not this API.

See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the full request model.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```sh
cd backend
uv sync
cp .env.example .env   # optional; defaults work for local dev
```

The project is installed as an editable package so `app` is importable for the server and tests.

## Configuration

Settings use the `MWE_` prefix (see `app/config.py`). Copy `.env.example` or export variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MWE_ENV` | `development` | Environment label |
| `MWE_DATA_ROOT` | `../data` | Root for published builds |
| `MWE_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed browser origins |
| `MWE_DUCKDB_MEMORY_LIMIT` | `1GB` | DuckDB memory cap (for upcoming query paths) |

The active build is resolved from `{data_root}/builds/current.json`. If that pointer is missing, `GET /api/v1/build` returns `503`.

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
| `GET` | `/api/v1/build` | Active build manifest from `current.json` |

Planned (not implemented yet): source/system/planet detail and search — see the architecture doc.

## Layout

```text
backend/
├── app/
│   ├── main.py          # FastAPI app, CORS
│   ├── config.py        # pydantic-settings
│   ├── builds.py        # current-build pointer
│   └── routers/
│       └── meta.py      # /api/v1/health, /build
├── tests/
├── pyproject.toml
└── uv.lock
```

## Develop

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
uv run ty check
```
