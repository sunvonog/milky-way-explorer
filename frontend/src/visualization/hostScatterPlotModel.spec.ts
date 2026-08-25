import { describe, it, expect } from 'vitest'

import type { HostVisualizationRecord } from '@/domain/host'
import { buildHostScatterPlotModel } from '@/visualization/hostScatterPlotModel'

function host(overrides: Partial<HostVisualizationRecord>): HostVisualizationRecord {
  return {
    hostId: 'nea:host:default',
    hostName: 'Default',
    gaiaSourceId: '101',
    planetCount: 1,
    archivePlanetCount: 1,
    planetCountMatchesArchive: true,
    isCircumbinary: false,
    positionStatus: 'available',
    distancePc: 10,
    distanceMethod: 'gaia_gspphot',
    distanceQuality: 'positive_gspphot_estimate',
    heliocentricPc: { x: 10, y: 0, z: 0 },
    galactocentricKpc: { x: -8.112, y: 0, z: 0.0208 },
    photGMeanMagnitude: 7.2,
    bpRpColor: 0.8,
    ...overrides,
  }
}

describe('buildHostScatterPlotModel', () => {
  it('selects only hosts positioned in the request frame', () => {
    const records = [
      host({
        hostId: 'nea:host:heliocentric',
        heliocentricPc: { x: 10, y: 0, z: 0 },
        galactocentricKpc: null,
      }),
      host({
        hostId: 'nea:host:galactocentric',
        heliocentricPc: null,
        galactocentricKpc: { x: -8, y: 1, z: 0.02 },
      }),
    ]

    const heliocentric = buildHostScatterPlotModel(records, 'heliocentric')
    const galactocentric = buildHostScatterPlotModel(records, 'galactocentric')

    expect(heliocentric.hostPoints.map(({ record }) => record.hostId)).toEqual([
      'nea:host:heliocentric',
    ])
    expect(galactocentric.hostPoints.map(({ record }) => record.hostId)).toEqual([
      'nea:host:galactocentric',
    ])
  })

  it('uses the same physical scale for the x and y axes', () => {
    const model = buildHostScatterPlotModel(
      [
        host({
          hostId: 'nea:host:x',
          heliocentricPc: { x: 10, y: 0, z: 0 },
        }),
        host({
          hostId: 'nea:host:y',
          heliocentricPc: { x: 0, y: 10, z: 0 },
        }),
      ],
      'heliocentric',
    )

    const xHost = model.hostPoints.find(({ record }) => record.hostId === 'nea:host:x')
    const yHost = model.hostPoints.find(({ record }) => record.hostId === 'nea:host:y')

    expect(xHost).toBeDefined()
    expect(yHost).toBeDefined()

    expect(Math.abs(xHost!.x - model.sun.x)).toBeCloseTo(Math.abs(yHost!.y - model.sun.y), 8)
  })

  it('uses planet count to determine point radius', () => {
    const model = buildHostScatterPlotModel(
      [
        host({
          hostId: 'nea:host:one',
          planetCount: 1,
        }),
        host({
          hostId: 'nea:host:four',
          planetCount: 4,
        }),
      ],
      'heliocentric',
    )

    const onePlanet = model.hostPoints.find(({ record }) => record.hostId === 'nea:host:one')
    const fourPlanets = model.hostPoints.find(({ record }) => record.hostId === 'nea:host:four')

    expect(onePlanet).toBeDefined()
    expect(fourPlanets).toBeDefined()
    expect(fourPlanets!.radius).toBeGreaterThan(onePlanet!.radius)
  })
})
