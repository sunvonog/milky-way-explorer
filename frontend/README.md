# Frontend

Vue 3 application for the Milky Way & Exoplanet Explorer. The current prototype
loads two published Arrow IPC files — a Gaia density grid and exoplanet hosts —
and renders side-by-side interactive SVG plots (D3 scales, Vue-owned DOM) with
heliocentric / Galactocentric frame switching on the host panel.

WebGL / deck.gl rendering, Motion transitions, search UI, and detail panels
remain planned MVP work. The backend already exposes star/alias search; this
package does not call it yet.

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
│   ├── HostScatterPlot.vue
│   └── GaiaDensityPlot.vue
├── data/                   # Arrow fetch + validation boundary
│   ├── hostVisualization.ts
│   └── densityVisualization.ts
├── domain/                 # Scientific types, coordinates, frame definitions
│   ├── host.ts
│   └── density.ts
└── visualization/          # Pure D3 plot-model construction
    ├── hostScatterPlotModel.ts
    └── gaiaDensityPlotModel.ts
```

Dependency direction:

```text
App → data loaders + components
component → visualization model + domain
visualization model → domain
data loader → domain
domain → (no UI or transport dependencies)
```

| Layer            | Responsibility                                                                                             |
| ---------------- | ---------------------------------------------------------------------------------------------------------- |
| `domain/`        | Host and density record types, Cartesian positions, Astropy v4.0 Sun constants, frame presentation         |
| `data/`          | Fetch Arrow IPC, validate fields / enums / nullability, map snake_case columns to frontend records         |
| `visualization/` | Pure projection: equal physical scale, ticks, reference points, density cell geometry, planet-count radius |
| `components/`    | SVG rendering, frame toggle, and interaction state                                                         |

D3 is limited to scales, ticks, formatting, and projection inside
`visualization/`. Vue components own the SVG DOM. There is no router or global
store in this prototype.

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
  spatial relationships are not distorted.
- **Both artifacts required** — missing density or host data fails the whole
  load.

See [../docs/DATASET.md](../docs/DATASET.md) for the published schema and
[../docs/DATA_FLOW.md](../docs/DATA_FLOW.md) for pipeline → publish → backend →
browser flow.

## Editor setup

Recommended: [VS Code](https://code.visualstudio.com/) or Cursor with the
[Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
extension (disable Vetur). Workspace recommendations live under
`frontend/.vscode/`.
