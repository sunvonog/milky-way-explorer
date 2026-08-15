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

const hostPointClass = 'stroke-slate-50 opacity-75 [stroke-width:0.6]'

function pointClass(record: PositionedHost): string {
  const distanceClass =
    record.distanceMethod === 'inverse_parallax' ? 'fill-amber-400' : 'fill-blue-400'

  return `${hostPointClass} ${distanceClass}`
}
</script>

<template>
  <figure class="m-0 grid gap-3 text-slate-100">
    <figcaption class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
      <strong class="text-lg font-semibold">Heliocentric exoplanet hosts</strong>
      <span class="text-sm text-slate-400">
        {{ positionedRecords.length }} of {{ records.length }} hosts positioned
      </span>
    </figcaption>

    <svg
      class="block h-auto w-full rounded-xl bg-slate-950"
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
        class="fill-slate-900 stroke-slate-500 stroke-1"
        :x="margin.left"
        :y="margin.top"
        :width="plotWidth"
        :height="plotHeight"
      />

      <g v-for="tick in plot.xTicks" :key="`x-${tick}`">
        <line
          class="stroke-slate-800 stroke-1"
          :x1="plot.xScale(tick)"
          :x2="plot.xScale(tick)"
          :y1="margin.top"
          :y2="height - margin.bottom"
        />
        <text
          class="fill-slate-300 text-xs"
          text-anchor="middle"
          :x="plot.xScale(tick)"
          :y="height - margin.bottom + 22"
        >
          {{ formatTick(tick) }}
        </text>
      </g>

      <g v-for="tick in plot.yTicks" :key="`y-${tick}`">
        <line
          class="stroke-slate-800 stroke-1"
          :x1="margin.left"
          :x2="width - margin.right"
          :y1="plot.yScale(tick)"
          :y2="plot.yScale(tick)"
        />
        <text
          class="fill-slate-300 text-xs"
          text-anchor="end"
          dominant-baseline="middle"
          :x="margin.left - 10"
          :y="plot.yScale(tick)"
        >
          {{ formatTick(tick) }}
        </text>
      </g>

      <line
        class="stroke-slate-500 stroke-[1.25]"
        :x1="plot.xScale(0)"
        :x2="plot.xScale(0)"
        :y1="margin.top"
        :y2="height - margin.bottom"
      />
      <line
        class="stroke-slate-500 stroke-[1.25]"
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

      <circle
        data-sun-origin
        class="fill-yellow-300 stroke-yellow-100 stroke2"
        :cx="plot.xScale(0)"
        :cy="plot.yScale(0)"
        r="5"
      >
        <title>Sun — heliocentric origin</title>
      </circle>

      <text
        data-axis-title="x"
        class="fill-slate-300 text-sm font-semibold"
        text-anchor="middle"
        :x="margin.left + plotWidth / 2"
        :y="height - 14"
      >
        Heliocentric x (pc)
      </text>

      <text
        data-axis-title="y"
        class="fill-slate-300 text-sm font-semibold"
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
