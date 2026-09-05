import { OrthographicView, type OrthographicViewState } from '@deck.gl/core'

export interface GalacticMapViewState extends OrthographicViewState {
  target: [xKpc: number, yKpc: number, zKpc: number]
  zoom: number
}

export interface FitGalacticMapViewOptions {
  width: number
  height: number
  extentKpc: number
  paddingPx: number
}

/**
 * View the Galactic x-y plane with positive x rightward and positive y upward.
 * flipY: false gives the Cartesian orientation used by our SVG plots
 */
export function createGalacticMapView(): OrthographicView {
  return new OrthographicView({
    id: 'galactic-map',
    flipY: false,
    controller: true,
  })
}

/**
 * Fit the full square grid [-extentKpc, +extentKpc] around the Galactic centre.
 *
 * The usable side length is min(width, height) - 2 * paddingPx.
 * Dividing by the grid width, 2 * extentKpc, gives pixels per kiloparsecs.
 *
 * deck.gl's orthographic scale is 2^zoom, so zoom = log2(pixelsPerKpc).
 * A single zoom value preserves equal physical scale on both axes.
 *
 * @see https://deck.gl/docs/api-reference/core/orthographic-view
 */
export function fitGalacticMapView({
  width,
  height,
  extentKpc,
  paddingPx,
}: FitGalacticMapViewOptions): GalacticMapViewState {
  if (![width, height, extentKpc, paddingPx].every(Number.isFinite)) {
    throw new RangeError('camera inputs must be finite numbers')
  }

  if (extentKpc <= 0) {
    throw new RangeError('extentKpc must be positive')
  }

  if (paddingPx < 0) {
    throw new RangeError('paddingPx must be non-negative')
  }

  const usableSidePx = Math.min(width, height) - 2 * paddingPx

  if (usableSidePx <= 0) {
    throw new RangeError('viewport must have positive space inside its padding')
  }

  const pixelsPerKpc = usableSidePx / (2 * extentKpc)

  return {
    target: [0, 0, 0],
    zoom: Math.log2(pixelsPerKpc),
  }
}
