import { describe, expect, it } from 'vitest'

import { coordinateFrames } from '@/domain/coordinateFrames'
import {
  buildGalacticReferenceLayers,
  type GalacticReferencePoint,
} from './galacticReferenceLayers'

describe('buildGalacticReferenceLayers', () => {
  it('uses the shared Sun and Galactic-centre positions', () => {
    const [markers, labels] = buildGalacticReferenceLayers()
    const frame = coordinateFrames.galactocentric

    expect(markers.props.data).toMatchObject([
      {
        id: 'sun',
        label: 'Sun',
        position: frame.sunPosition,
      },
      {
        id: 'galactic-centre',
        label: 'Galactic centre',
        position: frame.galacticCentrePosition,
      },
    ])

    expect(labels.props.data).toEqual(markers.props.data)
  })

  it('projects references onto XY while preserving source coordinates', () => {
    const [markers, labels] = buildGalacticReferenceLayers()

    const reference: GalacticReferencePoint = {
      id: 'sun',
      label: 'Sun',
      position: { x: 2, y: 3, z: 4 },
      color: [253, 224, 71, 255],
    }

    const info = {
      index: 0,
      data: [reference],
      target: [],
    }

    for (const layer of [markers, labels]) {
      const accessor = layer.props.getPosition

      if (typeof accessor !== 'function') {
        throw new TypeError('Expected a position accessor')
      }

      expect(accessor(reference, info)).toEqual([2, 3, 0])
    }

    expect(reference.position).toEqual({ x: 2, y: 3, z: 4 })

    expect(labels.props.getText(reference, info)).toBe('Sun')

    for (const accessor of [markers.props.getFillColor, labels.props.getColor]) {
      if (typeof accessor !== 'function') {
        throw new TypeError('Expected a colour accessor')
      }

      expect(accessor(reference, info)).toEqual(reference.color)
    }
  })

  it('uses screen-pixel sizes for annotations in Cartesian coordinates', () => {
    const [markers, labels] = buildGalacticReferenceLayers()

    expect(markers.props.coordinateSystem).toBe('cartesian')
    expect(labels.props.coordinateSystem).toBe('cartesian')

    expect(markers.props.radiusUnits).toBe('pixels')
    expect(markers.props.lineWidthUnits).toBe('pixels')
    expect(labels.props.sizeUnits).toBe('pixels')
  })

  it('keeps reference annotations visible over the density layer', () => {
    const layers = buildGalacticReferenceLayers()

    for (const layer of layers) {
      expect(layer.props.parameters).toMatchObject({
        depthCompare: 'always',
        depthWriteEnabled: false,
      })
    }
  })
})
