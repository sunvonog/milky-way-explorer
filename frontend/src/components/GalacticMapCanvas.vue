<script setup lang="ts">
import { Deck, type LayersList, type OrthographicView } from '@deck.gl/core'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { createGalacticMapView, fitGalacticMapView } from '@/visualization/galacticMapView'

interface Props {
  layers: LayersList
  extentKpc: number
}

const props = defineProps<Props>()

const canvas = ref<HTMLCanvasElement | null>(null)
const errorMessage = ref<string | null>(null)

const paddingPx = 40

let deck: Deck<OrthographicView> | null = null
let size = { width: 0, height: 0 }

function resetView(): void {
  if (!deck || Math.min(size.width, size.height) <= 2 * paddingPx) {
    return
  }

  deck.setProps({
    viewState: fitGalacticMapView({
      ...size,
      extentKpc: props.extentKpc,
      paddingPx,
    }),
  })
}

function showError(error: unknown): void {
  errorMessage.value = error instanceof Error ? error.message : 'WebGL rendering failed'
}

onMounted(() => {
  if (!canvas.value) {
    return
  }

  try {
    deck = new Deck<OrthographicView>({
      canvas: canvas.value,
      width: '100%',
      height: '100%',
      views: createGalacticMapView(),
      layers: props.layers,
      viewState: {
        target: [0, 0, 0],
        zoom: 0,
      },
      onResize: (dimensions) => {
        size = dimensions
        resetView()
      },
      onViewStateChange: ({ viewState }) => {
        deck?.setProps({ viewState })
      },
      onError: showError,
    })
  } catch (error: unknown) {
    showError(error)
  }
})

watch(
  () => props.layers,
  (layers) => {
    deck?.setProps({ layers })
  },
)

watch(() => props.extentKpc, resetView)

onBeforeUnmount(() => {
  deck?.finalize()
  deck = null
})
</script>

<template>
  <div class="grid gap-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-400">
        Drag to pan. Scroll or pinch to zoom. Galactocentric x-y plane, in kpc.
      </p>

      <button
        data-reset-map
        type="button"
        class="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
        @click="resetView"
      >
        Reset view
      </button>
    </div>

    <div class="relative aspect-square overflow-hidden rounded-xl bg-slate-950">
      <canvas
        ref="canvas"
        class="absolute inset-0 block h-full w-full touch-none"
        tabindex="0"
        role="img"
        aria-label="Interactive Galactocentric density map. Drag to pan and scroll to zoom."
      >
        Interactive Galactic map. An SVG comparison is available below
      </canvas>

      <p
        v-if="errorMessage"
        role="alert"
        class="absolute inset-x-4 top-4 rounded-lg bg-red-950 p-4 text-sm text-red-200"
      >
        {{ errorMessage }}. You can still use the SVG comparison below.
      </p>
    </div>
  </div>
</template>
