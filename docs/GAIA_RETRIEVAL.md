# Gaia Retrieval Strategy

## 1. Status

Exact Gaia retrieval for exoplanet hosts is implemented as a maintainer-only
refresh:

```bash
cd pipelines
uv run python -m app.main refresh-gaia-hosts
```

It queries known Gaia DR3 `source_id` values in batches of 500, writes CSV
batches to a temporary staging directory, and promotes them as one multi-file
snapshot under `data/raw/gaia_hosts/current/`. The canonical build then loads
that snapshot into `gaia_host_sources.parquet` without contacting Gaia.

Background density retrieval is also implemented:

```bash
uv run python -m app.main refresh-gaia-background
uv run python -m app.main build-gaia-density
```

`refresh-gaia-background` scans 5,000,000 `random_index` candidates in fifty
asynchronous CSV batches of 100,000 (configurable via
`MWE_GAIA_BACKGROUND_SOURCE_COUNT` / `MWE_GAIA_BACKGROUND_BATCH_SIZE`). The
snapshot under `data/raw/gaia_background/current/` is **not** vendored in git.

**10,000 rows is not the official anonymous asynchronous Gaia limit.** The
official documentation states that anonymous asynchronous TAP jobs may return
up to 3,000,000 rows and run for up to 90 minutes.

## 2. Historical failure context (≈181k single query)

Early development attempted larger single background queries around ~181,000
rows and failed. The exact cause for those attempts was never fully pinned
without complete job diagnostics, but the failure mode was **not** treated as
an official Gaia ceiling. Likely client-side causes are listed below for
troubleshooting regressions.

### 2.1 The ADQL query still contains `TOP 10000`

Search the final query string, not only the template.

```sql
SELECT TOP 10000 ...
```

Remove `TOP 10000` when requesting a larger range.

### 2.2 A client or TAP `MAXREC` value is 10,000

Inspect the code and HTTP request for:

```text
maxrec=10000
MAXREC=10000
ROW_LIMIT=10000
```

Do not assume that setting `Gaia.ROW_LIMIT = -1` affects every TAP path.

### 2.3 A synchronous query is being used

Large Gaia queries must use asynchronous execution.

Use:

```python
Gaia.launch_job_async(...)
```

not:

```python
Gaia.launch_job(...)
```

### 2.4 The result is loaded into memory after being downloaded

For larger responses, use direct file output.

Avoid calling `job.get_results()` merely to count rows after `dump_to_file=True`,
because that can parse the result into memory again.

### 2.5 Too many columns

A large-row query with dozens of nullable columns is much heavier than a
minimal render query. Test row counts with a minimal query first, then add
fields incrementally.

### 2.6 Archive instability or timeout

The Gaia Archive may be unstable while it evolves toward DR4. Persist the job
ID and inspect the server-side error instead of immediately resubmitting a
different query.

### 2.7 Output-format or decompression problem

The live pipeline downloads **CSV** async results. When diagnosing alternate
formats, ensure the output filename matches the actual compressed format.

### 2.8 Local disk or permissions

Verify:

- destination directory exists;
- sufficient free space exists;
- the process can write to it;
- a partial file from an earlier attempt is not blocking the output.

## 3. Safe diagnostic query progression

Run these steps without changing multiple variables at once when investigating
TAP failures.

### Step 1 — Count only

```sql
SELECT COUNT(*) AS source_count
FROM gaiadr3.gaia_source
WHERE random_index < 100000
```

### Step 2 — Retrieve a small minimal batch

```sql
SELECT
    source_id,
    ra,
    dec
FROM gaiadr3.gaia_source
WHERE random_index < 20000
```

### Step 3 — Scale batch size

Increase the `random_index` upper bound (for example 50,000 then 100,000)
before combining batches into the full background sample.

### Step 4 — Add required columns in groups

Add:

1. Galactic coordinates;
2. parallax and quality;
3. photometry;
4. motion;
5. model-derived fields.

The first failing group identifies the cost or problematic field set.

## 4. Recommended asynchronous file-download pattern

The implemented pipeline uses Astroquery async jobs with CSV file output. A
minimal pattern:

```python
from pathlib import Path

from astroquery.gaia import Gaia


def download_gaia_query(
    *,
    query: str,
    output_path: Path,
) -> Path:
    """Submit a Gaia asynchronous TAP job and save the result directly."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        raise FileExistsError(output_path)

    job = Gaia.launch_job_async(
        query=query,
        output_file=str(output_path),
        output_format="csv",
        dump_to_file=True,
        verbose=True,
    )

    phase = job.get_phase()

    if phase != "COMPLETED":
        raise RuntimeError(f"Gaia job {job.jobid} ended with phase {phase}.")

    if not output_path.exists():
        raise FileNotFoundError(
            f"Gaia reported completion but no file exists: {output_path}"
        )

    return output_path
```

The package download function returns `job.jobid`, but the current refresh does
not persist it in snapshot manifests. Prefer the package implementation in
`pipelines/app/sources/gaia.py` over copying this snippet.

## 5. Chunking strategy

Chunking remains the production approach even when a single large job might
succeed.

### Random-index chunks

```sql
SELECT
    source_id,
    ra,
    dec,
    l,
    b,
    parallax,
    parallax_over_error,
    phot_g_mean_mag,
    bp_rp,
    ruwe
FROM gaiadr3.gaia_source
WHERE random_index >= 0
  AND random_index < 100000
  AND (
    distance_gspphot > 0
    OR parallax > 0
  )
ORDER BY source_id
```

This query intentionally retrieves candidates rather than enforcing the final
distance-quality policy in ADQL. The domain layer classifies candidates as
baseline, exploratory, or unavailable. Keeping classification offline makes
the scientific policy testable and allows it to evolve without changing the
raw retrieval boundary.

Next chunk:

```sql
WHERE random_index >= 100000
  AND random_index < 200000
```

Continue until the configured source-count threshold is reached (default
1,000,000).

### Benefits

- memory use remains bounded;
- file sizes remain manageable;
- progress is measurable.

The current refresh is atomic but not resumable: if one batch fails, the staged
snapshot is discarded and a later refresh starts again. Persisted batch
journals and incremental aggregation are planned for larger retrievals.

## 6. Operational recommendation

Prefer the implemented maintainer commands over ad-hoc TAP experiments:

1. `refresh-gaia-hosts` for exact exoplanet-host enrichment (vendored snapshot);
2. `refresh-gaia-background` for the density sample (local / maintainer snapshot);
3. `build-gaia-density` for Parquet + Arrow publication into the mutable tree;
4. `publish-release` so the backend can serve the density artifact.

The exact host dataset is smaller and more valuable than a large random point
sample. Keep host and background refreshes maintainer-only; commit vendored
snapshots before rebuilding where the repository tracks them.

Operational flow: [DATA_FLOW.md](DATA_FLOW.md) and
[../pipelines/README.md](../pipelines/README.md).

## 7. Required diagnostic information

When a Gaia job fails, preserve:

```text
complete Python traceback
final ADQL query
sync or async method
Astroquery version
output format
job ID
job phase
server error message
partial output-file size
local free disk space
```

Do not reduce the exception to a generic message before logging it.

## 8. Official references

- Gaia FAQ and TAP limits: https://www.cosmos.esa.int/web/gaia/faqs
- Programmatic access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
- Gaia Archive status: https://gea.esac.esa.int/archive/
- Astroquery Gaia guide: https://astroquery.readthedocs.io/en/stable/gaia/gaia.html
