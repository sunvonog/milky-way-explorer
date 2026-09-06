import { scaleSqrt } from 'd3'

import type { DensityDistanceTier, DensityVisualizationRecord } from '@/domain/density'

type RgbColor = readonly [red: number, green: number, blue: number]

export const gaiaDensityTierColors: Readonly<Record<DensityDistanceTier, RgbColor>> = {
  baseline: [34, 211, 238],
  exploratory: [251, 191, 36],
}

/**
 * Apply a square-root stretch to source counts:
 * opacity = 0.15 + 0.85 * sqrt(count / maxCount).
 *
 * This display mapping keeps sparsely populated cells visible alongside
 * dense cells. maxCount is at least 1, including for an empty selection.
 */
export function createGaiaDensityOpacityScale(
  records: readonly DensityVisualizationRecord[],
): (sourceCount: number) => number {
  const largestSourceCount = records.reduce(
    (largest, record) => Math.max(largest, record.sourceCount),
    1,
  )

  return scaleSqrt().domain([0, largestSourceCount]).range([0.15, 1]).clamp(true)
}
