import { format, scaleLinear, scaleSqrt } from 'd3'

import { coordinateFrames } from '@/domain/coordinateFrames'
import type { DensityVisualizationRecord } from '@/domain/density'

const width = 800
const height = 800

const margin = {
  top: 32,
  right: 24,
  bottom: 64,
  left: 72,
}

export const gaiaDensityPlotLayout = {
  width,
  height,
  margin,
  plotWidth: width - margin.left - margin.right,
  plotHeight: height - margin.top - margin.bottom,
}

interface ScreenPosition {
  x: number
  y: number
}

interface AxisTick {
  value: number
  label: string
  pixel: number
}

interface DensityCell {
  record: DensityVisualizationRecord
  x: number
  y: number
  width: number
  height: number
  opacity: number
}

export interface gaiaDensityPlotModel {
  cells: DensityCell[]
  gridLevel: number
  extentKpc: number
  sun: ScreenPosition
  galacticCentre: ScreenPosition
  xTicks: AxisTick[]
  yTicks: AxisTick[]
}

const formatTick = format('~s')

export function buildGaiaDensityPlotModel(
  records: readonly DensityVisualizationRecord[],
  gridLevel: number,
): gaiaDensityPlotModel {
  const selectedRecords = records.filter((record) => record.gridLevel === gridLevel)

  if (selectedRecords.length === 0) {
    throw new RangeError(`no density cells available for grid level ${gridLevel}`)
  }

  const cellSizeKpc = selectedRecords[0]!.cellSizeKpc

  if (selectedRecords.some((record) => record.cellSizeKpc !== cellSizeKpc)) {
    throw new TypeError(`grid level ${gridLevel} contains inconsistent cell sizes`)
  }

  /**
   * A grid with N cells of width s covers [-N*s/2, N*s/2].
   * Reconstructing the complete extent prevents sparse occupied cells from
   * changing the apparent physical scale of the Milky Way.
   */
  const extentKpc = (gridLevel * cellSizeKpc) / 2

  const xScale = scaleLinear()
    .domain([-extentKpc, extentKpc])
    .range([margin.left, width - margin.right])

  const yScale = scaleLinear()
    .domain([-extentKpc, extentKpc])
    .range([height - margin.bottom, margin.top])

  const largestSourceCount = Math.max(1, ...selectedRecords.map((record) => record.sourceCount))

  const opacityScale = scaleSqrt().domain([0, largestSourceCount]).range([0.15, 1]).clamp(true)

  function project(xKpc: number, yKpc: number): ScreenPosition {
    return {
      x: xScale(xKpc),
      y: yScale(yKpc),
    }
  }

  const galactocentricFrame = coordinateFrames.galactocentric

  return {
    cells: selectedRecords.map((record) => {
      const halfCellSize = record.cellSizeKpc / 2
      const left = xScale(record.cellCenterXKpc - halfCellSize)
      const right = xScale(record.cellCenterXKpc + halfCellSize)
      const top = yScale(record.cellCenterYKpc + halfCellSize)
      const bottom = yScale(record.cellCenterYKpc - halfCellSize)

      return {
        record,
        x: left,
        y: top,
        width: right - left,
        height: bottom - top,
        opacity: opacityScale(record.sourceCount),
      }
    }),
    gridLevel,
    extentKpc,
    sun: project(galactocentricFrame.sunPosition.x, galactocentricFrame.sunPosition.y),
    galacticCentre: project(
      galactocentricFrame.galacticCentrePosition.x,
      galactocentricFrame.galacticCentrePosition.y,
    ),
    xTicks: xScale.ticks(8).map((value) => ({
      value,
      label: formatTick(value),
      pixel: xScale(value),
    })),
    yTicks: yScale.ticks(8).map((value) => ({
      value,
      label: formatTick(value),
      pixel: yScale(value),
    })),
  }
}
