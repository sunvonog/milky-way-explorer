<script setup lang="ts">
import { computed } from 'vue'
import { format, scaleLinear, scaleSqrt } from 'd3'

import type { CartesianPosition, HostVisualizationRecord } from '@/data/hostVisualization'

interface Props {
  records: HostVisualizationRecord[]
}

type PositionedHost = HostVisualizationRecord & {
  heliocentricPc: CartesianPosition
}

const props = defineProps<Props>()

const width = 800
const height = 600

const margin = {
  top: 32,
  right: 24,
  bottom: 64,
  left: 72,
}

const plotWidth = width - margin.left - margin.right
const plotHeight = height - margin.top - margin.bottom

const positionedRecords = computed<PositionedHost[]>(() =>
  props.records.filter((record): record is PositionedHost => record.heliocentricPc !== null),
)

const plot = computed(() => {
  // Include the Sun so the origin always remains visible.
  const xValues = [0, ...positionedRecords.value.map((record) => record.heliocentricPc.x)]
  const yValues = [0, ...positionedRecords.value.map((record) => record.heliocentricPc.y)]

  const xMinimum = Math.min(...xValues)
  const xMaximum = Math.max(...xValues)
  const yMinimum = Math.min(...yValues)
  const yMaximum = Math.max(...yValues)

  const xSpan = xMaximum - xMinimum
  const ySpan = yMaximum - yMinimum

  /*
   * Select one physical-units-per-pixel value for both axes.
   * This prevents spatial shapes from being visually distorted.
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

  const largestPlanetCount = Math.max(
    1,
    ...positionedRecords.value.map((record) => record.planetCount),
  )

  const radiusScale = scaleSqrt().domain([1, largestPlanetCount]).range([3, 9]).clamp(true)

  return {
    xScale,
    yScale,
    radiusScale,
    xTicks: xScale.ticks(6),
    yTicks: yScale.ticks(6),
  }
})

const formatTick = format('~s')

function pointClass(record: PositionedHost): string {
  return record.distanceMethod === 'inverse_parallax'
    ? 'host-point host-point--inverse-parallax'
    : 'host-point host-point--gspphot'
}
</script>

<template>
  <figure class="host-scatter">
    <figcaption>
      <strong>Heliocentric exoplanet hosts</strong>
      <span> {{ positionedRecords.length }} of {{ records.length }} hosts positioned </span>
    </figcaption>

    <svg
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      aria-labelledby="host-scatter-title host-scatter-description"
    >
      <title id="host-scatter-title">Heliocentric exoplanet-host positions</title>
      <desc id="host-scatter-description">
        Top-down Cartesian view centred on the Sun. Point size represents the number of published
        planets.
      </desc>

      <rect
        class="plot-frame"
        :x="margin.left"
        :y="margin.top"
        :width="plotWidth"
        :height="plotHeight"
      />

      <g v-for="tick in plot.xTicks" :key="`x-${tick}`">
        <line
          class="grid-line"
          :x1="plot.xScale(tick)"
          :x2="plot.xScale(tick)"
          :y1="margin.top"
          :y2="height - margin.bottom"
        />
        <text
          class="tick-label"
          text-anchor="middle"
          :x="plot.xScale(tick)"
          :y="height - margin.bottom + 22"
        >
          {{ formatTick(tick) }}
        </text>
      </g>

      <g v-for="tick in plot.yTicks" :key="`y-${tick}`">
        <line
          class="grid-line"
          :x1="margin.left"
          :x2="width - margin.right"
          :y1="plot.yScale(tick)"
          :y2="plot.yScale(tick)"
        />
        <text
          class="tick-label"
          text-anchor="end"
          dominant-baseline="middle"
          :x="margin.left - 10"
          :y="plot.yScale(tick)"
        >
          {{ formatTick(tick) }}
        </text>
      </g>

      <line
        class="origin-axis"
        :x1="plot.xScale(0)"
        :x2="plot.xScale(0)"
        :y1="margin.top"
        :y2="height - margin.bottom"
      />
      <line
        class="origin-axis"
        :x1="margin.left"
        :x2="width - margin.right"
        :y1="plot.yScale(0)"
        :y2="plot.yScale(0)"
      />

      <circle
        v-for="record in positionedRecords"
        :key="record.hostId"
        data-host-point
        :data-host-id="record.hostId"
        :class="pointClass(record)"
        :cx="plot.xScale(record.heliocentricPc.x)"
        :cy="plot.yScale(record.heliocentricPc.y)"
        :r="plot.radiusScale(record.planetCount)"
      >
        <title>
          {{ record.hostName }}:
          {{ record.planetCount }}
          {{ record.planetCount === 1 ? 'planet' : 'planets' }}
        </title>
      </circle>

      <circle data-sun-origin class="sun-origin" :cx="plot.xScale(0)" :cy="plot.yScale(0)" r="5">
        <title>Sun — heliocentric origin</title>
      </circle>

      <text
        data-axis-title="x"
        class="axis-title"
        text-anchor="middle"
        :x="margin.left + plotWidth / 2"
        :y="height - 14"
      >
        Heliocentric x (pc)
      </text>

      <text
        data-axis-title="y"
        class="axis-title"
        text-anchor="middle"
        :transform="`
          translate(18 ${margin.top + plotHeight / 2})
          rotate(-90)
        `"
      >
        Heliocentric y (pc)
      </text>
    </svg>
  </figure>
</template>

<style scoped>
.host-scatter {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  color: #e8edf7;
}

figcaption {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem 1rem;
}

figcaption strong {
  font-size: 1.1rem;
}

figcaption span {
  color: #a8b3c7;
  font-size: 0.9rem;
}

svg {
  display: block;
  width: 100%;
  height: auto;
  background: #080c16;
}

.plot-frame {
  fill: #0c1322;
  stroke: #566176;
  stroke-width: 1;
}

.grid-line {
  stroke: #293246;
  stroke-width: 1;
}

.origin-axis {
  stroke: #65738d;
  stroke-width: 1.25;
}

.tick-label,
.axis-title {
  fill: #c9d2e3;
  font-size: 12px;
}

.axis-title {
  font-size: 13px;
  font-weight: 600;
}

.host-point {
  stroke: #f5f8ff;
  stroke-width: 0.6;
  opacity: 0.72;
}

.host-point--gspphot {
  fill: #69a7ff;
}

.host-point--inverse-parallax {
  fill: #ffb454;
}

.sun-origin {
  fill: #ffe36e;
  stroke: #fff8cc;
  stroke-width: 2;
}
</style>
