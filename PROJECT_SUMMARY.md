# New Project Start Summary

## Product

Build an interactive 2D Milky Way and exoplanet explorer with:

- a Gaia-derived top-down Galactic density background;
- individually selectable exoplanet host stars;
- readable host names from the NASA Exoplanet Archive;
- an Earth-centred exoplanet atlas;
- detailed planetary-system views;
- smooth WebGL and Motion transitions.

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

## Current Gaia retrieval status

- 10,000 Gaia rows can be retrieved successfully.
- Attempts around 181,000 rows currently fail.
- This is not expected to be Gaia's official anonymous async row ceiling.
- Preserve the exact error, TAP job ID, final query, and output details.
- Use asynchronous file output and chunked jobs.
- Continue development with the 10,000-row fixture and exact exoplanet host queries.

## Server constraints

The Hetzner server has:

- 4 vCPU;
- 8 GB RAM;
- 80 GB disk;
- 20 TB outbound traffic.

It is suitable for the MVP, but not for the full Gaia catalogue.

Operational rules:

- two initial API workers;
- static data served by Caddy or Nginx;
- no full-dataset preload;
- keep at least 25 GB disk free;
- retain only current and rollback builds;
- move large immutable data to object storage later.

## First vertical slice

```text
PSCompPars ingestion
    → hosts, systems, planets
    → exact Gaia host-ID retrieval
    → coordinate transformation
    → compact host Arrow file
    → Vue host visualization
    → selected-system detail panel
```

## Next action

Create the new GitHub repository and implement the NASA Exoplanet Archive ingestion pipeline before rebuilding the Gaia background pipeline.
