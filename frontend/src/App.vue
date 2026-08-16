<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { loadHostVisualization, type HostVisualizationRecord } from '@/data/hostVisualization'
import HostScatterPlot from '@/components/HostScatterPlot.vue'

const records = ref<HostVisualizationRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  try {
    records.value = await loadHostVisualization(import.meta.env.VITE_DATA_BASE_URL)
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof Error ? error.message : 'failed to load host visualization'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <main class="mx-auto min-h-screen w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="mb-6 text-2xl font-semibold tracking-tight sm:text-4xl">Milky Way Explorer</h1>

    <p v-if="isLoading" class="text-sm text-slate-400">Loading exoplanet hosts...</p>

    <p
      v-else-if="errorMessage"
      class="rounded-lg border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-200"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <HostScatterPlot v-else :records="records" />
  </main>
</template>
