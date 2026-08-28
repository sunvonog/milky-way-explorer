# Project summary

Condensed status for Milky Way Explorer. Operational commands live in the
package READMEs and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md); this file tracks
product decisions and where the vertical slice stands.

## Product

Build an interactive 2D Milky Way and exoplanet explorer with:

- a Gaia-derived top-down Galactic density background;
- individually selectable exoplanet host stars;
- readable host names from the NASA Exoplanet Archive;
- an Earth-centred exoplanet atlas;
- detailed planetary-system views;
- smooth WebGL and Motion transitions (planned for the public MVP).

## Dataset decision

Use only:

- Gaia DR3;
- NASA Exoplanet Archive `PSCompPars`.

Do not use DESI in the MVP.

Do not use a large random Gaia sample as the primary public star layer.

## Data composition

```text
Global Milky Way context
    aggregated Gaia density cells

Interactive objects
    all confirmed exoplanet hosts
    exact Gaia enrichment when an ID is available
    readable NASA/HD/HIP/Gaia names

Details
    systems and planets from PSCompPars
    source metadata from local Parquet
```

## Validated learnings

- deck.gl can render at least 100,000 development points successfully.
- Static Arrow files should deliver global rendering data.
- Full metadata should be fetched only after selection.
- Python pipelines should perform coordinate transforms and aggregation offline.
- FastAPI should remain thin.
- Gaia should not be called directly by the browser.
- Mutable pipeline outputs must be published into immutable builds before the
  backend serves them.

## Current status

Completed for the current snapshots and prototype:

- identity naming catalogues → `stars.parquet` / `alias.parquet`;
- PSCompPars ingestion and review sinks;
- exact Gaia host retrieval (`refresh-gaia-hosts` + committed `gaia_hosts` snapshot);
- chunked Gaia background retrieval (1M `random_index` candidates in 100k
  batches) and `build-gaia-density`;
- host and density Arrow visualization files;
- `publish-release` → `data/builds/{build_id}/` + atomic `current.json`;
- FastAPI health, build, star/alias search, and Arrow data routes;
- Vue SVG dual-panel density + host prototype.

Historical note: early single-query attempts around ~181k random sources failed;
the implemented path uses chunked async CSV downloads. See
[docs/GAIA_RETRIEVAL.md](docs/GAIA_RETRIEVAL.md).

## Deployment constraints

An example target production profile has:

- 4 vCPU;
- 8 GB RAM;
- 80 GB disk.

It is suitable for the MVP, but not for the full Gaia catalogue.

Operational rules (target production layout; not automated in-repo yet):

- two initial API workers;
- static data served by Caddy or Nginx when possible;
- no full-dataset preload;
- keep at least 25 GB disk free;
- retain only current and rollback builds;
- move large immutable data to object storage later.

## Vertical slice (implemented)

```text
naming snapshots + PSCompPars
    → identity tables
    → hosts, systems, planets
    → exact Gaia host-ID retrieval
    → coordinate transformation
    → density aggregation
    → compact host + density Arrow files
    → publish-release
    → FastAPI serves published build
    → Vue density + host visualization
```

Still planned: planetary-system detail panel, WebGL rendering, UI search wiring,
and production deploy automation.

## Next actions

1. Wire the frontend to `GET /api/v1/search` and add object-detail panels.
2. Move rendering toward deck.gl / WebGL for the public MVP.
3. Add production reverse-proxy + deploy automation (see
   [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)).
4. Decide whether to vendor or document a fetch path for
   `data/raw/gaia_background/` so fresh clones can publish density releases
   offline.
