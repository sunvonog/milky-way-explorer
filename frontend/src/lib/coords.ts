// frontend/src/lib/coords.ts
/** Galactocentric frame: Sun at (-R0, 0, Z0), Galactic centre at origin. */
export const SUN_GALACTOCENTRIC_R_KPC = 8.122
/** Solar height above the Galactic midplane in Astropy's v4.0 frame. */
export const SUN_GALACTOCENTRIC_Z_KPC = 0.0208

/**
 * Astropy tilts the Galactocentric x-axis to account for the solar height,
 * so the Sun's x coordinate is slightly smaller in magnitude than R0.
 */
export const SUN_GALACTOCENTRIC_X_KPC = -Math.sqrt(
  SUN_GALACTOCENTRIC_R_KPC ** 2 - SUN_GALACTOCENTRIC_Z_KPC ** 2,
)

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
