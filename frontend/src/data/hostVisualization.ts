import { tableFromIPC } from 'apache-arrow'

const HOST_VISUALIZATION_FILENAME = 'exoplanet_hosts.arrow'

export type PositionStatus = 'available' | 'no_accepted_distance' | 'no_exact_gaia_source'

export type DistanceMethod = 'gaia_gspphot' | 'inverse_parallax' | 'unavailable'

export type DistanceQuality =
  | 'positive_gspphot_estimate'
  | 'snr_ge_5_ruwe_acceptable'
  | 'unavailable'

export interface CartesianPosition {
  x: number
  y: number
  z: number
}

export interface HostVisualizationRecord {
  hostId: string
  hostName: string
  gaiaSourceId: string | null
  planetCount: number
  archivePlanetCount: number
  planetCountMatchesArchive: boolean
  isCircumbinary: boolean
  positionStatus: PositionStatus
  distancePc: number | null
  distanceMethod: DistanceMethod | null
  distanceQuality: DistanceQuality | null
  heliocentricPc: CartesianPosition | null
  galactocentricKpc: CartesianPosition | null
  photGMeanMagnitude: number | null
  bpRpColor: number | null
}

type ArrowRow = Record<string, unknown>

function requiredString(row: ArrowRow, field: string): string {
  const value = row[field]

  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string`)
  }

  return value
}

function requiredNumber(row: ArrowRow, field: string): number {
  const value = row[field]

  if (typeof value !== 'number') {
    throw new TypeError(`${field} must be a number`)
  }

  return value
}

function requiredBoolean(row: ArrowRow, field: string): boolean {
  const value = row[field]

  if (typeof value !== 'boolean') {
    throw new TypeError(`${field} must be a boolean`)
  }

  return value
}

function nullableString(row: ArrowRow, field: string): string | null {
  const value = row[field]

  if (value === null) {
    return null
  }

  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string or null`)
  }

  return value
}

function nullableNumber(row: ArrowRow, field: string): number | null {
  const value = row[field]

  if (value === null) {
    return null
  }

  if (typeof value !== 'number') {
    throw new TypeError(`${field} must be a number or null`)
  }

  return value
}

function nullableGaiaSourceId(row: ArrowRow, field: string): string | null {
  const value = row[field]

  if (value === null) {
    return null
  }

  if (typeof value !== 'bigint' && typeof value !== 'string') {
    throw new TypeError(`${field} must be an Int64 or null`)
  }

  return value.toString()
}

function positionStatus(row: ArrowRow): PositionStatus {
  const value = requiredString(row, 'position_status')

  switch (value) {
    case 'available':
    case 'no_accepted_distance':
    case 'no_exact_gaia_source':
      return value
    default:
      throw new TypeError(`unknown position_status: ${value}`)
  }
}

function distanceMethod(row: ArrowRow): DistanceMethod | null {
  const value = nullableString(row, 'distance_method')

  switch (value) {
    case null:
    case 'gaia_gspphot':
    case 'inverse_parallax':
    case 'unavailable':
      return value
    default:
      throw new TypeError(`unknown distance_method: ${value}`)
  }
}

function distanceQuality(row: ArrowRow): DistanceQuality | null {
  const value = nullableString(row, 'distance_quality')

  switch (value) {
    case null:
    case 'positive_gspphot_estimate':
    case 'snr_ge_5_ruwe_acceptable':
    case 'unavailable':
      return value
    default:
      throw new TypeError(`unknown distance_quality: ${value}`)
  }
}

function nullablePosition(
  row: ArrowRow,
  xField: string,
  yField: string,
  zField: string,
): CartesianPosition | null {
  const x = nullableNumber(row, xField)
  const y = nullableNumber(row, yField)
  const z = nullableNumber(row, zField)

  if (x === null && y === null && z === null) {
    return null
  }

  if (x === null || y === null || z === null) {
    throw new TypeError(
      `${xField}, ${yField}, and ${zField} must be either all numbers or all null`,
    )
  }

  return { x, y, z }
}

export function decodeHostVisualization(data: Uint8Array): HostVisualizationRecord[] {
  const table = tableFromIPC(data)

  return Array.from({ length: table.numRows }, (_, index) => {
    const arrowRow = table.get(index)

    if (arrowRow === null) {
      throw new RangeError(`missing Arrow row at index ${index}`)
    }

    const row = arrowRow.toJSON() as ArrowRow

    return {
      hostId: requiredString(row, 'host_id'),
      hostName: requiredString(row, 'host_name'),
      gaiaSourceId: nullableGaiaSourceId(row, 'gaia_source_id'),
      planetCount: requiredNumber(row, 'planet_count'),
      archivePlanetCount: requiredNumber(row, 'archive_planet_count'),
      planetCountMatchesArchive: requiredBoolean(row, 'planet_count_matches_archive'),
      isCircumbinary: requiredBoolean(row, 'is_circumbinary'),
      positionStatus: positionStatus(row),
      distancePc: nullableNumber(row, 'distance_pc'),
      distanceMethod: distanceMethod(row),
      distanceQuality: distanceQuality(row),
      heliocentricPc: nullablePosition(
        row,
        'heliocentric_x_pc',
        'heliocentric_y_pc',
        'heliocentric_z_pc',
      ),
      galactocentricKpc: nullablePosition(
        row,
        'galactocentric_x_kpc',
        'galactocentric_y_kpc',
        'galactocentric_z_kpc',
      ),
      photGMeanMagnitude: nullableNumber(row, 'phot_g_mean_magnitude'),
      bpRpColor: nullableNumber(row, 'bp_rp_color'),
    }
  })
}

export async function loadHostVisualization(
  baseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<HostVisualizationRecord[]> {
  const normalizedBaseURL = baseUrl.replace(/\/+$/, '')
  const url = `${normalizedBaseURL}/${HOST_VISUALIZATION_FILENAME}`

  const response = await fetcher(url)

  if (!response.ok) {
    throw new Error(`failed to load host visualization: ${response.status} ${response.statusText}`)
  }

  const data = new Uint8Array(await response.arrayBuffer())

  return decodeHostVisualization(data)
}
