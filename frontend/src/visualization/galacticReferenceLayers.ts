import type { Color } from '@deck.gl/core'
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers'

import { coordinateFrames } from '@/domain/coordinateFrames'
import type { CartesianPosition } from '@/domain/coordinates'

export interface GalacticReferencePoint {
  id: 'sun' | 'galactic-centre'
  label: string
  position: CartesianPosition
  color: Color
}

/**
 * Reference annotations in the pipeline's Astropy v4.0 Galactocentric frame.
 *
 * Source positions retain XYZ in kiloparsecs. This 2D layer renders
 * [x, y, 0] to avoid depth clipping when zooming.
 * Scientific sources are documented in domain/coordinates.ts
 *
 * Marker and text sizes are screen pixels, not physical object sizes
 */
export function buildGalacticReferenceLayers(): [
  ScatterplotLayer<GalacticReferencePoint>,
  TextLayer<GalacticReferencePoint>,
] {
  const frame = coordinateFrames.galactocentric

  const references: GalacticReferencePoint[] = [
    {
      id: 'sun',
      label: 'Sun',
      position: frame.sunPosition,
      color: [253, 224, 71, 255],
    },
    {
      id: 'galactic-centre',
      label: 'Galactic centre',
      position: frame.galacticCentrePosition,
      color: [240, 171, 252, 255],
    },
  ]

  const getPosition = ({ position }: GalacticReferencePoint): [number, number, number] => [
    position.x,
    position.y,
    0,
  ]

  const getColor = (reference: GalacticReferencePoint): Color => reference.color

  // These are visual annotations, so density geometry must not hide them
  const parameters = {
    depthWriteEnabled: false,
    depthCompare: 'always',
  } as const

  return [
    new ScatterplotLayer<GalacticReferencePoint>({
      id: 'galactic-reference-points',
      data: references,
      coordinateSystem: 'cartesian',
      getPosition,
      getFillColor: getColor,
      radiusUnits: 'pixels',
      getRadius: 6,
      stroked: true,
      lineWidthUnits: 'pixels',
      getLineWidth: 1.5,
      getLineColor: [15, 23, 42, 255],
      pickable: false,
      parameters,
    }),

    new TextLayer<GalacticReferencePoint>({
      id: 'galactic-reference-labels',
      data: references,
      coordinateSystem: 'cartesian',
      getPosition,
      getText: (reference) => reference.label,
      getColor,
      sizeUnits: 'pixels',
      getSize: 14,
      fontFamily: 'sans-serif',
      getTextAnchor: 'start',
      getAlignmentBaseline: 'center',
      getPixelOffset: [12, 0],
      background: true,
      getBackgroundColor: [2, 6, 23, 220],
      backgroundPadding: [4, 2],
      pickable: false,
      parameters,
    }),
  ]
}
