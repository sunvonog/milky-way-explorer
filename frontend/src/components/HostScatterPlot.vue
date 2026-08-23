<script setup lang="ts">
import { computed, ref } from 'vue'

import type { HostVisualizationRecord } from '@/domain/host'
import {
  buildHostScatterPlotModel,
  hostScatterPlotLayout,
} from '@/visualization/hostScatterPlotModel'

import {
  coordinateFrameIds,
  coordinateFrames,
  type CoordinateFrameId,
} from '@/domain/coordinateFrames'

interface Props {
  records: HostVisualizationRecord[]
}

const props = defineProps<Props>()

const selectedFrame = ref<CoordinateFrameId>('heliocentric')

const selectedFramePresentation = computed(() => coordinateFrames[selectedFrame.value])

const { width, height, margin, plotWidth, plotHeight } = hostScatterPlotLayout

const plot = computed(() => buildHostScatterPlotModel(props.records, selectedFrame.value))

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
          {{ plot.hostPoints.length }} of {{ records.length }} hosts positioned
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

      <g v-for="tick in plot.xTicks" :key="`x-${tick.value}`">
        <line
          data-x-grid-line
          class="stroke-slate-800 stroke-1"
          :x1="tick.pixel"
          :x2="tick.pixel"
          :y1="margin.top"
          :y2="height - margin.bottom"
        />
        <text
          class="fill-slate-300 text-xs"
          text-anchor="middle"
          :x="tick.pixel"
          :y="height - margin.bottom + 22"
        >
          {{ tick.label }}
        </text>
      </g>

      <g v-for="tick in plot.yTicks" :key="`y-${tick.value}`">
        <line
          data-y-grid-line
          class="stroke-slate-800 stroke-1"
          :x1="margin.left"
          :x2="width - margin.right"
          :y1="tick.pixel"
          :y2="tick.pixel"
        />
        <text
          class="fill-slate-300 text-xs"
          text-anchor="end"
          dominant-baseline="middle"
          :x="margin.left - 10"
          :y="tick.pixel"
        >
          {{ tick.label }}
        </text>
      </g>

      <line
        class="stroke-slate-500 stroke-[1.25]"
        :x1="plot.axisOrigin.x"
        :x2="plot.axisOrigin.x"
        :y1="margin.top"
        :y2="height - margin.bottom"
      />
      <line
        class="stroke-slate-500 stroke-[1.25]"
        :x1="margin.left"
        :x2="width - margin.right"
        :y1="plot.axisOrigin.y"
        :y2="plot.axisOrigin.y"
      />

      <circle
        v-for="hostPoint in plot.hostPoints"
        :key="hostPoint.record.hostId"
        data-host-point
        :data-host-id="hostPoint.record.hostId"
        :class="pointClass(hostPoint.record)"
        :cx="hostPoint.x"
        :cy="hostPoint.y"
        :r="hostPoint.radius"
      >
        <title>
          {{ hostPoint.record.hostName }}:
          {{ hostPoint.record.planetCount }}
          {{ hostPoint.record.planetCount === 1 ? 'planet' : 'planets' }}
        </title>
      </circle>

      <circle
        data-sun-reference
        :data-sun-origin="selectedFrame === 'heliocentric' ? '' : undefined"
        class="fill-yellow-300 stroke-yellow-100 stroke-2"
        :cx="plot.sun.x"
        :cy="plot.sun.y"
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
        :cx="plot.galacticCentre.x"
        :cy="plot.galacticCentre.y"
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
