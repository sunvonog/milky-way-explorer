// frontend/src/lib/coords.ts
/** Galactrocentric frame: Sun at (-R0, 0, Z0), Galactic centre at origin. */
export const SUN_GALACTOCENTRIC_R_KPC = 8.122

export interface Spherical {
  lDeg: number
  bDeg: number
  distanceKpc: number
}

export interface CartesianKpc {
  x: number
  y: number
  z: number
}

/** Galactic (l, b, d) -> heliocentric Cartesian, x toward the Galactic centre. */
export function galacticToHeliocentric({ lDeg, bDeg, distanceKpc }: Spherical): CartesianKpc {
  const l = (lDeg * Math.PI) / 180
  const b = (bDeg * Math.PI) / 180
  const cosB = Math.cos(b)

  return {
    x: distanceKpc * cosB * Math.cos(l),
    y: distanceKpc * cosB * Math.sin(l),
    z: distanceKpc * Math.sin(b),
  }
}
