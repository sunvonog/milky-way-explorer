# Milky Way & Exoplanet Explorer

An interactive 2D data-visualization project for exploring the Milky Way, named stellar objects, and confirmed exoplanet systems.

This repository is a **fresh project start**. It intentionally does not preserve earlier implementation choices. The new design keeps only the validated learnings:

- WebGL rendering can handle at least 100,000 points on the development machine.
- A browser should never receive the full Gaia catalogue.
- Random Gaia samples are useful for benchmarks, but are not the primary public dataset.
- The public experience should combine a compact Milky Way background with individually selectable named or scientifically important stars.
- Gaia and the NASA Exoplanet Archive are sufficient for the MVP.
- Expensive astronomical processing belongs in offline pipelines, not in browser requests.
- The production server has finite CPU, RAM, and disk capacity, so immutable compact files and on-demand metadata are essential.

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
- deployment to the existing Hetzner server.

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

- Node.js LTS
- Vue 3
- TypeScript
- Vite
- deck.gl
- D3
- Motion for Vue
- Apache Arrow JavaScript

### Backend

- Python 3.12
- FastAPI
- Pydantic
- DuckDB
- Polars
- PyArrow
- Astropy
- Astroquery

### Storage

- Raw downloads: FITS, VOTable, or CSV
- Processed analytical data: Parquet
- Frontend datasets: Arrow IPC or compact binary
- Metadata and manifests: JSON

### Deployment

- Hetzner virtual server
- 4 vCPU
- 8 GB RAM
- 80 GB local disk
- 20 TB monthly outbound traffic
- Caddy or Nginx
- Uvicorn/FastAPI
- Docker Compose or systemd

## Repository layout

```text
milky-way-explorer/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_FLOW.md
│   ├── DATASET.md
│   ├── DEPLOYMENT.md
│   ├── GAIA_RETRIEVAL.md
│   └── START_HERE.md
├── frontend/
├── backend/
├── pipelines/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── frontend/
│   ├── tiles/
│   └── metadata/
└── infrastructure/
```

## Development phases

### Phase 1 — Foundation

- Create the GitHub repository.
- Configure Vue, TypeScript, Vite, linting, and tests.
- Configure FastAPI, Ruff, MyPy, and Pytest.
- Add Docker Compose for local integration.
- Add CI checks without deployment.

### Phase 2 — Exoplanet-first ingestion

- Download `PSCompPars`.
- Normalize planets, hosts, and systems.
- Extract distinct Gaia DR3 host identifiers.
- Produce the first readable named-star catalogue.

### Phase 3 — Exact Gaia host retrieval

- Query Gaia only for the extracted host IDs.
- Enrich hosts with Gaia astrometry and photometry.
- Generate heliocentric and Galactocentric coordinates.
- Store match method and confidence.

### Phase 4 — Milky Way background

- Start with the successfully retrieved 10,000-source Gaia sample.
- Validate the top-down coordinate pipeline.
- Build a coarse density grid.
- Replace single large queries with chunked asynchronous jobs.
- Increase coverage only when pipeline reliability is proven.

### Phase 5 — Frontend visualization

- Render the density background.
- Render exoplanet hosts as a separate interactive layer.
- Add view switching and Motion-powered transitions.
- Add search and details.

### Phase 6 — CI/CD and deployment

- Build and test on GitHub Actions.
- Build production images or artifacts.
- Deploy through SSH to the Hetzner server.
- Add health checks, rollback, and backups.

## Scientific honesty

Every displayed value should be tagged as one of:

- observed;
- derived;
- estimated;
- inferred;
- procedurally visualized;
- unknown.

The top-down Milky Way view must be labelled as a **Gaia-observed reconstruction**, not as a complete map of every star in the Galaxy.

## Official data sources

- Gaia Archive: https://gea.esac.esa.int/archive/
- Gaia programmatic access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
- NASA Exoplanet Archive TAP: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- NASA `PSCompPars` definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
