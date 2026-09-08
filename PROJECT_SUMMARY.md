# Project summary

Working product direction, implementation status, and project-management
roadmap for Milky Way Explorer. Updated with the owner's decisions on
2026-09-07. Operational commands live in the package READMEs and
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

This direction supersedes earlier descriptions that made density cells the
primary public background. Other documentation still needs to be aligned.

## Product vision

Build a website whose main page is an interactive, top-down **2D Milky Way
map**. Visitors explore observed/catalogued stars, discover interesting
objects, and open progressively richer views of stars and their planets.

The intended experience is:

- Individual Gaia stars provide the background at their supported positions.
- Exoplanet hosts, named stars, and other curated or scientifically interesting
  stars are highlighted and clickable. These important objects remain available
  independently of background sampling.
- Visitors can pan and zoom around one shared map.
- Clicking a star opens its properties, provenance, and known exoplanets, when
  available.
- A planetary-system view shows planets orbiting their host and the star's
  estimated habitable zone, where the available data supports those views.
- Smooth Motion animations connect the map, star/system view, and planet view.
- Search finds stars and supported aliases or planet names, highlights the
  associated star, and smoothly moves and zooms the camera to it.
- Additional information and visualization tools grow out of this map and
  selection experience.

**Initial device scope: desktop and laptop browsers.** Phone-specific work is
deferred until the first usable explorer and its performance are proven.

The first usable map is an intermediate milestone. Planetary-system views,
orbital animation, habitable zones, and smooth navigation are part of the
intended core product, delivered in subsequent milestones rather than omitted.

## Layers and future exploration tools

The main visual identity is an individual-star map. The existing density map
becomes an optional overlay and remains useful for scientific comparison and
diagnostics.

Future extensions include:

- additional scientific overlays and dataset-specific highlights;
- a view of the Milky Way and stars from Earth;
- constellation exploration;
- visual explanations of interesting stellar and exoplanet properties.

These are a backlog of possibilities, not commitments for the first usable
release. Prioritize them after the central map-to-object experience works.

## Dataset direction and scientific presentation

- Gaia DR3 supplies background stars and exact host enrichment where matched.
- NASA Exoplanet Archive `PSCompPars` supplies hosts, systems, and planets.
- Existing identity and naming sources, including IAU names and exoplanet
  naming catalogues, support readable names and aliases. Their ingestion does
  not yet constitute a clickable named-star layer on the map.
- Additional datasets for important or interesting stars are in scope for
  future selection by the owner. No new dataset is selected by this update;
  DESI remains outside the initial scope.
- Publish a bounded, deterministic overview of real Gaia sources. Sampling
  should preserve the source distribution; load regional detail as needed
  within measured limits. Do not send the full Gaia catalogue to the browser.
- Preserve stable identifiers and reconcile overlapping catalogues so one
  physical object is not presented as unrelated stars across layers.
- Distinguish observed values, derived estimates, illustrative presentation,
  and unknown information. Retain distance quality and source provenance.
- Present the Galactic view as a Gaia-observed reconstruction with incomplete
  coverage. Do not invent stars or spiral structure to fill observational gaps.
- Orbital animations and habitable-zone overlays must identify their data,
  estimation method, and illustrative choices. Missing parameters should remain
  explicit rather than being silently presented as measurements.
- Objects without supported map coordinates must not receive invented
  positions. Search/details should explain when camera focus is unavailable.

## Architecture and performance guardrails

- Keep expensive transformations and catalogue reconciliation in offline
  pipelines; keep FastAPI focused on serving data, search, and details.
- Publish immutable builds before serving browser data. New star artifacts
  and detail tables must be included in the release contract.
- Use compact render datasets; fetch full metadata after selection.
- Keep background stars, highlighted objects, density, labels, and selection
  independently updatable on a shared camera.
- Review the current per-row object decoding and reactive data storage before
  scaling background stars. Large datasets need a bounded memory footprint.
- Opening details or selecting a host should not reload the background or
  rebuild unrelated rendering data.
- Measure download/decode time, first display, interaction frame times, memory,
  and quality-toggle latency on agreed desktop/laptop hardware. Earlier
  100,000-point development trials do not establish production limits.
- Set payload, visible-point, and cache budgets from those measurements before
  increasing coverage or committing to extensive regional loading machinery.
- Keep the existing domain, data, visualization, and component boundaries.
  Refactor when a concrete coupling, duplication, or performance problem
  threatens the next milestone; a broad rewrite is not currently justified.

## Current status

Implemented in the current checkout; this is a foundation, not the complete
product experience:

The owner reviewed and merged the WebGL foundation in PR #23. The local
`main` checkout includes merge commit `4bd4b95` as of 2026-09-07.

- identity naming catalogues → `stars.parquet` / `alias.parquet`;
- PSCompPars ingestion and review sinks;
- exact Gaia host retrieval (`refresh-gaia-hosts` + committed `gaia_hosts` snapshot);
- chunked Gaia background retrieval and quality-aware density aggregation;
- host and density Arrow visualization files;
- `publish-release` → `data/builds/{build_id}/` + atomic `current.json`;
- FastAPI health, build, star/alias search, and Arrow data routes;
- WebGL / deck.gl density foundation: quality-aware `PolygonLayer`, fitted
  camera, pan/zoom/reset, Sun / Galactic-centre references, SVG diagnostic;
- SVG exoplanet-host scatter with heliocentric / Galactocentric frames.

Still missing:

- a published individual-background-star dataset and renderer;
- one shared map with highlighted, selectable hosts and named/curated stars;
- selection panels and source/system/planet detail endpoints;
- host/planet search beyond the current identity catalogue, plus frontend
  search, highlight, and animated camera focus;
- planetary-system and planet views, orbital animations, and habitable zones;
- Motion transitions between views;
- optional density controls within the unified explorer;
- representative browser performance measurements and production deployment
  automation.

The current release publishes identity search tables and host/density Arrow
files. System and planet detail tables are not yet published for API use;
search and rich details therefore require pipeline/publication and backend
work as well as frontend work.

Historical note: early single-query attempts around ~181k random sources failed;
the implemented path uses chunked async CSV downloads. See
[docs/GAIA_RETRIEVAL.md](docs/GAIA_RETRIEVAL.md).

## Deployment constraints

An example target production profile has:

- 4 vCPU;
- 8 GB RAM;
- 80 GB disk.

Treat this as a planning constraint, with suitability checked against actual
payloads and workloads. Hosting the full Gaia catalogue is outside scope.

Operational rules (target production layout; not automated in-repo yet):

- two initial API workers;
- static data served by Caddy or Nginx when possible;
- no full-dataset preload;
- keep at least 25 GB disk free;
- retain only current and rollback builds;
- move large immutable data to object storage later.

## Delivery roadmap

| Order | Milestone | Completion criteria |
| --- | --- | --- |
| Complete | WebGL foundation | The owner reviewed and merged PR #23. Remaining product-documentation alignment is tracked separately below. |
| Proposed next PR | Publish and render a bounded Gaia star overview | Reuse the existing Gaia snapshot and coordinate processing; export and publish a reproducible, size-limited star overview; render it on the existing WebGL map with reference markers and distance-quality controls; record representative desktop/laptop performance. Agree the default point budget and any regional-detail follow-up from evidence. |
| Then | First usable unified explorer | One main map combines background stars, highlighted hosts, references, and an optional density overlay. Clicking a host opens basic available information; returning to the map preserves context. Establish the path for named/curated highlights using supported identities and coordinates. |
| Then | Search and object navigation | Search supported stars, aliases, and planets; highlight and animate focus to the associated star. Publish and serve the required metadata, provide useful star/system details, and handle missing positions or data explicitly. |
| Then | Planetary-system and planet views | Show known planets, supported orbital motion, the estimated habitable zone, and planet details. Smooth Motion transitions connect these views with the main map. Scientific and illustrative information is clearly distinguished. |
| Release readiness | Deploy and harden | Verify the selected release scope in a hosted environment, including loading/error states, performance, data provenance, health checks, and rollback. An earlier preview can validate completed milestones. |
| Later | Additional exploration tools | Select Earth-sky, constellation, additional dataset, and explanatory visualization features with the owner after reviewing the core experience. |

## Active management concerns and next decisions

- **Direction drift:** root README and architecture documentation still contain
  density-first statements. Bring them into agreement with this summary.
- **Performance:** choose representative desktop/laptop hardware and measurable
  budgets before scaling the star layer. Do not treat unit-test success as
  evidence of real-browser rendering performance.
- **Data dependencies:** decide named/interesting-star datasets incrementally;
  account for identity matching, positions, provenance, and release publication.
- **Reproducibility:** decide whether to vendor or document a fetch path for
  `data/raw/gaia_background/` so fresh clones can reproduce the required builds.
- **Scope control:** keep milestones small and reviewable. Tooling cleanup and
  speculative overlays should not displace the next usable product increment.

At each milestone review, compare the actual implementation with this roadmap,
record completed work and new risks, and check direction with the owner before
material scope changes. The project-management task reviews code health,
maintains planning documentation, and recommends priorities or refactors; it
does not write application code or provide implementation snippets.
