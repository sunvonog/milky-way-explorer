<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { loadDensityVisualization } from './data/densityVisualization'
import { loadHostVisualization } from '@/data/hostVisualization'
import GaiaDensityPlot from './components/GaiaDensityPlot.vue'
import HostScatterPlot from '@/components/HostScatterPlot.vue'
import type { DensityVisualizationRecord } from './domain/density'
import type { HostVisualizationRecord } from './domain/host'

const hostRecords = ref<HostVisualizationRecord[]>([])
const densityRecords = ref<DensityVisualizationRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  try {
    const [hosts, density] = await Promise.all([
      loadHostVisualization(import.meta.env.VITE_DATA_BASE_URL),
      loadDensityVisualization(import.meta.env.VITE_DATA_BASE_URL),
    ])

    hostRecords.value = hosts
    densityRecords.value = density
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'failed to load Milky Way data'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <main class="mx-auto min-h-screen w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="mb-6 text-2xl font-semibold tracking-tight sm:text-4xl">Milky Way Explorer</h1>

    <p v-if="isLoading" class="text-sm text-slate-400">Loading Milky Way data...</p>

    <p
      v-else-if="errorMessage"
      class="rounded-lg border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-200"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <div v-else class="grid items-start gap-10 xl:grid-cols-2">
      <GaiaDensityPlot :records="densityRecords" />
      <HostScatterPlot :records="hostRecords" />
    </div>
  </main>
</template>
