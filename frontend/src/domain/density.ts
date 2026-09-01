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
