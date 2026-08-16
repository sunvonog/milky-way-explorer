import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { HostVisualizationRecord } from '@/data/hostVisualization'
import HostScatterPlot from './HostScatterPlot.vue'

function host(overrides: Partial<HostVisualizationRecord>): HostVisualizationRecord {
  return {
    hostId: 'nea:host:default',
    hostName: 'Default',
    gaiaSourceId: '101',
    planetCount: 1,
    archivePlanetCount: 1,
    planetCountMatchesArchive: true,
    isCircumbinary: false,
    positionStatus: 'available',
    distancePc: 10,
    distanceMethod: 'gaia_gspphot',
    distanceQuality: 'positive_gspphot_estimate',
    heliocentricPc: { x: 10, y: 0, z: 0 },
    galactocentricKpc: { x: -8.112, y: 0, z: 0.0208 },
    photGMeanMagnitude: 7.2,
    bpRpColor: 0.8,
    ...overrides,
  }
}

const records: HostVisualizationRecord[] = [
  host({
    hostId: 'nea:host:alpha',
    hostName: 'Alpha',
    planetCount: 1,
    heliocentricPc: { x: 10, y: 0, z: 0 },
  }),
  host({
    hostId: 'nea:host:beta',
    hostName: 'Beta',
    gaiaSourceId: null,
    positionStatus: 'no_exact_gaia_source',
    distancePc: null,
    distanceMethod: null,
    distanceQuality: null,
    heliocentricPc: null,
    galactocentricKpc: null,
    photGMeanMagnitude: null,
    bpRpColor: null,
  }),
  host({
    hostId: 'nea:host:gamma',
    hostName: 'Gamma',
    planetCount: 4,
    distanceMethod: 'inverse_parallax',
    distanceQuality: 'snr_ge_5_ruwe_acceptable',
    heliocentricPc: { x: 0, y: 10, z: 0 },
  }),
]

describe('HostScatterPlot', () => {
  it('renders only hosts with heliocentric positions', () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const points = wrapper.findAll('[data-host-point]')

    expect(points).toHaveLength(2)
    expect(points.map((point) => point.attributes('data-host-id'))).toEqual([
      'nea:host:alpha',
      'nea:host:gamma',
    ])

    expect(wrapper.text()).toContain('2 of 3 hosts positioned')
  })

  it('marks the Sun and labels both axes in parsecs', () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    expect(wrapper.find('[data-sun-origin]').exists()).toBe(true)
    expect(wrapper.get('[data-axis-title="x"]').text()).toBe('Heliocentric x (pc)')
    expect(wrapper.get('[data-axis-title="y"]').text()).toBe('Heliocentric y (pc)')
  })

  it('uses an equal physical scale for both coordinate axes', () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const sun = wrapper.get('[data-sun-origin]')
    const alpha = wrapper.get('[data-host-id="nea:host:alpha"]')
    const gamma = wrapper.get('[data-host-id="nea:host:gamma"]')

    const sunX = Number(sun.attributes('cx'))
    const sunY = Number(sun.attributes('cy'))

    const alphaDistance = Math.abs(Number(alpha.attributes('cx')) - sunX)
    const gammaDistance = Math.abs(Number(gamma.attributes('cy')) - sunY)

    expect(alphaDistance).toBeCloseTo(gammaDistance, 8)
  })

  it('uses planet count for point size', () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const alphaRadius = Number(wrapper.get('[data-host-id="nea:host:alpha"]').attributes('r'))
    const gammaRadius = Number(wrapper.get('[data-host-id="nea:host:gamma"]').attributes('r'))

    expect(gammaRadius).toBeGreaterThan(alphaRadius)
  })

  it('switches between heliocentric and galactocentric frames', async () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const heliocentricButton = wrapper.get('[data-coordinate-frame="heliocentric"]')
    const galactocentricButton = wrapper.get('[data-coordinate-frame="galactocentric"]')

    expect(heliocentricButton.attributes('aria-pressed')).toBe('true')
    expect(galactocentricButton.attributes('aria-pressed')).toBe('false')
    expect(wrapper.find('[data-sun-origin]').exists()).toBe(true)
    expect(wrapper.find('[data-galactic-centre-origin]').exists()).toBe(false)

    await galactocentricButton.trigger('click')

    expect(heliocentricButton.attributes('aria-pressed')).toBe('false')
    expect(galactocentricButton.attributes('aria-pressed')).toBe('true')

    expect(wrapper.text()).toContain('Galactocentric exoplanet hosts')
    expect(wrapper.get('[data-axis-title="x"]').text()).toBe('Galactocentric x (kpc)')
    expect(wrapper.get('[data-axis-title="y"]').text()).toBe('Galactocentric y (kpc)')

    expect(wrapper.find('[data-sun-origin]').exists()).toBe(false)
    expect(wrapper.find('[data-galactic-centre-origin]').exists()).toBe(true)
  })

  it('plots positions from the selected coordinate frame', async () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const heliocentricOriginX = Number(wrapper.get('[data-sun-origin]').attributes('cx'))
    const heliocentricAlphaX = Number(
      wrapper.get('[data-host-id="nea:host:alpha"]').attributes('cx'),
    )

    expect(heliocentricAlphaX).toBeGreaterThan(heliocentricOriginX)

    await wrapper.get('[data-coordinate-frame="galactocentric"]').trigger('click')

    const galactocentricOriginX = Number(
      wrapper.get('[data-galactic-centre-origin]').attributes('cx'),
    )
    const galactocentricAlphaX = Number(
      wrapper.get('[data-host-id="nea:host:alpha"]').attributes('cx'),
    )

    expect(galactocentricAlphaX).toBeLessThan(galactocentricOriginX)
  })

  it('renders only hosts positioned in the selected frame', async () => {
    const frameSpecificRecords: HostVisualizationRecord[] = [
      host({
        hostId: 'nea:host:heliocentric-only',
        hostName: 'Heliocentric only',
        heliocentricPc: { x: 10, y: 2, z: 1 },
        galactocentricKpc: null,
      }),
      host({
        hostId: 'nea:host:galactocentric-only',
        hostName: 'Galactocentric only',
        heliocentricPc: null,
        galactocentricKpc: { x: -8, y: 0.5, z: 0.02 },
      }),
    ]

    const wrapper = mount(HostScatterPlot, {
      props: { records: frameSpecificRecords },
    })

    expect(
      wrapper.findAll('[data-host-point]').map((point) => point.attributes('data-host-id')),
    ).toEqual(['nea:host:heliocentric-only'])
    expect(wrapper.text()).toContain('1 of 2 hosts positioned')

    await wrapper.get('[data-coordinate-frame="galactocentric"]').trigger('click')

    expect(
      wrapper.findAll('[data-host-point]').map((point) => point.attributes('data-host-id')),
    ).toEqual(['nea:host:galactocentric-only'])
    expect(wrapper.text()).toContain('1 of 2 hosts positioned')
  })

  it('shows the Sun and Galactic centre in both coordinate frames', async () => {
    const wrapper = mount(HostScatterPlot, {
      props: { records },
    })

    const heliocentricSun = wrapper.get('[data-sun-reference]')
    const heliocentricGalacticCentre = wrapper.get('[data-galactic-centre-reference]')

    expect(Number(heliocentricGalacticCentre.attributes('cx'))).toBeGreaterThan(
      Number(heliocentricSun.attributes('cx')),
    )

    await wrapper.get('[data-coordinate-frame="galactocentric"]').trigger('click')

    const galactocentricSun = wrapper.get('[data-sun-reference]')
    const galactocentricGalacticCentre = wrapper.get('[data-galactic-centre-reference]')

    expect(Number(galactocentricSun.attributes('cx'))).toBeLessThan(
      Number(galactocentricGalacticCentre.attributes('cx')),
    )
  })
})
