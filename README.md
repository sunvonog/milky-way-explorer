# Milky Way & Exoplanet Explorer

An interactive 2D data-visualization project for exploring the Milky Way, named
stellar objects, and confirmed exoplanet systems.

This monorepo contains offline pipelines, a FastAPI metadata service, and a Vue
prototype. Design constraints carried forward from earlier experiments:

- WebGL rendering can handle at least 100,000 points in local benchmark runs.
- A browser should never receive the full Gaia catalogue.
- Random Gaia samples are useful for benchmarks, but are not the primary public dataset.
- The public experience should combine a compact Milky Way background with individually selectable named or scientifically important stars.
- Gaia and the NASA Exoplanet Archive are sufficient for the MVP.
- Expensive astronomical processing belongs in offline pipelines, not in browser requests.
- Target production deployments have finite CPU, RAM, and disk capacity, so immutable compact files and on-demand metadata are essential.

## Product vision

The application contains three connected experiences:

1. **Top-down Milky Way explorer**  
   A Gaia-derived, Galactocentric density reconstruction with the Galactic centre and Sun clearly marked.

2. **Earth-centred exoplanet atlas**  
   All confirmed exoplanet host systems positioned relative to Earth.

3. **Planetary-system viewer**  
   A selected host opens an orbital view with planets, orbital parameters, stellar properties, and provenance labels.

## Dataset strategy

The public application does not render a permanent random cloud of Gaia sources. Instead, it uses:

```text
Gaia-derived Milky Way density background
+ exact Gaia records for exoplanet hosts
+ readable host names from the NASA Exoplanet Archive
+ optional bright or curated stars added later
+ on-demand Gaia detail queries for selected regions
```

The initial named-star layer is built from the NASA Exoplanet Archive because its `PSCompPars` table contains host names and Gaia DR3 identifiers.

A deterministic Gaia sample remains available only for:

- renderer benchmarks;
- development without network access;
- validation of coordinate transforms;
- density-background prototyping.

## Current prototype status

Implemented today:

- offline identity, exoplanet, Gaia host, density, and visualization pipelines;
- immutable release publication (`publish-release` → `data/builds/{build_id}/` + `current.json`);
- FastAPI health, build status, star/alias search, and Arrow data routes;
- Vue SVG prototype with side-by-side density grid and exoplanet-host scatter plots.

Still planned for the public MVP: deck.gl / WebGL rendering, Motion transitions,
exoplanet/planet search and detail panels, and production deploy automation.

## MVP scope

The minimum viable product includes:

- Gaia DR3 and NASA Exoplanet Archive ingestion;
- exact Gaia retrieval for all matched exoplanet hosts;
- a top-down Galactocentric density view;
- an Earth-centred exoplanet view;
- readable host names with Gaia designation fallback;
- search by host and planet name;
- WebGL rendering with smooth transitions;
- source and system detail panels;
- Parquet for analytical storage;
- Arrow or compact binary files for frontend rendering;
- FastAPI for metadata and search;
- deployment to a production VPS.

## Non-goals for the MVP

- Downloading or storing the full Gaia DR3 catalogue;
- rendering every Gaia source individually;
- hosting Gaia spectra or epoch photometry;
- DESI integration;
- SIMBAD enrichment for all stars;
- 3D rendering;
- user accounts or social features;
- Kubernetes or distributed processing.

## Technology stack

### Frontend

Current prototype:

- Node.js LTS
- Vue 3
- TypeScript
- Vite
- Tailwind CSS
- D3
- Apache Arrow JavaScript
- Vue-managed SVG rendering

Planned for the public MVP:

- deck.gl / WebGL rendering
- Motion for Vue (or equivalent transitions)
- search and object-detail API client

### Backend

- Python 3.12
- FastAPI
- Pydantic
- DuckDB
- Polars
- PyArrow

### Pipelines

- Python 3.12
- Polars / PyArrow
- Astropy
- Astroquery
- Prefect-style `@flow` / `@task` decorators (no orchestrator server)

### Storage

- Raw downloads: FITS, VOTable, or CSV
- Processed analytical data: Parquet
- Frontend datasets: Arrow IPC or compact binary
- Metadata and manifests: JSON
- Immutable releases: `data/builds/{build_id}/` selected by `data/builds/current.json`

### Deployment

- Production VPS (example capacity: 4 vCPU / 8 GB RAM / 80 GB disk)
- Caddy or Nginx (planned)
- Uvicorn/FastAPI
- Docker Compose or systemd (planned; not in repo yet)

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the release lifecycle and local
publish workflow.

## Repository layout

```text
milky-way-explorer/
├── README.md
├── PROJECT_SUMMARY.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── DATASET.md
│   ├── DEPLOYMENT.md
│   └── GAIA_RETRIEVAL.md
├── frontend/
├── backend/
├── pipelines/
└── data/
    ├── raw/          # source snapshots (partially vendored)
    ├── processed/    # mutable Parquet workspace (gitignored)
    ├── frontend/     # mutable Arrow staging (gitignored)
    ├── builds/       # immutable releases + current.json (gitignored)
    └── logs/         # pipeline run logs (gitignored)
```

Package setup and commands:

- [pipelines/README.md](pipelines/README.md)
- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)

## Developer quick start

```bash
# 1. Canonical offline build (identity, exoplanets, Gaia hosts, host Arrow)
cd pipelines
uv sync --all-groups
uv run python -m app.main

# 2. Density Arrow (needs data/raw/gaia_background/current/)
uv run python -m app.main build-gaia-density

# 3. Immutable release for the backend
uv run python -m app.main publish-release --build-id local-001

# 4. API + Arrow serving
cd ../backend
uv sync --locked --group dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Vue prototype
cd ../frontend
npm ci
cp .env.example .env
npm run dev
```

Optional local quality gates (mirrors CI / pre-commit):

```bash
# from repo root, once
uv run --project backend pre-commit install
```

CI already runs package lint, type, test, and frontend build jobs. Production
SSH deploy is not automated yet.

## Development phases

### Phase 1 — Foundation

- Create the GitHub repository.
- Configure Vue, TypeScript, Vite, linting, and tests.
- Configure FastAPI, Ruff, `ty`, and Pytest.
- Add CI checks without deployment.
- Docker Compose for local integration remains planned.

### Phase 2 — Exoplanet-first ingestion

- Download `PSCompPars` into a versioned raw snapshot.
- Validate staging rows and publish planet, host, and system Parquet tables.
- Keep review sinks for invalid rows, stellar conflicts, and archive count mismatches.
- Carry normalized host `gaia_source_id` values for exact Gaia retrieval.
- Produce the first readable named-star catalogue from identity naming sources.

### Phase 3 — Exact Gaia host retrieval

- Query Gaia only for the extracted host IDs.
- Enrich hosts with Gaia astrometry and photometry.
- Generate heliocentric and Galactocentric coordinates (implemented on `gaia_host_sources`).
- Store match method and confidence.

### Phase 4 — Milky Way background

- Chunked asynchronous Gaia background retrieval (current sample: 1M
  `random_index` candidates → accepted sources → density cells).
- Validate the top-down coordinate pipeline.
- Build a coarse density grid (`build-gaia-density`).
- Increase coverage only when pipeline reliability is proven.

### Phase 5 — Frontend visualization

- Current prototype: Vue SVG + D3 density grid and host scatter with
  heliocentric / Galactocentric frame switching over published Arrow files.
- Render density and hosts via WebGL / deck.gl (planned).
- Add view switching and Motion-powered transitions (planned).
- Wire search and detail panels to the API (backend search exists; UI pending).

### Phase 6 — CI/CD and deployment

- Build and test on GitHub Actions (implemented).
- Build production images or artifacts (planned).
- Deploy through SSH to a production host (planned).
- Add health checks, rollback, and backups (planned).

## Scientific honesty

Every displayed value should be tagged as one of:

- observed;
- derived;
- estimated;
- inferred;
- procedurally visualized;
- unknown.

The top-down Milky Way view must be labelled as a **Gaia-observed reconstruction**, not as a complete map of every star in the Galaxy.

## License

Copyright (c) 2026 Oliver Grun.

This project is available under the
[PolyForm Noncommercial License 1.0.0](LICENSE). Personal, educational,
research, hobby, and other non-commercial use is permitted. Commercial use,
including selling the software or using it for an income-generating purpose,
requires a separate written license from the copyright holder.

Because commercial use is restricted, this project is **source-available**,
not OSI-approved open-source software.

## Official data sources

- Gaia Archive: https://gea.esac.esa.int/archive/
- Gaia programmatic access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
- NASA Exoplanet Archive TAP: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- NASA `PSCompPars` definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
