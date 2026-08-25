import { describe, expect, it } from 'vitest'
import { coordinateFrameIds, coordinateFrames, type CoordinateFrameId } from './coordinateFrames'

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

  it.each<CoordinateFrameId>(coordinateFrameIds)(
    'defines both reference points in the %s frame',
    (frameId) => {
      const frame = coordinateFrames[frameId]

      expect(frame.sunPosition).toBeDefined()
      expect(frame.galacticCentrePosition).toBeDefined()
    },
  )
})
