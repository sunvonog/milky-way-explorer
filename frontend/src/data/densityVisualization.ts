import { tableFromIPC } from 'apache-arrow'
import type { DensityVisualizationRecord } from '@/domain/density'
import { nullableNumber, requiredNumber, type ArrowRow } from './arrowRow'

const DENSITY_VISUALIZATION_FILENAME = 'milky-way-density.arrow'

export function decodeDensityVisualization(data: Uint8Array): DensityVisualizationRecord[] {
  const table = tableFromIPC(data)

  return Array.from({ length: table.numRows }, (_, index) => {
    const arrowRow = table.get(index)

    if (arrowRow === null) {
      throw new RangeError(`missing Arrow row at index ${index}`)
    }

    const row = arrowRow.toJSON() as ArrowRow

    return {
      gridLevel: requiredNumber(row, 'grid_level'),
      cellX: requiredNumber(row, 'cell_x'),
      cellY: requiredNumber(row, 'cell_y'),
      cellCenterXKpc: requiredNumber(row, 'cell_center_x_kpc'),
      cellCenterYKpc: requiredNumber(row, 'cell_center_y_kpc'),
      cellSizeKpc: requiredNumber(row, 'cell_size_kpc'),
      sourceCount: requiredNumber(row, 'source_count'),
      weightedBrightness: requiredNumber(row, 'weighted_brightness'),
      meanBpRp: nullableNumber(row, 'mean_bp_rp'),
    }
  })
}

export async function loadDensityVisualization(
  baseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<DensityVisualizationRecord[]> {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, '')
  const url = `${normalizedBaseUrl}/${DENSITY_VISUALIZATION_FILENAME}`

  const response = await fetcher(url)

  if (!response.ok) {
    throw new Error(
      `failed to load density visualization: ${response.status} ${response.statusText}`,
    )
  }

  const data = new Uint8Array(await response.arrayBuffer())

  return decodeDensityVisualization(data)
}
