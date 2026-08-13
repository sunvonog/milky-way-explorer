import { tableFromArrays, tableToIPC } from 'apache-arrow'
import { describe, expect, it, vi } from 'vitest'

import { decodeHostVisualization, loadHostVisualization } from './hostVisualization'

function visualizationArrowFixture(): Uint8Array {
  const table = tableFromArrays({
    host_id: ['nea:host:alpha', 'nea:host:beta'],
    host_name: ['Alpha', 'Beta'],
    gaia_source_id: [3946945413106333696n, null],
    planet_count: [2, 1],
    archive_planet_count: [3, 1],
    planet_count_matches_archive: [false, true],
    is_circumbinary: [false, true],
    position_status: ['available', 'no_exact_gaia_source'],
    distance_pc: [10, null],
    distance_method: ['inverse_parallax', null],
    distance_quality: ['snr_ge_5_ruwe_acceptable', null],
    heliocentric_x_pc: [10, null],
    heliocentric_y_pc: [0, null],
    heliocentric_z_pc: [0, null],
    galactocentric_x_kpc: [-8.112, null],
    galactocentric_y_kpc: [0, null],
    galactocentric_z_kpc: [0.0208, null],
    phot_g_mean_magnitude: [7.2, null],
    bp_rp_color: [0.8, null],
  })

  return tableToIPC(table, 'file')
}

describe('decodeHostVisualization', () => {
  it('decodes an available host into the frontend model', () => {
    const records = decodeHostVisualization(visualizationArrowFixture())

    expect(records[0]).toEqual({
      hostId: 'nea:host:alpha',
      hostName: 'Alpha',
      gaiaSourceId: '3946945413106333696',
      planetCount: 2,
      archivePlanetCount: 3,
      planetCountMatchesArchive: false,
      isCircumbinary: false,
      positionStatus: 'available',
      distancePc: 10,
      distanceMethod: 'inverse_parallax',
      distanceQuality: 'snr_ge_5_ruwe_acceptable',
      heliocentricPc: {
        x: 10,
        y: 0,
        z: 0,
      },
      galactocentricKpc: {
        x: -8.112,
        y: 0,
        z: 0.0208,
      },
      photGMeanMagnitude: 7.2,
      bpRpColor: 0.8,
    })
  })

  it('retains a host without a renderable position', () => {
    const records = decodeHostVisualization(visualizationArrowFixture())

    expect(records[1]).toMatchObject({
      hostId: 'nea:host:beta',
      gaiaSourceId: null,
      positionStatus: 'no_exact_gaia_source',
      distancePc: null,
      distanceMethod: null,
      heliocentricPc: null,
      galactocentricKpc: null,
    })
  })
})

function responseBody(data: Uint8Array): ArrayBuffer {
  const buffer = new ArrayBuffer(data.byteLength)
  new Uint8Array(buffer).set(data)
  return buffer
}

describe('loadHostVisualization', () => {
  it.each(['https://example.test/data', 'https://example.test/data/'])(
    'loads and decodes the Arrow artifact from %s',
    async (baseUrl) => {
      const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
        new Response(responseBody(visualizationArrowFixture()), {
          status: 200,
        }),
      )

      const records = await loadHostVisualization(baseUrl, fetcher)

      expect(fetcher).toHaveBeenCalledOnce()
      expect(fetcher).toHaveBeenCalledWith('https://example.test/data/exoplanet_hosts.arrow')
      expect(records).toHaveLength(2)
      expect(records[0]?.hostName).toBe('Alpha')
    },
  )

  it('reports an HTTP failure before decoding', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(null, {
        status: 503,
        statusText: 'Service Unavailable',
      }),
    )

    await expect(loadHostVisualization('https://example.test/data', fetcher)).rejects.toThrow(
      'failed to load host visualization: 503 Service Unavailable',
    )
  })
})
