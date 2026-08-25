import {
  SUN_GALACTOCENTRIC_R_KPC,
  SUN_GALACTOCENTRIC_X_KPC,
  SUN_GALACTOCENTRIC_Z_KPC,
  type CartesianPosition,
} from './coordinates'

export const coordinateFrameIds = ['heliocentric', 'galactocentric'] as const

export type CoordinateFrameId = (typeof coordinateFrameIds)[number]

export type PositionField = 'heliocentricPc' | 'galactocentricKpc'

export interface CoordinateFramePresentation {
  label: string
  unit: string
  description: string
  positionField: PositionField
  sunPosition: CartesianPosition
  galacticCentrePosition: CartesianPosition
}

/**
 * Plot reference points expressed in each frame's native units
 *
 * The Galactocentric frame matches the Astropy v4.0 coordinates produced by
 * the pipeline
 */
export const coordinateFrames = {
  heliocentric: {
    label: 'Heliocentric',
    unit: 'pc',
    description: 'Top-down Cartesian view centred on the Sun.',
    positionField: 'heliocentricPc',
    sunPosition: { x: 0, y: 0, z: 0 },
    galacticCentrePosition: {
      x: SUN_GALACTOCENTRIC_R_KPC * 1000,
      y: 0,
      z: 0,
    },
  },
  galactocentric: {
    label: 'Galactocentric',
    unit: 'kpc',
    description: 'Top-down Cartesian view centred on the Milky Way centre.',
    positionField: 'galactocentricKpc',
    sunPosition: { x: SUN_GALACTOCENTRIC_X_KPC, y: 0, z: SUN_GALACTOCENTRIC_Z_KPC },
    galacticCentrePosition: {
      x: 0,
      y: 0,
      z: 0,
    },
  },
} satisfies Record<CoordinateFrameId, CoordinateFramePresentation>
