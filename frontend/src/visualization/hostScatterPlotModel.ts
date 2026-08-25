import { format, scaleLinear, scaleSqrt } from 'd3'

import { coordinateFrames, type CoordinateFrameId } from '@/domain/coordinateFrames'
import type { CartesianPosition } from '@/domain/coordinates'
import type { HostVisualizationRecord } from '@/domain/host'

const width = 800
const height = 600

const margin = {
  top: 32,
  right: 24,
  bottom: 64,
  left: 72,
}

export const hostScatterPlotLayout = {
  width,
  height,
  margin,
  plotWidth: width - margin.left - margin.right,
  plotHeight: height - margin.top - margin.bottom,
}

interface PositionedHost {
  record: HostVisualizationRecord
  position: CartesianPosition
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

interface HostPoint extends ScreenPosition {
  record: HostVisualizationRecord
  position: CartesianPosition
  radius: number
}

export interface HostScatterPlotModel {
  hostPoints: HostPoint[]
  sun: ScreenPosition
  galacticCentre: ScreenPosition
  axisOrigin: ScreenPosition
  xTicks: AxisTick[]
  yTicks: AxisTick[]
}

const formatTick = format('~s')

export function buildHostScatterPlotModel(
  records: readonly HostVisualizationRecord[],
  frameId: CoordinateFrameId,
): HostScatterPlotModel {
  const frame = coordinateFrames[frameId]
  const { plotWidth, plotHeight } = hostScatterPlotLayout

  const positionedHosts = records.reduce<PositionedHost[]>((result, record) => {
    const position = record[frame.positionField]

    if (position !== null) {
      result.push({ record, position })
    }

    return result
  }, [])

  // Both reference points participate in the domain so they remain visible.
  const xValues = [
    frame.sunPosition.x,
    frame.galacticCentrePosition.x,
    ...positionedHosts.map(({ position }) => position.x),
  ]
  const yValues = [
    frame.sunPosition.y,
    frame.galacticCentrePosition.y,
    ...positionedHosts.map(({ position }) => position.y),
  ]

  const xMinimum = Math.min(...xValues)
  const xMaximum = Math.max(...xValues)
  const yMinimum = Math.min(...yValues)
  const yMaximum = Math.max(...yValues)

  const xSpan = xMaximum - xMinimum
  const ySpan = yMaximum - yMinimum

  /**
   * One physical-units-per-pixel value is used for both axes so spatial
   * relationships are not visually distorted.
   */
  const unitsPerPixel =
    Math.max(xSpan / plotWidth, ySpan / plotHeight, 1 / Math.min(plotWidth, plotHeight)) * 1.08

  const xCentre = (xMinimum + xMaximum) / 2
  const yCentre = (yMinimum + yMaximum) / 2

  const xHalfSpan = (unitsPerPixel * plotWidth) / 2
  const yHalfSpan = (unitsPerPixel * plotHeight) / 2

  const xScale = scaleLinear()
    .domain([xCentre - xHalfSpan, xCentre + xHalfSpan])
    .range([margin.left, width - margin.right])

  const yScale = scaleLinear()
    .domain([yCentre - yHalfSpan, yCentre + yHalfSpan])
    .range([height - margin.bottom, margin.top])

  const largestPlanetCount = Math.max(1, ...positionedHosts.map(({ record }) => record.planetCount))

  const radiusScale = scaleSqrt().domain([1, largestPlanetCount]).range([3, 9]).clamp(true)

  function project(position: CartesianPosition): ScreenPosition {
    return {
      x: xScale(position.x),
      y: yScale(position.y),
    }
  }

  return {
    hostPoints: positionedHosts.map(({ record, position }) => ({
      record,
      position,
      ...project(position),
      radius: radiusScale(record.planetCount),
    })),
    sun: project(frame.sunPosition),
    galacticCentre: project(frame.galacticCentrePosition),
    axisOrigin: {
      x: xScale(0),
      y: yScale(0),
    },
    xTicks: xScale.ticks(6).map((value) => ({
      value,
      label: formatTick(value),
      pixel: xScale(value),
    })),
    yTicks: yScale.ticks(6).map((value) => ({
      value,
      label: formatTick(value),
      pixel: yScale(value),
    })),
  }
}
