// frontend/src/lib/coords.spec.ts
import { describe, it, expect } from 'vitest'
import {
  galacticToHeliocentric,
  SUN_GALACTOCENTRIC_R_KPC,
  SUN_GALACTOCENTRIC_X_KPC,
  SUN_GALACTOCENTRIC_Z_KPC,
} from './coords'

describe('galacticToHeliocentric', () => {
  it('places l=0, b=0 along +x', () => {
    const p = galacticToHeliocentric({ lDeg: 0, bDeg: 0, distanceKpc: 1 })
    expect(p.x).toBeCloseTo(1, 10)
    expect(p.y).toBeCloseTo(0, 10)
    expect(p.z).toBeCloseTo(0, 10)
  })

  it('places l=90, b=0, along +y', () => {
    const p = galacticToHeliocentric({ lDeg: 90, bDeg: 0, distanceKpc: 2 })
    expect(p.x).toBeCloseTo(0, 10)
    expect(p.y).toBeCloseTo(2, 10)
  })

  it('places b=90 at the north Galactic pole', () => {
    const p = galacticToHeliocentric({ lDeg: 123, bDeg: 90, distanceKpc: 3 })
    expect(p.z).toBeCloseTo(3, 10)
  })

  it('places the Sun at the adopted Galactocentric distance and height', () => {
    expect(Math.hypot(SUN_GALACTOCENTRIC_X_KPC, SUN_GALACTOCENTRIC_Z_KPC)).toBeCloseTo(
      SUN_GALACTOCENTRIC_R_KPC,
      10,
    )

    expect(SUN_GALACTOCENTRIC_X_KPC).toBeLessThan(0)
    expect(SUN_GALACTOCENTRIC_Z_KPC).toBe(0.0208)
  })
})
