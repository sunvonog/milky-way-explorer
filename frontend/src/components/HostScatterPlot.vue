<script setup lang="ts">
import { computed, ref } from 'vue'
import { format, scaleLinear, scaleSqrt } from 'd3'

import type { CartesianPosition } from '@/domain/coordinates'
import type { HostVisualizationRecord } from '@/domain/host'

import {
  coordinateFrameIds,
  coordinateFrames,
  type coordinateFrameId,
} from '@/domain/coordinateFrames'

interface Props {
  records: HostVisualizationRecord[]
}

type PositionedHost = {
  record: HostVisualizationRecord
  position: CartesianPosition
}

const props = defineProps<Props>()

const selectedFrame = ref<coordinateFrameId>('heliocentric')

const selectedFramePresentation = computed(() => coordinateFrames[selectedFrame.value])

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

const positionedRecords = computed<PositionedHost[]>(() => {
  const positionField = selectedFramePresentation.value.positionField

  return props.records.reduce<PositionedHost[]>((result, record) => {
    const position = record[positionField]

    if (position !== null) {
      result.push({ record, position })
    }

    return result
  }, [])
})

const plot = computed(() => {
  const { sunPosition, galacticCentrePosition } = selectedFramePresentation.value
  // Include both reference points so they remain visible
  const xValues = [
    sunPosition.x,
    galacticCentrePosition.x,
    ...positionedRecords.value.map(({ position }) => position.x),
  ]
  const yValues = [
    sunPosition.y,
    galacticCentrePosition.y,
    ...positionedRecords.value.map(({ position }) => position.y),
  ]

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
    ...positionedRecords.value.map(({ record }) => record.planetCount),
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

function pointClass(record: HostVisualizationRecord): string {
  const distanceClass =
    record.distanceMethod === 'inverse_parallax' ? 'fill-amber-400' : 'fill-blue-400'

  return `${hostPointClass} ${distanceClass}`
}
</script>

<template>
  <figure class="m-0 grid gap-3 text-slate-100">
    <figcaption class="grid gap-3">
      <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <strong class="text-lg font-semibold"
          >{{ selectedFramePresentation.label }} exoplanet hosts</strong
        >

        <span class="text-sm text-slate-400">
          {{ positionedRecords.length }} of {{ records.length }} hosts positioned
        </span>
      </div>

      <div
        class="flex w-fit rounded-lg border border-slate-700 bg-slate-900 p-1"
        role="group"
        aria-label="Coordinate frame"
      >
        <button
          v-for="frameId in coordinateFrameIds"
          :key="frameId"
          type="button"
          :data-coordinate-frame="frameId"
          :aria-pressed="selectedFrame === frameId"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition"
          :class="
            selectedFrame === frameId
              ? 'bg-slate-100 text-slate-950'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          "
          @click="selectedFrame = frameId"
        >
          {{ coordinateFrames[frameId].label }}
        </button>
      </div>
    </figcaption>

    <svg
      class="block h-auto w-full rounded-xl bg-slate-950"
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      aria-labelledby="host-scatter-title host-scatter-description"
    >
      <title id="host-scatter-title">
        {{ selectedFramePresentation.label }} exoplanet-host positions
      </title>
      <desc id="host-scatter-description">
        {{ selectedFramePresentation.description }}
        Point size represents the number of published planets.
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
        v-for="positionedHost in positionedRecords"
        :key="positionedHost.record.hostId"
        data-host-point
        :data-host-id="positionedHost.record.hostId"
        :class="pointClass(positionedHost.record)"
        :cx="plot.xScale(positionedHost.position.x)"
        :cy="plot.yScale(positionedHost.position.y)"
        :r="plot.radiusScale(positionedHost.record.planetCount)"
      >
        <title>
          {{ positionedHost.record.hostName }}:
          {{ positionedHost.record.planetCount }}
          {{ positionedHost.record.planetCount === 1 ? 'planet' : 'planets' }}
        </title>
      </circle>

      <circle
        data-sun-reference
        :data-sun-origin="selectedFrame === 'heliocentric' ? '' : undefined"
        class="fill-yellow-300 stroke-yellow-100 stroke-2"
        :cx="plot.xScale(selectedFramePresentation.sunPosition.x)"
        :cy="plot.yScale(selectedFramePresentation.sunPosition.y)"
        r="5"
      >
        <title>
          {{
            selectedFrame === 'heliocentric' ? 'Sun — heliocentric origin' : 'Sun — reference point'
          }}
        </title>
      </circle>

      <circle
        data-galactic-centre-reference
        :data-galactic-centre-origin="selectedFrame === 'galactocentric' ? '' : undefined"
        class="fill-fuchsia-300 stroke-fuchsia-100 stroke-2"
        :cx="plot.xScale(selectedFramePresentation.galacticCentrePosition.x)"
        :cy="plot.yScale(selectedFramePresentation.galacticCentrePosition.y)"
        r="5"
      >
        <title>
          {{
            selectedFrame === 'galactocentric'
              ? 'Galactic centre — Galactocentric origin'
              : 'Galactic centre — reference point'
          }}
        </title>
      </circle>

      <text
        data-axis-title="x"
        class="fill-slate-300 text-sm font-semibold"
        text-anchor="middle"
        :x="margin.left + plotWidth / 2"
        :y="height - 14"
      >
        {{ selectedFramePresentation.label }} x ({{ selectedFramePresentation.unit }})
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
        {{ selectedFramePresentation.label }} y ({{ selectedFramePresentation.unit }})
      </text>
    </svg>
  </figure>
</template>
