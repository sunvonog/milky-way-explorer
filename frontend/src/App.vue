<script setup lang="ts">
import { onMounted, ref } from 'vue'

import HostScatterPlot from '@/components/HostScatterPlot.vue'
import { loadHostVisualization, type HostVisualizationRecord } from '@/data/hostVisualization'

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
  <main>
    <h1>Milky Way Explorer</h1>

    <p v-if="isLoading">Loading exoplanet hosts...</p>

    <p v-else-if="errorMessage" role="alert">
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
