import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, it, expect, vi } from 'vitest'

import App from '../App.vue'
import HostScatterPlot from '@/components/HostScatterPlot.vue'
import { loadHostVisualization } from '@/data/hostVisualization'

vi.mock('@/data/hostVisualization', () => ({
  loadHostVisualization: vi.fn<typeof import('@/data/hostVisualization').loadHostVisualization>(),
}))

const loadHostVisualizationMock = vi.mocked(loadHostVisualization)

describe('App', () => {
  beforeEach(() => {
    loadHostVisualizationMock.mockReset()
  })

  it('shows the loading state while data is pending', () => {
    loadHostVisualizationMock.mockReturnValue(new Promise(() => undefined))

    const wrapper = mount(App)

    expect(wrapper.text()).toContain('Milky Way Explorer')
    expect(wrapper.text()).toContain('Loading exoplanet hosts...')
  })

  it('renders the scatter plot after loading', async () => {
    loadHostVisualizationMock.mockResolvedValue([])

    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.findComponent(HostScatterPlot).exists()).toBe(true)
  })

  it('shows a useful loading error', async () => {
    loadHostVisualizationMock.mockRejectedValue(new Error('visualization unavailable'))

    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('visualization unavailable')
  })
})
