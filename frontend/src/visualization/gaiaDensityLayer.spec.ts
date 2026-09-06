import { describe, expect, it } from 'vitest'

import type { DensityVisualizationRecord } from '@/domain/density'
import type { PolygonLayer } from '@deck.gl/layers'

import { buildGaiaDensityPlotModel } from './gaiaDensityPlotModel'
import { buildGaiaDensityLayer } from './gaiaDensityLayer'

function densityCell(
  overrides: Partial<DensityVisualizationRecord> = {},
): DensityVisualizationRecord {
  return {
    gridLevel: 4,
    cellX: 0,
    cellY: 1,
    distanceTier: 'baseline',
    cellCenterXKpc: -1.5,
    cellCenterYKpc: -0.5,
    cellSizeKpc: 1,
    sourceCount: 10,
    weightedBrightness: 0.1,
    meanBpRp: 0.8,
    ...overrides,
  }
}

function fillColorFor(
  layer: PolygonLayer<DensityVisualizationRecord>,
  record: DensityVisualizationRecord,
): number[] {
  const accessor = layer.props.getFillColor

  const color =
    typeof accessor === 'function'
      ? accessor(record, {
          index: 0,
          data: [record],
          target: [],
        })
      : accessor

  return Array.from(color)
}

describe('buildGaiaDensityLayer', () => {
  it('represents a cell as a flat square in Galactocentric kiloparsecs', () => {
    const record = densityCell()
    const layer = buildGaiaDensityLayer([record], 4)

    expect(layer.props.coordinateSystem).toBe('cartesian')
    expect(layer.props.extruded).toBe(false)

    expect(
      layer.props.getPolygon(record, {
        index: 0,
        data: [record],
        target: [],
      }),
    ).toEqual([
      [-2, -1, 0],
      [-1, -1, 0],
      [-1, 0, 0],
      [-2, 0, 0],
      [-2, -1, 0],
    ])
  })

  it('selects only baseline cells at the requested grid level by default', () => {
    const baseline = densityCell()
    const exploratory = densityCell({
      distanceTier: 'exploratory',
    })
    const finerCell = densityCell({
      gridLevel: 8,
      cellY: 0,
      cellSizeKpc: 0.5,
      cellCenterXKpc: -1.75,
      cellCenterYKpc: -1.75,
    })

    const layer = buildGaiaDensityLayer([baseline, exploratory, finerCell], 4)

    expect(layer.props.data).toEqual([baseline])
  })

  it('preserves both tiers in the same cell when exploratory density is enabled', () => {
    const baseline = densityCell()
    const exploratory = densityCell({
      distanceTier: 'exploratory',
      sourceCount: 4,
    })

    const layer = buildGaiaDensityLayer([baseline, exploratory], 4, { includeExploratory: true })

    expect(layer.props.data).toEqual([baseline, exploratory])
  })

  it('accepts an empty dataset', () => {
    const layer = buildGaiaDensityLayer([], 4)

    expect(layer.props.data).toEqual([])
  })

  it('returns an empty layer when all available cells are excluded', () => {
    const layer = buildGaiaDensityLayer([densityCell({ distanceTier: 'exploratory' })], 4)

    expect(layer.props.data).toEqual([])
  })

  it('distinguishes quality tiers by colour while preserving equal-count opacity', () => {
    const baseline = densityCell({ sourceCount: 10 })
    const exploratory = densityCell({
      distanceTier: 'exploratory',
      sourceCount: 10,
    })

    const layer = buildGaiaDensityLayer([baseline, exploratory], 4, { includeExploratory: true })

    const baselineColor = fillColorFor(layer, baseline)
    const exploratoryColor = fillColorFor(layer, exploratory)

    expect(baselineColor).toHaveLength(4)
    expect(exploratoryColor).toHaveLength(4)
    expect(baselineColor.slice(0, 3)).not.toEqual(exploratoryColor.slice(0, 3))
    expect(baselineColor[3]).toBe(exploratoryColor[3])
  })

  it('matches the SVG source-count opacity scale', () => {
    const records = [
      densityCell({ sourceCount: 1 }),
      densityCell({
        cellX: 1,
        cellCenterXKpc: -0.5,
        sourceCount: 4,
      }),
      densityCell({
        cellX: 2,
        cellCenterXKpc: 0.5,
        sourceCount: 16,
      }),
    ]

    const layer = buildGaiaDensityLayer(records, 4)
    const svgModel = buildGaiaDensityPlotModel(records, 4)

    const actualAlpha = records.map((record) => fillColorFor(layer, record)[3])
    const expectedAlpha = svgModel.cells.map((cell) => Math.round(cell.opacity * 255))

    expect(actualAlpha).toEqual(expectedAlpha)
  })

  it('ignores excluded cells when normalizing intensity', () => {
    const baseline = densityCell({ sourceCount: 10 })
    const exploratory = densityCell({
      distanceTier: 'exploratory',
      sourceCount: 100_000,
    })
    const finerCell = densityCell({
      gridLevel: 8,
      cellSizeKpc: 0.5,
      cellY: 0,
      cellCenterXKpc: -1.75,
      cellCenterYKpc: -1.75,
      sourceCount: 100_000,
    })

    const baselineLayer = buildGaiaDensityLayer([baseline], 4)
    const mixedLayer = buildGaiaDensityLayer([baseline, exploratory, finerCell], 4)

    expect(fillColorFor(mixedLayer, baseline)[3]).toBe(fillColorFor(baselineLayer, baseline)[3])
  })
})
