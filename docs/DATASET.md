# Dataset Design

## 1. Scope

The MVP uses two upstream datasets:

1. **Gaia DR3** for astrometry, photometry, motion, source quality, and model-derived stellar parameters.
2. **NASA Exoplanet Archive `PSCompPars`** for confirmed planets, host names, host identifiers, system metadata, and orbital properties.

DESI is explicitly excluded from the MVP.

SIMBAD and other naming catalogues may be added later, but the first readable-name layer is based on NASA exoplanet hosts.

## 2. Public dataset composition

Analytical workspace (mutable, under `data/processed/` and `data/frontend/`):

```text
workspace =
    stars + alias + exoplanet_host_links
    + exoplanet_hosts + exoplanet_systems + exoplanets
    + gaia_host_sources + gaia_density_cells
    + frontend Arrow staging files
    + review_* sinks
```

Immutable release allowlist copied into `data/builds/{build_id}/`:

```text
public_build =
    processed/stars.parquet
    + processed/alias.parquet
    + frontend/exoplanet_hosts.arrow
    + frontend/milky-way-density.arrow
    + manifest.json   # also written as data/builds/current.json
```

Other processed tables remain available for analysis but are not served by the
backend until included in a future allowlist. A random Gaia sample is not part
of the required public dataset. Snapshot and layout details:
[DEPLOYMENT.md](DEPLOYMENT.md).

## 3. Gaia use cases

### 3.1 Global context

Gaia sources are aggregated into density cells for the Galactocentric Milky Way view.

The global context does not require:

- source names;
- detailed uncertainties for every browser point;
- full source metadata;
- individual source selection.

### 3.2 Exact host enrichment

Gaia rows are retrieved individually for exoplanet hosts identified by the NASA dataset.

These rows support:

- accurate source identifiers;
- Gaia coordinates;
- photometric appearance;
- proper motion;
- quality indicators;
- top-down coordinates;
- selected-source details.

### 3.3 Development samples

Deterministic Gaia background samples remain available for pipeline and
renderer experiments. Prefer the committed/maintainer `gaia_background`
snapshot and `build-gaia-density` over ad-hoc TAP downloads.

They are used to test:

- query handling;
- transformations;
- density aggregation;
- render performance;
- data serialization.

## 4. Gaia fields

### 4.1 Required host-enrichment fields

```text
source_id
designation
ref_epoch
ra
dec
l
b
parallax
parallax_error
parallax_over_error
pm
pmra
pmra_error
pmdec
pmdec_error
radial_velocity
radial_velocity_error
phot_g_mean_mag
phot_bp_mean_mag
phot_rp_mean_mag
bp_rp
ruwe
duplicated_source
astrometric_params_solved
visibility_periods_used
phot_variable_flag
non_single_star
teff_gspphot
distance_gspphot
distance_gspphot_lower
distance_gspphot_upper
```

### 4.2 Minimal background fields

```text
source_id
ra
dec
l
b
parallax
parallax_over_error
phot_g_mean_mag
bp_rp
ruwe
distance_gspphot
```

The background query should remain minimal because every extra column increases upstream execution time, download size, parsing memory, and disk use.

## 5. NASA Exoplanet Archive fields

Columns retrieved into the PSCompPars snapshot (`refresh-pscomppars`).

### 5.1 Identity and names

```text
pl_name
hostname
pl_letter
hd_name
hip_name
tic_id
gaia_dr3_id
```

### 5.2 Coordinates and system

```text
ra
dec
sy_dist
sy_snum
sy_pnum
cb_flag
```

### 5.3 Stellar properties

```text
st_teff
st_mass
st_rad
st_lum
```

### 5.4 Planetary properties

```text
pl_rade
pl_bmasse
pl_bmassprov
pl_dens
pl_eqt
pl_insol
```

### 5.5 Orbital properties

```text
pl_orbper
pl_orbsmax
pl_orbeccen
pl_orbincl
```

### 5.6 Discovery metadata

```text
discoverymethod
disc_year
disc_facility
pl_controv_flag
```

## 6. Entity schemas

Published PSCompPars domain tables use stable `nea:{kind}:{search_key}` identifiers.
Exact Gaia host enrichment is a separate canonical step that publishes
`gaia_host_sources.parquet` from the committed `gaia_hosts` snapshot. Curated
`display_name` / `name_source` fields and fallback match metadata remain later
work.

Processed files:

```text
data/processed/exoplanets.parquet
data/processed/exoplanet_hosts.parquet
data/processed/exoplanet_systems.parquet
data/processed/gaia_host_ids.parquet
data/processed/gaia_host_sources.parquet
data/processed/review_invalid_exoplanet_rows.parquet
data/processed/review_host_stellar_conflicts.parquet
data/processed/review_system_planet_count_mismatches.parquet
```

### 6.1 Host (`exoplanet_hosts.parquet`)

One row per exact NASA `host_name`. Stellar properties come from the selected planet-row candidate (`stellar_selection_method = most_complete_then_planet_name`).

```text
host_id                      string
host_name                    string
hd_name                      string nullable
hip_name                     string nullable
tic_id                       string nullable
gaia_dr3_designation         string nullable
gaia_source_id               int64 nullable
ra_deg                       float64
dec_deg                      float64
system_distance_pc           float64 nullable
star_count                   int16
planet_count                 int16
is_circumbinary              bool
stellar_temperature_k        float64 nullable
stellar_mass_solar           float64 nullable
stellar_radius_solar         float64 nullable
stellar_luminosity_log_solar float64 nullable
stellar_fields_available     uint8
stellar_source_planet_name   string
stellar_selection_method     string
stellar_values_conflict      bool
source                       string
```

### 6.2 Gaia host source (`gaia_host_sources.parquet`)

Published by the canonical build from the committed multi-file snapshot at
`data/raw/gaia_hosts/current/`. One row per exact Gaia DR3 source ID from the
host-ID manifest. Distance fields are selected offline with explicit method and
quality provenance. Heliocentric Cartesian coordinates (parsecs) and
Galactocentric Cartesian coordinates (kiloparsecs, Astropy `v4.0` frame) are
derived from the selected distance and Galactic sky position. Sources without an
accepted distance leave all six spatial columns null.

Current expectations: 4,396 rows; 109 with `distance_method = unavailable`
(and matching null spatial coordinates).

```text
gaia_source_id                         int64
gaia_dr3_designation                   string
reference_epoch                        float64
ra_deg                                 float64
dec_deg                                float64
galactic_longitude_deg                 float64
galactic_latitude_deg                  float64
parallax_mas                           float64 nullable
parallax_error_mas                     float64 nullable
parallax_over_error                    float64 nullable
proper_motion_mas_per_year             float64 nullable
proper_motion_ra_mas_per_year          float64 nullable
proper_motion_ra_error_mas_per_year    float64 nullable
proper_motion_dec_mas_per_year         float64 nullable
proper_motion_dec_error_mas_per_year   float64 nullable
radial_velocity_km_per_s               float64 nullable
radial_velocity_error_km_per_s         float64 nullable
phot_g_mean_magnitude                  float64 nullable
phot_bp_mean_magnitude                 float64 nullable
phot_rp_mean_magnitude                 float64 nullable
bp_rp_color                            float64 nullable
ruwe                                   float64 nullable
duplicated_source                      bool
astrometric_params_solved              int8
visibility_periods_used                int16 nullable
phot_variable_flag                     string nullable
non_single_star                        int16 nullable
temperature_gspphot_k                  float64 nullable
distance_gspphot_pc                    float64 nullable
distance_gspphot_lower_pc              float64 nullable
distance_gspphot_upper_pc              float64 nullable
distance_pc                            float64 nullable
distance_lower_pc                      float64 nullable
distance_upper_pc                      float64 nullable
distance_method                        string
distance_quality                       string
heliocentric_x_pc                      float64 nullable
heliocentric_y_pc                      float64 nullable
heliocentric_z_pc                      float64 nullable
galactocentric_x_kpc                   float64 nullable
galactocentric_y_kpc                   float64 nullable
galactocentric_z_kpc                   float64 nullable
source                                 string
```

### 6.3 Planetary system (`exoplanet_systems.parquet`)

Provisional systems are host-scoped (`system_grouping_method = exact_host_name`). `planet_count` is derived from published planets; `archive_planet_count` is NASA `sy_pnum`.

```text
system_id                      string
host_id                        string
host_name                      string
star_count                     int16
planet_count                   int16
archive_planet_count           int16
planet_count_matches_archive   bool
system_distance_pc             float64 nullable
is_circumbinary                bool
system_grouping_method         string
source                         string
```

### 6.4 Planet (`exoplanets.parquet`)

```text
planet_id                    string
system_id                    string
host_id                      string
planet_name                  string
planet_letter                string nullable
radius_earth                 float64 nullable
mass_earth                   float64 nullable
mass_provenance              string nullable
density_g_cm3                float64 nullable
equilibrium_temperature_k    float64 nullable
insolation_earth             float64 nullable
orbital_period_days          float64 nullable
semi_major_axis_au           float64 nullable
eccentricity                 float64 nullable
inclination_deg              float64 nullable
discovery_method             string nullable
discovery_year               int16 nullable
discovery_facility           string nullable
is_controversial             bool
source                       string
```

### 6.5 Density cell (`gaia_density_cells.parquet`)

```text
grid_level               uint16
cell_x                   int32
cell_y                   int32
distance_tier            string
source_count             uint32
weighted_brightness      float32
mean_bp_rp               float32 nullable
```

### 6.6 Name table (planned render-index)

A separate compact name-index table remains planned for denser future render
files. The current identity catalogue uses `stars.parquet` and `alias.parquet`
instead (see §6.7).

### 6.7 Identity tables

#### `stars.parquet`

Canonical IAU-named stars (plus enrichment) used by search:

```text
star_id
name_key
canonical_display_name
object_type
designation
hip
… enrichment and future Gaia columns …
```

#### `alias.parquet`

Alternate designations keyed to `star_id` for prefix/exact search.

#### `exoplanet_host_links.parquet`

Links NASA exoplanet hosts into the identity catalogue.

## 7. Name policy

The MVP display-name order is:

1. NASA `hostname`;
2. HD catalogue name;
3. Hipparcos name;
4. Gaia DR3 designation.

This does not imply that all names are common proper names. Names such as `Kepler-22`, `HD 209458`, and `HIP ...` are readable catalogue identifiers and are still preferable to a bare numeric Gaia ID.

## 8. Distance policy

### 8.1 Preferred methods

```text
GSP-Phot distance
    → model-derived Gaia estimate

inverse parallax
    → only for positive, sufficiently precise parallaxes

unavailable
    → source omitted from top-down spatial views
```

### 8.2 Exact-host inverse-parallax criteria

Suggested defaults:

```text
parallax > 0
parallax_over_error >= 5
ruwe is null or ruwe < 1.4
```

These values are configurable project criteria, not universal scientific truth.

### 8.3 Background density distance tiers

The statistical Gaia background uses two renderable distance tiers.

```text
baseline
    → positive GSP-Phot distance; or
    → positive inverse parallax with parallax_over_error >= 5
      and RUWE null or below 1.4

exploratory
    → no positive GSP-Phot distance
    → positive inverse parallax
    → 2 <= parallax_over_error < 5
    → RUWE null or below 1.4

unavailable
    → no distance accepted by either policy
```

GSP-Phot takes precedence when both distance methods are available.
Gaia `parallax_over_error` is the parallax signal-to-noise ratio. Its
reciprocal approximates fractional parallax uncertainty: S/N 5 corresponds
to approximately 20%, while S/N 2 corresponds to approximately 50%.
Direct inversion becomes increasingly unstable at lower signal-to-noise,
so exploratory density is visually distinguished and requires explicit
user opt-in.

This tiering applies only to the statistical Gaia background. Exact
exoplanet-host positions continue to use the stricter baseline policy.

The inverse-parallax limitation follows the discussion in
Coryn A. L. Bailer-Jones 2015 PASP 127 994
['https://iopscience.iop.org/article/10.1086/683116']

### 8.4 Required provenance

Every spatial record stores:

```text
distance_method
distance_quality
distance_lower_pc
distance_upper_pc
```

Published `distance_quality` values for exact Gaia hosts:

```text
positive_gspphot_estimate
    → GSP-Phot distance accepted

snr_ge_5_ruwe_acceptable
    → inverse-parallax distance accepted

unavailable
    → no accepted distance
```

## 9. Coordinate policy

### Sky views

- ICRS RA/Dec;
- Galactic longitude/latitude.

### Earth-centred exoplanet view

- heliocentric Cartesian coordinates from Galactic `(l, b)` and `distance_pc`;
- units: parsecs;
- Sun at the origin;
- `x`/`y` in the Galactic plane, `z` height from the plane.

### Milky Way top-down view

- Galactocentric Cartesian coordinates via Astropy `SkyCoord` → `Galactocentric`;
- units: kiloparsecs;
- Galactic centre at origin;
- frozen Astropy parameter set `v4.0` (Sun near `(-8.122, 0, 0.0208)` kpc);
- Sun shown separately.

The implemented v1 manifest records the build identity, source-snapshot
checksums, and artifact checksums, sizes, and row counts. Query text, Gaia job
IDs, transformation versions, and the Galactocentric parameter set remain
planned provenance fields.

## 10. Quality policy

### Gaia quality fields retained

- parallax uncertainty;
- parallax signal-to-noise;
- RUWE;
- duplicated-source flag;
- astrometric solution type;
- visibility periods;
- variability flag;
- non-single-star flag.

### UI quality categories

```text
high confidence
usable with limitations
sky position only
unavailable
```

Quality categories affect spatial inclusion and disclosure, not the existence of the source record.

## 11. Provenance categories

| Category | Meaning |
|---|---|
| Observed | Direct catalogue measurement |
| Derived | Project calculation from measured values |
| Estimated | Model-derived catalogue value |
| Inferred | Project classification based on several values |
| Procedurally visualized | Artistic visual generated from data |
| Unknown | No accepted value available |

## 12. Frontend file schemas

### 12.1 Milky Way density Arrow (`milky-way-density.arrow`)

Published by `build-gaia-density` to `data/frontend/milky-way-density.arrow`,
copied into the immutable release, and served at
`/data/milky-way-density.arrow` from the active build.

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
mean_bp_rp
```

### 12.2 Exoplanet-host Arrow (`exoplanet_hosts.arrow`)

Published by the pipelines visualization flow to
`data/frontend/exoplanet_hosts.arrow`, copied into the immutable release, and
served at `/data/exoplanet_hosts.arrow` from the active build. One row per
NASA exoplanet host, joined with system counts and exact Gaia spatial fields
when available.

```text
host_id                            string
host_name                          string
gaia_source_id                     int64 nullable
planet_count                       int16
archive_planet_count               int16
planet_count_matches_archive       bool
is_circumbinary                    bool
position_status                    string
distance_pc                        float64 nullable
distance_method                    string nullable
distance_quality                   string nullable
heliocentric_x_pc                  float64 nullable
heliocentric_y_pc                  float64 nullable
heliocentric_z_pc                  float64 nullable
galactocentric_x_kpc               float64 nullable
galactocentric_y_kpc               float64 nullable
galactocentric_z_kpc               float64 nullable
phot_g_mean_magnitude              float64 nullable
bp_rp_color                        float64 nullable
```

`position_status` is one of `available`, `no_accepted_distance`, or
`no_exact_gaia_source`. Spatial columns are null when no accepted distance or
exact Gaia source exists; the host row is still published.

Frontend decoding notes:

- `gaia_source_id` is an Arrow Int64. The browser stores it as a string because
  Gaia IDs exceed JavaScript's safe integer range.
- Complete x/y/z triples are either all present or all null for each coordinate
  frame.
- Display names currently travel as `host_name` on the same row. A separate
  name-index table remains planned for denser future render files.

### 12.3 Names Arrow or JSON (planned)

```text
name_index
display_name
name_source
```

Complete scientific metadata is not included in global render files.

## 13. Storage budget

The server has 80 GB local disk. The project should target:

| Category | Target |
|---|---:|
| Application, images, and build tools | under 10 GB |
| Current processed dataset | under 10 GB |
| Previous rollback dataset | under 10 GB |
| Raw temporary downloads | under 15 GB |
| Logs and backups | under 5 GB |
| Free safety margin | at least 25 GB |

These are operational targets, not hard limits.

## 14. Retention policy

Keep:

- current public build under `data/builds/{build_id}/`;
- previous public build for rollback;
- current raw NASA snapshot;
- current raw Gaia host snapshot (`data/raw/gaia_hosts/current/`);
- current raw Gaia background snapshot when retained locally
  (`data/raw/gaia_background/current/` — not vendored in git);
- query manifests and checksums.

Delete or archive:

- failed partial outputs;
- duplicate uncompressed files;
- old Gaia background chunks after successful aggregation;
- unused Docker layers;
- expired logs.

## 15. Dataset manifest

`publish-release` writes `schema_version: 1` manifests. `current.json` is a
full copy of `builds/{build_id}/manifest.json`. Example (abbreviated):

```json
{
  "schema_version": 1,
  "build_id": "local-001",
  "created_at": "2026-08-28T19:03:25.492714Z",
  "source_snapshots": {
    "exoplanet_names": "65116f8b…",
    "gaia_background": "2fcfd7e4…",
    "gaia_hosts": "1e009edb…",
    "iau_csn": "1479ce77…",
    "nasa_pscomppars": "1c8ce850…",
    "wgsn_faints": "54cde8e8…"
  },
  "row_counts": {
    "processed/stars.parquet": 605,
    "processed/alias.parquet": 2875,
    "frontend/exoplanet_hosts.arrow": 4749,
    "frontend/milky-way-density.arrow": 2222
  },
  "artifacts": {
    "processed/stars.parquet": {
      "sha256": "7a836ae1…",
      "bytes": 32591,
      "rows": 605
    },
    "processed/alias.parquet": {
      "sha256": "679510f4…",
      "bytes": 37789,
      "rows": 2875
    },
    "frontend/exoplanet_hosts.arrow": {
      "sha256": "a6b1d757…",
      "bytes": 891106,
      "rows": 4749
    },
    "frontend/milky-way-density.arrow": {
      "sha256": "9317885c…",
      "bytes": 77725,
      "rows": 2222
    }
  }
}
```

## 16. Official references

- Gaia data access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
- Gaia Archive: https://gea.esac.esa.int/archive/
- NASA TAP guide: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- NASA PS/PSCompPars columns: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
