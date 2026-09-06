# Frontend

Vue 3 application for the Milky Way & Exoplanet Explorer. The current prototype
loads two published Arrow IPC files — a Gaia density grid and exoplanet hosts —
and renders side-by-side panels: an interactive WebGL Galactocentric density map
(deck.gl) and an SVG exoplanet-host scatter plot (D3 scales, Vue-owned DOM) with
heliocentric / Galactocentric frame switching.

A collapsed SVG density plot remains available as a diagnostic comparison under
the WebGL map. Motion transitions, search UI, host markers on the GPU map, and
detail panels remain planned MVP work. The backend already exposes star/alias
search; this package does not call it yet.

## Requirements

- Node.js `^22.18.0` or `>=24.12.0` (CI uses Node 24)
- npm (lockfile workflow; prefer `npm ci`)
- A published immutable build with both visualization artifacts (see
  [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md))
- The FastAPI backend serving those artifacts at `/data/*.arrow`

Pipelines stage files under `data/frontend/`, but the backend serves only
copies under `data/builds/{build_id}/frontend/` selected by
`data/builds/current.json`. A missing published build yields HTTP 503 and the
page fails to load (both Arrow files are fetched with `Promise.all`).

## Setup

```sh
cd frontend
npm ci
cp .env.example .env
```

| Variable             | Purpose                                                              |
| -------------------- | -------------------------------------------------------------------- |
| `VITE_DATA_BASE_URL` | Base URL for static/frontend data files (required; no fallback)      |
| `VITE_API_BASE_URL`  | Reserved for metadata/search APIs (backend search exists; UI unused) |

Local defaults point at the backend:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DATA_BASE_URL=http://localhost:8000/data
```

The app requests:

- `${VITE_DATA_BASE_URL}/exoplanet_hosts.arrow`
- `${VITE_DATA_BASE_URL}/milky-way-density.arrow`

There is no Vite proxy; the backend must allow the Vite origin
(`http://localhost:5173` by default).

## Local development

Build mutable artifacts, publish an immutable release, start the backend, then
start the frontend:

```sh
# 1. Canonical build + density + publish
cd pipelines
uv sync --locked --all-groups
uv run python -m app.main
uv run python -m app.main build-gaia-density   # needs gaia_background snapshot
uv run python -m app.main publish-release --build-id local-001

# 2. Serve published Arrow files and APIs
cd ../backend
uv sync --locked --group dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Run the Vue app
cd ../frontend
npm run dev
```

Open http://localhost:5173. Relative backend data paths assume the backend is
started from `backend/` (or `MWE_DATA_ROOT` points at the shared `data/` tree).

## Scripts

| Command                      | Purpose                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `npm run dev`                | Vite dev server with hot reload                                              |
| `npm run build`              | Type-check, then production build → `dist/`                                  |
| `npm run preview`            | Preview the production build                                                 |
| `npm run type-check`         | `vue-tsc --build`                                                            |
| `npm run lint`               | Oxlint and ESLint                                                            |
| `npm run lint:fix`           | Auto-fix lint issues                                                         |
| `npm run format`             | Format `src/` with Oxfmt                                                     |
| `npm run format:check`       | Check formatting (CI / pre-commit)                                           |
| `npm run test:unit`          | Vitest (watch by default)                                                    |
| `npm run test:unit -- --run` | One-shot unit tests (pre-commit)                                             |
| `npm run test:coverage`      | Coverage run with 85% statement/function/line and 80% branch thresholds (CI) |

CI runs lint, format check, type-check, `test:coverage`, and `build` for
`frontend/` changes. Pre-commit uses one-shot unit tests.

## Architecture

```text
src/
├── main.ts                 # Vue bootstrap
├── App.vue                 # Load both Arrow files and loading / error UI
├── assets/                 # Global styles (Tailwind)
├── components/             # Vue presentation and interaction state
│   ├── GalacticMapCanvas.vue   # deck.gl OrthographicView lifecycle
│   ├── GaiaDensityPlot.vue     # density controls + WebGL map + SVG diagnostic
│   └── HostScatterPlot.vue     # host SVG scatter + frame toggle
├── data/                   # Arrow fetch + validation boundary
│   ├── hostVisualization.ts
│   └── densityVisualization.ts
├── domain/                 # Scientific types, coordinates, frame definitions
│   ├── host.ts
│   ├── density.ts          # record types + baseline / exploratory selection
│   └── coordinates / frames
└── visualization/          # Pure projection + deck.gl layer builders
    ├── gaiaDensityLayer.ts
    ├── gaiaDensityStyle.ts
    ├── galacticMapView.ts
    ├── galacticReferenceLayers.ts
    ├── gaiaDensityPlotModel.ts   # SVG diagnostic model
    └── hostScatterPlotModel.ts
```

Dependency direction:

```text
App → data loaders + components
component → visualization model / layers + domain
visualization → domain (+ deck.gl layer constructors where applicable)
data loader → domain
domain → (no UI or transport dependencies)
```

| Layer            | Responsibility                                                                                             |
| ---------------- | ---------------------------------------------------------------------------------------------------------- |
| `domain/`        | Host and density record types, Cartesian positions, Astropy v4.0 Sun constants, frame presentation         |
| `data/`          | Fetch Arrow IPC, validate fields / enums / nullability, map snake_case columns to frontend records         |
| `visualization/` | Pure projection, deck.gl layer construction, camera fit, density styling, SVG diagnostic models            |
| `components/`    | Canvas / SVG rendering, quality toggle, frame toggle, and interaction state                                |

D3 is limited to scales, ticks, formatting, and projection inside
`visualization/`. Vue components own the SVG DOM and the deck.gl canvas
lifecycle. There is no router or global store in this prototype.

## Density map controls and canvas lifecycle

`GaiaDensityPlot` owns density selection state and composes layers for the
WebGL map:

| Control | Behaviour |
| --- | --- |
| Include exploratory distances | Off by default. Baseline cells use GSP-Phot or inverse-parallax S/N ≥ 5; enabling the toggle adds exploratory inverse-parallax S/N 2–5 (amber). |
| Reset view | Refits the orthographic camera to the full ±`extentKpc` grid with padding. |
| Pan / zoom | Drag to pan; scroll or pinch to zoom (`OrthographicView` controller). |
| SVG diagnostic | Collapsed `<details>` comparison using the same selection and styling. |

`GalacticMapCanvas` mounts a deck.gl `Deck` on a Vue-owned `<canvas>`:

1. **Mount** — create `Deck` with `createGalacticMapView()`, initial layers, and a zeroed view state.
2. **Resize** — store canvas size and call `fitGalacticMapView` so both axes share one zoom (equal physical scale).
3. **Layer updates** — watch `layers` and `extentKpc`; push new props / refit the camera.
4. **View changes** — sync controller `viewState` back into the Deck.
5. **Errors** — surface a WebGL failure message; the SVG diagnostic remains usable.
6. **Unmount** — `deck.finalize()` and drop the instance.

Layer composition for the density panel:

```text
PolygonLayer          Gaia density cells (cartesian kpc, quality-aware colours)
ScatterplotLayer      Sun + Galactic centre markers (screen-pixel radii)
TextLayer             Reference labels (drawn above density; depth write off)
```

Hosts remain on the SVG scatter panel. A unified WebGL explorer that overlays
hosts on the density map is still planned.

## Data contracts

### Host Arrow (`exoplanet_hosts.arrow`)

The decoder in `src/data/hostVisualization.ts` expects:

```text
host_id
host_name
gaia_source_id                 # Int64 or null → string | null in JS
planet_count
archive_planet_count
planet_count_matches_archive
is_circumbinary
position_status                # available | no_accepted_distance | no_exact_gaia_source
distance_pc
distance_method
distance_quality
heliocentric_{x,y,z}_pc
galactocentric_{x,y,z}_kpc
phot_g_mean_magnitude
bp_rp_color
```

### Density Arrow (`milky-way-density.arrow`)

The decoder in `src/data/densityVisualization.ts` expects:

```text
grid_level
cell_x
cell_y
distance_tier
cell_center_x_kpc
cell_center_y_kpc
cell_size_kpc
source_count
weighted_brightness
mean_bp_rp                     # nullable
```

Invariants contributors must preserve:

- **Gaia IDs as strings** — Int64 source IDs exceed JavaScript's safe integer
  range; never coerce them to `number`.
- **Nullable positions are valid** — hosts without an accepted distance or exact
  Gaia match remain in the dataset but are omitted from the selected spatial
  view.
- **Equal physical scale** — both plot axes share one units-per-pixel value so
  spatial relationships are not distorted (SVG models and `fitGalacticMapView`).
- **Both artifacts required** — missing density or host data fails the whole
  load.
- **Explicit uncertainty opt-in** — baseline density is displayed by default.
  Exploratory inverse-parallax density is visually distinguished and rendered
  only after the user enables it.

See [../docs/DATASET.md](../docs/DATASET.md) for the published schema and
[../docs/DATA_FLOW.md](../docs/DATA_FLOW.md) for pipeline → publish → backend →
browser flow.

## Editor setup

Recommended: [VS Code](https://code.visualstudio.com/) or Cursor with the
[Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
extension (disable Vetur). Workspace recommendations live under
`frontend/.vscode/`.
