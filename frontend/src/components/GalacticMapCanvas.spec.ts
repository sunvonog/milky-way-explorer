import type { DeckProps, OrthographicView } from '@deck.gl/core'
import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import GalacticMapCanvas from './GalacticMapCanvas.vue'
import { fitGalacticMapView } from '@/visualization/galacticMapView'

type MapDeckProps = DeckProps<OrthographicView>

const renderer = vi.hoisted(() => ({
  create: vi.fn<(props: MapDeckProps) => void>(),
  setProps: vi.fn<(props: MapDeckProps) => void>(),
  finalize: vi.fn<() => void>(),
}))

vi.mock('@deck.gl/core', async (importOriginal) => {
  const original = await importOriginal<typeof import('@deck.gl/core')>()

  return {
    ...original,
    Deck: class {
      constructor(props: MapDeckProps) {
        renderer.create(props)
      }

      setProps = renderer.setProps
      finalize = renderer.finalize
    },
  }
})

enableAutoUnmount(afterEach)

function mountMap() {
  const wrapper = mount(GalacticMapCanvas, {
    props: {
      layers: [],
      extentKpc: 20,
    },
  })

  const options = renderer.create.mock.calls.at(-1)![0]

  return { wrapper, options }
}

describe('GalacticMapCanvas', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('connects the canvas and fits the camera to its dimensions', () => {
    const { wrapper, options } = mountMap()

    expect(options.canvas).toBe(wrapper.get('canvas').element)
    expect(options.views?.props.flipY).toBe(false)

    options.onResize?.({ width: 800, height: 600 })

    expect(renderer.setProps).toHaveBeenCalledWith({
      viewState: fitGalacticMapView({
        width: 800,
        height: 600,
        extentKpc: 20,
        paddingPx: 40,
      }),
    })
  })

  it('accepts camera interaction and allows resetting the view', async () => {
    const { wrapper, options } = mountMap()

    options.onResize?.({ width: 800, height: 600 })

    const movedView = {
      target: [3, -2, 0] as [number, number, number],
      zoom: 7,
    }

    options.onViewStateChange?.({
      viewId: 'galactic-map',
      viewState: movedView,
      interactionState: { isPanning: true },
    })

    expect(renderer.setProps).toHaveBeenLastCalledWith({
      viewState: movedView,
    })

    await wrapper.get('[data-reset-map]').trigger('click')

    expect(renderer.setProps).toHaveBeenCalledWith({
      viewState: fitGalacticMapView({
        width: 800,
        height: 600,
        extentKpc: 20,
        paddingPx: 40,
      }),
    })
  })

  it('updates layers without recreating the renderer or resetting the camera', async () => {
    const { wrapper } = mountMap()

    renderer.setProps.mockClear()

    await wrapper.setProps({ layers: [] })

    expect(renderer.create).toHaveBeenCalledTimes(1)
    expect(renderer.setProps).toHaveBeenCalledExactlyOnceWith({
      layers: [],
    })
  })

  it('waits for usable dimensions before fitting the camera', () => {
    const { options } = mountMap()

    options.onResize?.({ width: 0, height: 0 })
    expect(renderer.setProps).not.toHaveBeenCalled()

    options.onResize?.({ width: 600, height: 800 })

    expect(renderer.setProps).toHaveBeenLastCalledWith({
      viewState: fitGalacticMapView({
        width: 600,
        height: 800,
        extentKpc: 20,
        paddingPx: 40,
      }),
    })
  })

  it('refits when the physical grid extent changes', async () => {
    const { wrapper, options } = mountMap()

    options.onResize?.({ width: 800, height: 600 })
    await wrapper.setProps({ extentKpc: 40 })

    expect(renderer.setProps).toHaveBeenLastCalledWith({
      viewState: fitGalacticMapView({
        width: 800,
        height: 600,
        extentKpc: 40,
        paddingPx: 40,
      }),
    })
  })

  it('shows rendering errors', async () => {
    const { wrapper, options } = mountMap()

    options.onError?.(new Error('WebGL is unavailable'))
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[role="alert"]').text()).toContain('WebGL is unavailable')
  })

  it('shows initialization errors', async () => {
    renderer.create.mockImplementationOnce(() => {
      throw new Error('Could not initialize WebGL')
    })

    const wrapper = mount(GalacticMapCanvas, {
      props: { layers: [], extentKpc: 20 },
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.get('[role="alert"]').text()).toContain('Could not initialize WebGL')
  })

  it('releases rendering resources when unmounted', () => {
    const { wrapper } = mountMap()

    wrapper.unmount()

    expect(renderer.finalize).toHaveBeenCalledTimes(1)
  })
})
