export type DensityDistanceTier = 'baseline' | 'exploratory'

export interface DensityVisualizationRecord {
  gridLevel: number
  cellX: number
  cellY: number
  distanceTier: DensityDistanceTier
  cellCenterXKpc: number
  cellCenterYKpc: number
  cellSizeKpc: number
  sourceCount: number
  weightedBrightness: number
  meanBpRp: number | null
}

export interface DensitySelectionOptions {
  includeExploratory?: boolean
}

export function selectDensityRecords(
  records: readonly DensityVisualizationRecord[],
  gridLevel: number,
  options: DensitySelectionOptions = {},
): DensityVisualizationRecord[] {
  return records.filter(
    (record) =>
      record.gridLevel === gridLevel &&
      (record.distanceTier === 'baseline' || options.includeExploratory === true),
  )
}
