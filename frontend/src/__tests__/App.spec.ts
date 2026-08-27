import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, it, expect, vi } from 'vitest'

import App from '../App.vue'
import GaiaDensityPlot from '@/components/GaiaDensityPlot.vue'
import HostScatterPlot from '@/components/HostScatterPlot.vue'
import { loadDensityVisualization } from '@/data/densityVisualization'
import { loadHostVisualization } from '@/data/hostVisualization'

vi.mock('@/data/densityVisualization', () => ({
  loadDensityVisualization:
    vi.fn<typeof import('@/data/densityVisualization').loadDensityVisualization>(),
}))

vi.mock('@/data/hostVisualization', () => ({
  loadHostVisualization: vi.fn<typeof import('@/data/hostVisualization').loadHostVisualization>(),
}))

const loadDensityVisualizationMock = vi.mocked(loadDensityVisualization)
const loadHostVisualizationMock = vi.mocked(loadHostVisualization)

describe('App', () => {
  beforeEach(() => {
    loadDensityVisualizationMock.mockReset()
    loadHostVisualizationMock.mockReset()
  })

  it('shows the loading state while either dataset is pending', () => {
    loadHostVisualizationMock.mockReturnValue(new Promise(() => undefined))
    loadDensityVisualizationMock.mockResolvedValue([])

    const wrapper = mount(App)

    expect(wrapper.text()).toContain('Milky Way Explorer')
    expect(wrapper.text()).toContain('Loading Milky Way data...')
    expect(wrapper.findComponent(HostScatterPlot).exists()).toBe(false)
    expect(wrapper.findComponent(GaiaDensityPlot).exists()).toBe(false)
  })

  it('renders both plots after loading both datasets', async () => {
    loadHostVisualizationMock.mockResolvedValue([])
    loadDensityVisualizationMock.mockResolvedValue([])

    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.findComponent(HostScatterPlot).exists()).toBe(true)
    expect(wrapper.findComponent(GaiaDensityPlot).exists()).toBe(true)

    expect(loadHostVisualizationMock).toHaveBeenCalledWith(import.meta.env.VITE_DATA_BASE_URL)
    expect(loadDensityVisualizationMock).toHaveBeenCalledWith(import.meta.env.VITE_DATA_BASE_URL)
  })

  it('shows a host loading error', async () => {
    loadHostVisualizationMock.mockRejectedValue(new Error('host visualization unavailable'))
    loadDensityVisualizationMock.mockResolvedValue([])

    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('host visualization unavailable')
  })
  it('shows a density loading error', async () => {
    loadHostVisualizationMock.mockResolvedValue([])
    loadDensityVisualizationMock.mockRejectedValue(new Error('density visualization unavailable'))

    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('density visualization unavailable')
  })
})
