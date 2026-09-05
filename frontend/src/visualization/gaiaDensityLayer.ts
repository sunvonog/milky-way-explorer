import { PolygonLayer } from '@deck.gl/layers'

import type { Color } from '@deck.gl/core'

import { createGaiaDensityOpacityScale, gaiaDensityTierColors } from './gaiaDensityStyle'

import {
  selectDensityRecords,
  type DensitySelectionOptions,
  type DensityVisualizationRecord,
} from '@/domain/density'

type GalacticVertex = [xKpc: number, yKpc: number, zKpc: number]

/**
 * A square cell centred at (x, y), with side length s, spans
 * x ± s/2 and y ± s/2. Coordinates remain in Galactocentric kpc.
 *
 * z = 0 defines the drawing plane of the aggregated top-down view;
 * it does not describe the individual stars' Galactic heights.
 */
function densityCellPolygon(record: DensityVisualizationRecord): GalacticVertex[] {
  const halfSize = record.cellSizeKpc / 2
  const left = record.cellCenterXKpc - halfSize
  const right = record.cellCenterXKpc + halfSize
  const bottom = record.cellCenterYKpc - halfSize
  const top = record.cellCenterYKpc + halfSize

  return [
    [left, bottom, 0],
    [right, bottom, 0],
    [right, top, 0],
    [left, top, 0],
    [left, bottom, 0],
  ]
}

export function buildGaiaDensityLayer(
  records: readonly DensityVisualizationRecord[],
  gridLevel: number,
  options: DensitySelectionOptions = {},
): PolygonLayer<DensityVisualizationRecord> {
  const selectedRecords = selectDensityRecords(records, gridLevel, options)
  const opacityScale = createGaiaDensityOpacityScale(selectedRecords)

  return new PolygonLayer<DensityVisualizationRecord>({
    id: `gaia-density-${gridLevel}`,
    data: selectedRecords,
    coordinateSystem: 'cartesian',
    filled: true,
    stroked: false,
    extruded: false,
    pickable: true,
    getPolygon: densityCellPolygon,
    getFillColor: (record): Color => {
      const [red, green, blue] = gaiaDensityTierColors[record.distanceTier]
      const alpha = Math.round(opacityScale(record.sourceCount) * 255)

      return [red, green, blue, alpha]
    },
  })
}
