import { describe, expect, it } from 'vitest'

import type { DensityVisualizationRecord } from '@/domain/density'
import {
  buildGaiaDensityPlotModel,
  gaiaDensityPlotLayout,
  selectHighestGaiaDensityGridLevel,
} from './gaiaDensityPlotModel'

function densityCell(
  overrides: Partial<DensityVisualizationRecord> = {},
): DensityVisualizationRecord {
  return {
    gridLevel: 4,
    cellX: 0,
    cellY: 0,
    cellCenterXKpc: -1.5,
    cellCenterYKpc: -1.5,
    cellSizeKpc: 1,
    sourceCount: 1,
    weightedBrightness: 0.1,
    meanBpRp: 0.8,
    ...overrides,
  }
}

describe('buildGaiaDensityPlotModel', () => {
  it('projects cells using the complete physical grid extent', () => {
    const model = buildGaiaDensityPlotModel([densityCell()], 4)
    const cell = model.cells[0]!

    const { margin, plotWidth, plotHeight } = gaiaDensityPlotLayout

    expect(cell.x).toBeCloseTo(margin.left)
    expect(cell.y).toBeCloseTo(margin.top + (plotHeight * 3) / 4)
    expect(cell.width).toBeCloseTo(plotWidth / 4)
    expect(cell.height).toBeCloseTo(plotHeight / 4)
  })

  it('preserves equal physical scale on both axes', () => {
    const model = buildGaiaDensityPlotModel([densityCell()], 4)
    const cell = model.cells[0]!

    expect(cell.width).toBeCloseTo(cell.height)
  })

  it('selects only cells from the requested grid level', () => {
    const records = [
      densityCell({ gridLevel: 4 }),
      densityCell({
        gridLevel: 8,
        cellSizeKpc: 0.5,
        cellCenterXKpc: -1.75,
        cellCenterYKpc: -1.75,
      }),
    ]

    const model = buildGaiaDensityPlotModel(records, 4)

    expect(model.cells.map(({ record }) => record.gridLevel)).toEqual([4])
  })

  it('gives denser cells greater visual intensity', () => {
    const model = buildGaiaDensityPlotModel(
      [
        densityCell({ cellX: 0, sourceCount: 1 }),
        densityCell({
          cellX: 1,
          cellCenterXKpc: -0.5,
          sourceCount: 16,
        }),
      ],
      4,
    )

    expect(model.cells[1]!.opacity).toBeGreaterThan(model.cells[0]!.opacity)
  })

  it('places the Galactic centre at the plot centre', () => {
    const model = buildGaiaDensityPlotModel([densityCell()], 4)
    const { margin, plotWidth, plotHeight } = gaiaDensityPlotLayout

    expect(model.galacticCentre.x).toBeCloseTo(margin.left + plotWidth / 2)
    expect(model.galacticCentre.y).toBeCloseTo(margin.top + plotHeight / 2)
  })

  it('selects the highest available grid level', () => {
    expect(
      selectHighestGaiaDensityGridLevel([
        densityCell({ gridLevel: 4 }),
        densityCell({ gridLevel: 16 }),
        densityCell({ gridLevel: 8 }),
      ]),
    ).toBe(16)

    expect(selectHighestGaiaDensityGridLevel([])).toBeNull()
  })

  it('aggregates source counts for the selected grid level', () => {
    const model = buildGaiaDensityPlotModel(
      [
        densityCell({ sourceCount: 1 }),
        densityCell({
          cellX: 1,
          cellCenterXKpc: -0.5,
          sourceCount: 16,
        }),
      ],
      4,
    )

    expect(model.sourceCount).toBe(17)
  })
})
