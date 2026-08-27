export interface DensityVisualizationRecord {
  gridLevel: number
  cellX: number
  cellY: number
  cellCenterXKpc: number
  cellCenterYKpc: number
  cellSizeKpc: number
  sourceCount: number
  weightedBrightness: number
  meanBpRp: number | null
}
