<script setup lang="ts">
import { computed, ref } from 'vue'

import type { DensityVisualizationRecord } from '@/domain/density'
import {
  buildGaiaDensityPlotModel,
  gaiaDensityPlotLayout,
  selectHighestGaiaDensityGridLevel,
} from '@/visualization/gaiaDensityPlotModel'

interface Props {
  records: DensityVisualizationRecord[]
}

const props = defineProps<Props>()

const includeExploratory = ref(false)

const selectedGridLevel = computed(() => selectHighestGaiaDensityGridLevel(props.records))

const plot = computed(() => {
  if (selectedGridLevel.value === null) {
    return null
  }

  return buildGaiaDensityPlotModel(props.records, selectedGridLevel.value, {
    includeExploratory: includeExploratory.value,
  })
})

const occupiedCellLabel = computed(() => {
  if (!plot.value) {
    return ''
  }

  const count = plot.value.occupiedCellCount
  return `${count} occupied ${count === 1 ? 'cell' : 'cells'}`
})

const { width, height, margin, plotWidth, plotHeight } = gaiaDensityPlotLayout
</script>

<template>
  <p
    v-if="plot === null"
    class="rounded-xl border border-slate-800 bg-slate-950 p-6 text-slate-400"
  >
    No Gaia density data is available
  </p>

  <figure v-else class="m-0 grid gap-3 text-slate-100">
    <figcaption class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
      <strong class="text-lg font-semibold">Gaia source density</strong>

      <span class="text-sm text-slate-400">
        {{ plot.sourceCount }} Gaia sources in {{ occupiedCellLabel }} - {{ plot.gridLevel }} x
        {{ plot.gridLevel }} grid
      </span>
    </figcaption>

    <div class="space-y-1">
      <label
        for="include-exploratory-density"
        class="flex items-center gap-2 text-sm text-slate-200"
      >
        <input
          id="include-exploratory-density"
          v-model="includeExploratory"
          data-density-quality-toggle
          type="checkbox"
          aria-describedby="gaia-density-quality-description"
          class="size-4 accent-amber-400"
        />

        Include exploratory distances
      </label>

      <p id="gaia-density-quality-description" class="max-w-xl text-xs text-slate-400">
        Baseline uses GSP-Phot estimates or inverse-parallax S/N >= 5. Exploratory adds
        inverse-parallax S/N from 2 to below 5; these positions are less stable.
      </p>
    </div>

    <svg
      class="block h-auto w-full rounded-xl bg-slate-950"
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      aria-labelledby="gaia-density-title gaia-density-description"
    >
      <title id="gaia-density-title">Galactocentric Gaia source-density grid</title>

      <desc id="gaia-density-description">
        Top-down view of Gaia sources in the Galactic plane. Cell opacity represents source count
        using a square-root scale.
      </desc>

      <rect
        class="fill-slate-900 stroke-slate-500 stroke-1"
        :x="margin.left"
        :y="margin.top"
        :width="plotWidth"
        :height="plotHeight"
      />

      <rect
        v-for="cell in plot.cells"
        :key="`${plot.gridLevel}-${cell.record.cellX}-${cell.record.cellY}-${cell.record.distanceTier}`"
        data-density-cell
        :data-cell-x="cell.record.cellX"
        :data-cell-y="cell.record.cellY"
        :class="cell.record.distanceTier === 'baseline' ? 'fill-cyan-400' : 'fill-amber-400'"
        :x="cell.x"
        :y="cell.y"
        :width="cell.width"
        :height="cell.height"
        :fill-opacity="cell.opacity"
        :data-distance-tier="cell.record.distanceTier"
      >
        <title>
          {{ cell.record.sourceCount }} Gaia sources - {{ cell.record.distanceTier }} distance tier
        </title>
      </rect>

      <g v-for="tick in plot.xTicks" :key="`x-${tick.value}`">
        <line
          data-x-grid-line
          class="stroke-slate-700 stroke-1"
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
          class="stroke-slate-700 stroke-1"
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

      <circle
        data-sun-reference
        class="fill-yellow-300 stroke-yellow-100 stroke-2"
        :cx="plot.sun.x"
        :cy="plot.sun.y"
        r="5"
      >
        <title>Sun - reference point</title>
      </circle>

      <circle
        data-galactic-centre-reference
        data-galactic-centre-origin
        class="fill-fuchsia-300 stroke-fuchsia-100 stroke-2"
        :cx="plot.galacticCentre.x"
        :cy="plot.galacticCentre.y"
        r="8"
      >
        <title>Galactic centre - Galactocentric origin</title>
      </circle>

      <text
        data-axis-title="x"
        class="fill-slate-300 text-sm font-semibold"
        text-anchor="middle"
        :x="margin.left + plotWidth / 2"
        :y="height - 14"
      >
        Galactocentric x (kpc)
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
        Galactocentric y (kpc)
      </text>
    </svg>
  </figure>
</template>
