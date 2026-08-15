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
    <h1 class="mb-6 text-2xl fontfont-semibold tracking-tight sm:text-4xl">Milky Way Explorer</h1>

    <p v-if="isLoading" class="text-sm text-slate-400">Loading exoplanet hosts...</p>

    <p
      v-if="errorMessage"
      class="rounded-lg border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-200"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <HostScatterPlot v-else :records="records" />
  </main>
</template>

<style>
html {
  color-scheme: dark;
  background: #080c16;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background: #080c16;
  color: #e8edf7;
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
}

main {
  width: min(1100px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 2rem 0;
}

h1 {
  margin: 0 0 1.5rem;
  font-size: clamp(1.5rem, 4vw, 2.5rem);
}
</style>
