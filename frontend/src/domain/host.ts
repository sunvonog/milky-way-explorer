import type { CartesianPosition } from './coordinates'

export type PositionStatus = 'available' | 'no_accepted_distance' | 'no_exact_gaia_source'

/**
 * Distance selection priority:
 * positive Gaia GSP-Phot estimate, qualified inverse parallax, or unavailable.
 */
export type DistanceMethod = 'gaia_gspphot' | 'inverse_parallax' | 'unavailable'

export type DistanceQuality =
  | 'positive_gspphot_estimate'
  | 'snr_ge_5_ruwe_acceptable'
  | 'unavailable'

export interface HostVisualizationRecord {
  hostId: string
  hostName: string

  /** Stored as a string because Gaia IDs exceed JavaScript's safe integer range*/
  gaiaSourceId: string | null

  planetCount: number
  archivePlanetCount: number
  planetCountMatchesArchive: boolean
  isCircumbinary: boolean
  positionStatus: PositionStatus

  /** Selected distance from the sun in parsecs. */
  distancePc: number | null

  distanceMethod: DistanceMethod | null
  distanceQuality: DistanceQuality | null

  /** Sun-centred Galactic Cartesian coordinaets in parsecs. */
  heliocentricPc: CartesianPosition | null

  /** Astropy v4.0 Galactocentric Cartesian coordinates */
  galactocentricKpc: CartesianPosition | null

  photGMeanMagnitude: number | null
  bpRpColor: number | null
}
