/**
 * Cartesian position whose frame and unit are specified by the owning field.
 */
export interface CartesianPosition {
  x: number
  y: number
  z: number
}

/**
 * Sun-Galactic-centre distance adopted by Astropy's v4.0 frame.
 * Source: GRAVITY Collaboration (2018).
 */
export const SUN_GALACTOCENTRIC_R_KPC = 8.122

/**
 * Solar height above the Galactic midplane in Astropy's v4.0
 * Source: Bennett & Bovy (2019)
 */
export const SUN_GALACTOCENTRIC_Z_KPC = 0.0208

/**
 * Astropy's Galactocentric x-coordinate for the Sun.
 *
 * The x component is the projection of the Sun-centre distance into the
 * Galactic plane: x = -sqrt(R0^2 - z_sun^2)
 */
export const SUN_GALACTOCENTRIC_X_KPC = -Math.sqrt(
  SUN_GALACTOCENTRIC_R_KPC ** 2 - SUN_GALACTOCENTRIC_Z_KPC ** 2,
)
