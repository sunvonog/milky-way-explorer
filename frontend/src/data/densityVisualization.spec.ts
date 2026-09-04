import { tableFromArrays, tableToIPC } from 'apache-arrow'
import { describe, expect, it, vi } from 'vitest'

import { decodeDensityVisualization, loadDensityVisualization } from '@/data/densityVisualization'

function densityArrowFixture(distanceTiers: string[] = ['baseline', 'exploratory']): Uint8Array {
  return tableToIPC(
    tableFromArrays({
      grid_level: [128, 128],
      cell_x: [20, 21],
      cell_y: [30, 31],
      distance_tier: distanceTiers,
      cell_center_x_kpc: [-13.59375, -13.28125],
      cell_center_y_kpc: [-10.46875, -10.15625],
      cell_size_kpc: [0.3125, 0.3125],
      source_count: [7, 3],
      weighted_brightness: [0.25, 0.1],
      mean_bp_rp: [0.8, null],
    }),
    'file',
  )
}

function responseBody(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer
}

describe('decodeDensityVisualization', () => {
  it('decodes density cells into the frontend model', () => {
    const records = decodeDensityVisualization(densityArrowFixture())

    expect(records).toEqual([
      {
        gridLevel: 128,
        cellX: 20,
        cellY: 30,
        distanceTier: 'baseline',
        cellCenterXKpc: -13.59375,
        cellCenterYKpc: -10.46875,
        cellSizeKpc: 0.3125,
        sourceCount: 7,
        weightedBrightness: 0.25,
        meanBpRp: 0.8,
      },
      {
        gridLevel: 128,
        cellX: 21,
        cellY: 31,
        distanceTier: 'exploratory',
        cellCenterXKpc: -13.28125,
        cellCenterYKpc: -10.15625,
        cellSizeKpc: 0.3125,
        sourceCount: 3,
        weightedBrightness: 0.1,
        meanBpRp: null,
      },
    ])
  })

  it('rejects an unknown distance tier', () => {
    expect(() => decodeDensityVisualization(densityArrowFixture(['baseline', 'unknown']))).toThrow(
      'unknown distance_tier: unknown',
    )
  })
})

describe('loadDensityVisualization', () => {
  it('loads the density Arrow artifact from the backend', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(responseBody(densityArrowFixture()), {
        status: 200,
      }),
    )

    const records = await loadDensityVisualization('http://localhost:8000/data', fetcher)
    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/data/milky-way-density.arrow')
    expect(records).toHaveLength(2)
  })

  it('reports an unsuccessful response', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(null, {
        status: 503,
        statusText: 'Service Unavailable',
      }),
    )

    await expect(loadDensityVisualization('http://localhost:8000/data', fetcher)).rejects.toThrow(
      'failed to load density visualization: 503 Service Unavailable',
    )
  })
})
