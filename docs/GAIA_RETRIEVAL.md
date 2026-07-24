# Gaia Retrieval Strategy and the 10,000-Row Problem

## 1. Current observation

The current pipeline successfully retrieves 10,000 Gaia sources but fails when attempting the planned approximately 181,000-source sample.

The exact cause cannot be determined without the complete error message and query/job status. However, **10,000 rows is not the official anonymous asynchronous Gaia limit**.

The official Gaia documentation states that anonymous asynchronous TAP jobs may return up to 3,000,000 rows and run for up to 90 minutes. Therefore, a failure above 10,000 rows is more likely caused by the client path, query design, output handling, timeout, archive instability, or a locally configured row limit.

## 2. Most likely causes

Check these in order.

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

Avoid calling `job.get_results()` merely to count rows after `dump_to_file=True`, because that can parse the result into memory again.

### 2.5 Too many columns

A 181,000-row query with dozens of nullable columns is much heavier than a 181,000-row render query with ten columns.

Test the row count with a minimal query first:

```sql
SELECT
    source_id,
    ra,
    dec,
    l,
    b,
    parallax,
    phot_g_mean_mag,
    bp_rp
FROM gaiadr3.gaia_source
WHERE random_index < 181171
```

Then add fields incrementally.

### 2.6 Archive instability or timeout

The Gaia Archive currently warns that it may be unstable while it evolves in preparation for DR4. A valid query may occasionally time out or fail.

Persist the job ID and inspect the server-side error instead of immediately resubmitting a different query.

### 2.7 Output-format or decompression problem

Try compressed VOTable or FITS output and ensure the output filename matches the actual compressed format.

### 2.8 Local disk or permissions

Verify:

- destination directory exists;
- sufficient free space exists;
- the process can write to it;
- a partial file from an earlier attempt is not blocking the output.

## 3. Safe diagnostic query progression

Run these steps without changing multiple variables at once.

### Step 1 — Count only

```sql
SELECT COUNT(*) AS source_count
FROM gaiadr3.gaia_source
WHERE random_index < 181171
```

This confirms that the selection is valid without downloading the rows.

### Step 2 — Retrieve 20,000 minimal rows

```sql
SELECT
    source_id,
    ra,
    dec
FROM gaiadr3.gaia_source
WHERE random_index < 20000
```

### Step 3 — Retrieve 50,000 minimal rows

```sql
SELECT
    source_id,
    ra,
    dec
FROM gaiadr3.gaia_source
WHERE random_index < 50000
```

### Step 4 — Retrieve 181,171 minimal rows

```sql
SELECT
    source_id,
    ra,
    dec
FROM gaiadr3.gaia_source
WHERE random_index < 181171
```

### Step 5 — Add required columns in groups

Add:

1. Galactic coordinates;
2. parallax and quality;
3. photometry;
4. motion;
5. model-derived fields.

The first failing group identifies the cost or problematic field set.

## 4. Recommended asynchronous file-download code

```python
from pathlib import Path

from astroquery.gaia import Gaia


def download_gaia_query(
    *,
    query: str,
    output_path: Path,
) -> Path:
    """
    Submit a Gaia asynchronous TAP job and save the result directly.

    Reference:
    ESA Gaia Archive programmatic-access documentation.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        raise FileExistsError(output_path)

    job = Gaia.launch_job_async(
        query=query,
        output_file=str(output_path),
        output_format="votable_gzip",
        dump_to_file=True,
        verbose=True,
    )

    phase = job.get_phase()

    if phase != "COMPLETED":
        raise RuntimeError(
            f"Gaia job {job.jobid} ended with phase {phase}."
        )

    if not output_path.exists():
        raise FileNotFoundError(
            f"Gaia reported completion but no file exists: {output_path}"
        )

    return output_path
```

Record `job.jobid` in logs and manifests.

## 5. Chunking strategy

Even when a single 181,000-row job should work, chunking is more reliable and resumable.

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
  AND random_index < 10000
```

Next chunk:

```sql
WHERE random_index >= 10000
  AND random_index < 20000
```

Continue until the target threshold is reached.

### Benefits

- failed chunks can be retried independently;
- memory use remains bounded;
- file sizes remain manageable;
- progress is measurable;
- the pipeline can resume;
- transformed chunks may be aggregated immediately.

## 6. New project recommendation

Do not block the new project on obtaining 181,000 random sources.

Start with:

1. the existing 10,000-source sample for the density-pipeline proof;
2. the complete NASA exoplanet catalogue;
3. exact Gaia retrieval for exoplanet host IDs;
4. chunked Gaia jobs for expanding the density background later.

The exact host dataset is likely much smaller and more valuable than a large random point sample.

## 7. Required diagnostic information

When the error happens again, preserve:

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
