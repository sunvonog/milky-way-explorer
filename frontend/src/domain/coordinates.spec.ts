// frontend/src/lib/coords.spec.ts
import { describe, it, expect } from 'vitest'
import { type coordinateFrameId, coordinateFrameIds, coordinateFrames } from './coordinateFrames'
import {
  SUN_GALACTOCENTRIC_R_KPC,
  SUN_GALACTOCENTRIC_X_KPC,
  SUN_GALACTOCENTRIC_Z_KPC,
} from './coordinates'

describe('Galactocentric coordinate references', () => {
  it('places the Sun at the adopted distance and height', () => {
    expect(Math.hypot(SUN_GALACTOCENTRIC_X_KPC, SUN_GALACTOCENTRIC_Z_KPC)).toBeCloseTo(
      SUN_GALACTOCENTRIC_R_KPC,
      10,
    )
    expect(SUN_GALACTOCENTRIC_X_KPC).toBeLessThan(0)
    expect(SUN_GALACTOCENTRIC_Z_KPC).toBe(0.0208)
  })
})

describe('coordinateFrames', () => {
  it('maps each frame to its matching host position and unit', () => {
    expect(coordinateFrameIds).toEqual(['heliocentric', 'galactocentric'])

    expect(coordinateFrames.heliocentric).toMatchObject({
      unit: 'pc',
      positionField: 'heliocentricPc',
    })

    expect(coordinateFrames.galactocentric).toMatchObject({
      unit: 'kpc',
      positionField: 'galactocentricKpc',
    })
  })

  it.each<coordinateFrameId>(coordinateFrameIds)(
    'defines both reference points in the %s frame',
    (frameId) => {
      const frame = coordinateFrames[frameId]

      expect(frame.sunPosition).toBeDefined()
      expect(frame.galacticCentrePosition).toBeDefined()
    },
  )
})
