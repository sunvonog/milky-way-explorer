// frontend/src/lib/coords.spec.ts
import { describe, it, expect } from 'vitest'
import { galacticToHeliocentric } from './coords'

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
})
