// frontend/src/lib/coords.spec.ts
import { describe, it, expect } from 'vitest'
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
