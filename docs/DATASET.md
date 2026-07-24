# Dataset Design

## 1. Scope

The MVP uses two upstream datasets:

1. **Gaia DR3** for astrometry, photometry, motion, source quality, and model-derived stellar parameters.
2. **NASA Exoplanet Archive `PSCompPars`** for confirmed planets, host names, host identifiers, system metadata, and orbital properties.

DESI is explicitly excluded from the MVP.

SIMBAD and other naming catalogues may be added later, but the first readable-name layer is based on NASA exoplanet hosts.

## 2. Public dataset composition

```text
public_build =
    gaia_density_cells
    + exoplanet_hosts
    + gaia_host_sources
    + planetary_systems
    + planets
    + names
    + build_manifest
```

A random Gaia sample is not part of the required public dataset.

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

The existing 10,000-source sample is retained as a development fixture.

It is used to test:

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

### 5.1 Identity and names

```text
pl_name
hostname
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
```

## 6. Entity schemas

### 6.1 Host

```text
host_id                 string
hostname                string
gaia_source_id          int64 nullable
gaia_designation        string nullable
hd_name                 string nullable
hip_name                string nullable
tic_id                   string nullable
display_name            string
name_source              string
ra_deg                   float64
dec_deg                  float64
system_distance_pc       float64 nullable
planet_count             int16
star_count               int16
match_method             string
match_confidence         string
```

### 6.2 Gaia host source

```text
gaia_source_id           int64
ref_epoch                float32
ra_deg                   float64
dec_deg                  float64
galactic_l_deg           float64
galactic_b_deg           float64
parallax_mas             float32 nullable
parallax_error_mas       float32 nullable
parallax_over_error      float32 nullable
pmra_mas_year            float32 nullable
pmdec_mas_year           float32 nullable
radial_velocity_kms      float32 nullable
g_magnitude              float32 nullable
bp_rp                    float32 nullable
temperature_k            float32 nullable
ruwe                      float32 nullable
distance_pc              float32 nullable
distance_method          string
distance_quality         string
heliocentric_x_pc        float32 nullable
heliocentric_y_pc        float32 nullable
heliocentric_z_pc        float32 nullable
galactocentric_x_kpc     float32 nullable
galactocentric_y_kpc     float32 nullable
galactocentric_z_kpc     float32 nullable
```

### 6.3 Planetary system

```text
system_id                string
host_id                  string
planet_count             int16
star_count               int16
system_distance_pc       float32 nullable
```

### 6.4 Planet

```text
planet_id                string
system_id                string
planet_name              string
radius_earth             float32 nullable
mass_earth               float32 nullable
density_g_cm3            float32 nullable
equilibrium_temp_k       float32 nullable
insolation_earth         float32 nullable
orbital_period_days      float64 nullable
semi_major_axis_au       float64 nullable
eccentricity             float32 nullable
inclination_deg          float32 nullable
discovery_method         string nullable
discovery_year           int16 nullable
discovery_facility       string nullable
```

### 6.5 Density cell

```text
grid_level               uint8
cell_x                   int32
cell_y                   int32
source_count             uint32
weighted_brightness      float32
mean_bp_rp               float32 nullable
mean_distance_quality    float32
```

### 6.6 Name table

```text
name_index               uint32
entity_type              string
entity_id                string
display_name             string
name_source              string
aliases                   list<string>
label_priority           uint16
```

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

### 8.2 Prototype inverse-parallax criteria

Suggested defaults:

```text
parallax > 0
parallax_over_error >= 5
ruwe is null or ruwe < 1.4
```

These values are configurable project criteria, not universal scientific truth.

### 8.3 Required provenance

Every spatial record stores:

```text
distance_method
distance_quality
distance_lower_pc
distance_upper_pc
```

## 9. Coordinate policy

### Sky views

- ICRS RA/Dec;
- Galactic longitude/latitude.

### Earth-centred exoplanet view

- heliocentric Cartesian coordinates;
- units: parsecs.

### Milky Way top-down view

- Galactocentric Cartesian coordinates;
- units: kiloparsecs;
- Galactic centre at origin;
- Sun shown separately.

The build manifest records the Astropy frame configuration.

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

### 12.1 Milky Way density Arrow

```text
grid_level
cell_x
cell_y
source_count
weighted_brightness
mean_bp_rp
```

### 12.2 Exoplanet-host Arrow

```text
gaia_source_id
host_index
name_index
heliocentric_x_pc
heliocentric_y_pc
galactocentric_x_kpc
galactocentric_y_kpc
g_magnitude
bp_rp
render_radius
planet_count
flags
```

### 12.3 Names Arrow or JSON

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

- current public build;
- previous public build;
- current raw NASA snapshot;
- successful Gaia host batches;
- query manifests and checksums.

Delete or archive:

- failed partial outputs;
- duplicate uncompressed files;
- old Gaia background chunks after successful aggregation;
- unused Docker layers;
- expired logs.

## 15. Dataset manifest

Example:

```json
{
  "build_id": "2026-07-24.1",
  "gaia_release": "DR3",
  "exoplanet_snapshot": "2026-07-24",
  "gaia_background_mode": "chunked_random_sample",
  "gaia_background_source_count": 10000,
  "matched_host_count": 0,
  "distance_policy_version": "1.0.0",
  "coordinate_pipeline_version": "1.0.0",
  "galactocentric_parameter_set": "v4.0",
  "files": [],
  "checksums": {}
}
```

## 16. Official references

- Gaia data access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
- Gaia Archive: https://gea.esac.esa.int/archive/
- NASA TAP guide: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- NASA PS/PSCompPars columns: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
