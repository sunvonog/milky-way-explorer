import { describe, expect, it } from 'vitest'

import { createGalacticMapView, fitGalacticMapView } from './galacticMapView'

function viewportFor(width: number, height: number) {
  const view = createGalacticMapView()
  const viewState = fitGalacticMapView({
    width,
    height,
    extentKpc: 20,
    paddingPx: 40,
  })

  const viewport = view.makeViewport({ width, height, viewState })

  if (viewport === null) {
    throw new Error('expected a viewport for positive dimensions')
  }

  return viewport
}

describe('Galactic map camera', () => {
  it('places the Galactic centre at the viewport centre', () => {
    const viewport = viewportFor(800, 600)
    const centre = viewport.project([0, 0, 0])

    expect(centre[0]).toBeCloseTo(400)
    expect(centre[1]).toBeCloseTo(300)
  })

  it.each([
    { width: 800, height: 600, left: 140, top: 40 },
    { width: 600, height: 800, left: 40, top: 140 },
  ])('fits the complete grid into a $width x $height viewport', ({ width, height, left, top }) => {
    const viewport = viewportFor(width, height)

    const lowerLeft = viewport.project([-20, -20, 0])
    const upperRight = viewport.project([20, 20, 0])

    expect(lowerLeft[0]).toBeCloseTo(left)
    expect(lowerLeft[1]).toBeCloseTo(height - top)
    expect(upperRight[0]).toBeCloseTo(width - left)
    expect(upperRight[1]).toBeCloseTo(top)
  })

  it('preserves equal scale with positive x rightward and positive y upward', () => {
    const viewport = viewportFor(800, 600)

    const origin = viewport.project([0, 0, 0])
    const alongX = viewport.project([1, 0, 0])
    const alongY = viewport.project([0, 1, 0])

    const horizontalPixels = alongX[0]! - origin[0]!
    const verticalPixels = origin[1]! - alongY[1]!

    expect(horizontalPixels).toBeGreaterThan(0)
    expect(verticalPixels).toBeGreaterThan(0)
    expect(horizontalPixels).toBeCloseTo(verticalPixels)
  })

  it('zooms out by one level when the physical extent doubles', () => {
    const dimensions = {
      width: 800,
      height: 600,
      paddingPx: 40,
    }

    const original = fitGalacticMapView({
      ...dimensions,
      extentKpc: 20,
    })
    const larger = fitGalacticMapView({
      ...dimensions,
      extentKpc: 40,
    })

    expect(larger.zoom).toBeCloseTo(original.zoom - 1)
  })

  it.each([
    { width: 0 },
    { height: 0 },
    { width: 80 },
    { extentKpc: 0 },
    { extentKpc: Number.POSITIVE_INFINITY },
    { paddingPx: -1 },
  ])('rejects unusable camera inputs: %o', (overrides) => {
    expect(() =>
      fitGalacticMapView({
        width: 800,
        height: 600,
        extentKpc: 20,
        paddingPx: 40,
        ...overrides,
      }),
    ).toThrow(RangeError)
  })
})
