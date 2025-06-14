/**
 * Response animation constants for the portfolio AI assistant.
 *
 * This centralizes all animation configuration for ResponseEmergence component
 * to ensure consistency between actual animations and timing guarantees.
 */

export const RESPONSE_ANIMATION_CONFIG = {
  // ===== TIMING =====
  // Individual animation durations (in seconds)
  EMERGENCE_DURATION: 1,
  EMERGENCE_STAGGER: 0.2,
  DISSOLUTION_DURATION: 1,
  DISSOLUTION_STAGGER: 0.3,

  // ===== TRANSFORM VALUES =====
  // Scattered state ranges for emergence/dissolution
  SCATTER_RANGE_X: 500, // pixels: -125 to +125
  SCATTER_RANGE_Y: 500, // pixels: -125 to +125
  SCATTER_ROTATION: 120, // degrees: -60 to +60

  // Dissolution scatter (more dramatic)
  DISSOLUTION_SCATTER_X: 600, // pixels: -150 to +150
  DISSOLUTION_SCATTER_Y: 600, // pixels: -150 to +150
  DISSOLUTION_SCATTER_ROTATION: 360, // degrees: -90 to +90

  // ===== SCALE VALUES =====
  // Emergence scale values
  EMERGENCE_SCATTERED_SCALE: 0.2, // Scale when scattered (emergence)
  EMERGENCE_FINAL_SCALE: 1.0, // Scale when in position (emergence)

  // Dissolution scale values
  DISSOLUTION_SCATTERED_SCALE: 0.5, // Scale when scattered (dissolution)
  DISSOLUTION_FINAL_SCALE: 1.0, // Scale when starting dissolution

  // ===== EASING & PHYSICS =====
  EMERGENCE_EASE: 'back.out(.4, .01)', // Gentler elastic bounce
  DISSOLUTION_EASE: 'power1.out', // Sharp dissolution

  // ===== GSAP SETTINGS =====
  FORCE_3D: true,
  TRANSFORM_ORIGIN: '50% 50% -1000px', // Center origin for transforms

  // Stagger direction settings
  EMERGENCE_STAGGER_FROM: 'start', // 'start', 'center', 'end', 'edges', 'random'
  DISSOLUTION_STAGGER_FROM: 'random', // 'start', 'center', 'end', 'edges', 'random'

  // ===== TIMING GUARANTEES =====
  // Buffer time to ensure smooth transitions (in milliseconds)
  TIMING_BUFFER: 0,

  // Calculated total durations
  get EMERGENCE_TOTAL_MS() {
    return (this.EMERGENCE_DURATION + this.EMERGENCE_STAGGER) * 1000;
  },

  get DISSOLUTION_TOTAL_MS() {
    return (this.DISSOLUTION_DURATION + this.DISSOLUTION_STAGGER) * 1000;
  },

  // Maximum time needed for any single animation
  get MAX_ANIMATION_MS() {
    return Math.max(this.EMERGENCE_TOTAL_MS, this.DISSOLUTION_TOTAL_MS);
  },

  // Minimum time to guarantee between API responses (includes buffer)
  get MINIMUM_API_INTERVAL_MS() {
    return this.MAX_ANIMATION_MS + this.TIMING_BUFFER;
  },
} as const;

// Export individual values for convenience
export const {
  // Timing
  EMERGENCE_DURATION,
  EMERGENCE_STAGGER,
  DISSOLUTION_DURATION,
  DISSOLUTION_STAGGER,

  // Transform values
  SCATTER_RANGE_X,
  SCATTER_RANGE_Y,
  SCATTER_ROTATION,
  DISSOLUTION_SCATTER_X,
  DISSOLUTION_SCATTER_Y,
  DISSOLUTION_SCATTER_ROTATION,

  // Scale values
  EMERGENCE_SCATTERED_SCALE,
  EMERGENCE_FINAL_SCALE,
  DISSOLUTION_SCATTERED_SCALE,
  DISSOLUTION_FINAL_SCALE,

  // Easing
  EMERGENCE_EASE,
  DISSOLUTION_EASE,

  // GSAP settings
  FORCE_3D,
  TRANSFORM_ORIGIN,
  EMERGENCE_STAGGER_FROM,
  DISSOLUTION_STAGGER_FROM,

  // Calculated values
  MINIMUM_API_INTERVAL_MS,
} = RESPONSE_ANIMATION_CONFIG;
