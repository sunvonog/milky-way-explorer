import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { DensityVisualizationRecord } from '@/domain/density'
import GaiaDensityPlot from './GaiaDensityPlot.vue'

function densityCell(
  overrides: Partial<DensityVisualizationRecord> = {},
): DensityVisualizationRecord {
  return {
    gridLevel: 4,
    cellX: 0,
    cellY: 0,
    distanceTier: 'baseline',
    cellCenterXKpc: -15,
    cellCenterYKpc: -15,
    cellSizeKpc: 10,
    sourceCount: 1,
    weightedBrightness: 0.1,
    meanBpRp: 0.8,
    ...overrides,
  }
}

describe('GaiaDensityPlot', () => {
  it('renders one rectangle for each occupied density cell', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [
          densityCell({ sourceCount: 1 }),
          densityCell({
            cellX: 1,
            cellCenterXKpc: -5,
            sourceCount: 16,
          }),
        ],
      },
    })

    const cells = wrapper.findAll('[data-density-cell]')

    expect(cells).toHaveLength(2)
    expect(cells.map((cell) => cell.attributes('data-cell-x'))).toEqual(['0', '1'])
    expect(wrapper.text()).toContain('17 Gaia sources in 2 occupied cells')
  })

  it('renders denser cells with greater opacity', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [
          densityCell({ sourceCount: 1 }),
          densityCell({
            cellX: 1,
            cellCenterXKpc: -5,
            sourceCount: 16,
          }),
        ],
      },
    })

    const cells = wrapper.findAll('[data-density-cell]')

    expect(Number(cells[1]!.attributes('fill-opacity'))).toBeGreaterThan(
      Number(cells[0]!.attributes('fill-opacity')),
    )
  })

  it('renders the Sun and Galactic centre reference points', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [densityCell()],
      },
    })

    const sun = wrapper.get('[data-sun-reference]')
    const galacticCentre = wrapper.get('[data-galactic-centre-reference]')

    expect(Number(sun.attributes('cx'))).toBeLessThan(Number(galacticCentre.attributes('cx')))
    expect(wrapper.find('[data-galactic-centre-origin]').exists()).toBe(true)
  })

  it('uses the highest available grid resolution', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [
          densityCell({ gridLevel: 4 }),
          densityCell({
            gridLevel: 8,
            cellSizeKpc: 5,
            cellCenterXKpc: -17.5,
            cellCenterYKpc: -17.5,
          }),
        ],
      },
    })

    expect(wrapper.findAll('[data-density-cell]')).toHaveLength(1)
    expect(wrapper.text()).toContain('8 x 8 grid')
  })

  it('labels both axes as Galactocentric kiloparsecs', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [densityCell()],
      },
    })

    expect(wrapper.get('[data-axis-title="x"]').text()).toBe('Galactocentric x (kpc)')
    expect(wrapper.get('[data-axis-title="y"]').text()).toBe('Galactocentric y (kpc)')
  })

  it('requires explicit opt-in before rendering exploratory density', async () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [
          densityCell({
            distanceTier: 'baseline',
            sourceCount: 10,
          }),
          densityCell({
            distanceTier: 'exploratory',
            sourceCount: 4,
          }),
        ],
      },
    })

    const initialCells = wrapper.findAll('[data-density-cell]')

    expect(initialCells).toHaveLength(1)
    expect(initialCells[0]!.attributes('data-distance-tier')).toBe('baseline')
    expect(wrapper.text()).toContain('10 Gaia sources in 1 occupied cell')

    const toggle = wrapper.get<HTMLInputElement>('[data-density-quality-toggle]')

    expect(toggle.element.checked).toBe(false)
    expect(toggle.attributes('aria-describedby')).toBe('gaia-density-quality-description')

    await toggle.setValue(true)

    const expandedCells = wrapper.findAll('[data-density-cell]')

    expect(expandedCells).toHaveLength(2)
    expect(expandedCells.map((cell) => cell.attributes('data-distance-tier'))).toEqual([
      'baseline',
      'exploratory',
    ])

    expect(expandedCells[0]!.classes()).toContain('fill-cyan-400')
    expect(expandedCells[1]!.classes()).toContain('fill-amber-400')
    expect(wrapper.text()).toContain('14 Gaia sources in 1 occupied cell')
  })

  it('explains what exoplatory density means', () => {
    const wrapper = mount(GaiaDensityPlot, {
      props: {
        records: [densityCell()],
      },
    })

    const label = wrapper.get('label[for="include-exploratory-density"]')
    const description = wrapper.get('#gaia-density-quality-description')

    expect(label.text()).toContain('exploratory')
    expect(description.text()).toContain('S/N')
    expect(description.text()).toContain('less stable')
  })
})
