// One chair + grass scene, rendered differently per page. Each page picks a preset and can override any
// value: <SeatScene preset="state" overrides={{ chair: { scale: 1 } }} />. All distances are world units.
import { CLEAN_LOOK, VHS_LOOK, type CRTLook } from './crt';
import type { Groove } from './groove';

export type SceneConfig = {
  /** How the ground reads on screen: height ÷ width of the ring and grass patch (1 = circle, 0.45 = flat oval). */
  oval: number;
  /** Camera elevation in degrees (lower = more face-on). */
  tilt: number;
  /** Radius of the walkers' ring; the grass patch is sized from it. */
  radius: number;
  /** Grass edge as a multiple of `radius`. */
  patchReach: number;
  /** Grass blades on desktop / on phones. */
  blades: { desktop: number; touch: number };
  /** Grass tone: brightness multiplier (1 = colours as set in grass.ts, lower = darker). */
  grass: { brightness: number };
  chair: {
    scale: number;   // chair.glb is 0.88 units tall
    x: number;       // left/right
    z: number;       // depth: negative = further back (up the screen)
    turn: number;    // degrees; the 3/4 view
  };
  walkers: {
    count: number;   // 0 = none (their model and animation aren't even downloaded)
    scale: number;   // the model is 2 units tall
    outfits: string[];
    motions: string[]; // clips the dancers play, cycled through in ring order; each one carries its own travel
    groove: Groove;    // Afrobeats bounce laid over the clip (src/lib/groove.ts); amount 0 = off
  };
  /** Framing. The view always fits `width` (in grass-patch widths, sand included); `minHeight` stops it getting
   *  too tight on wide screens; `lift` moves the scene down the frame (positive) or up (negative). */
  fit: { width: number; pad: number; minHeight: number; lift: number }; // pad: extra world units of width
  /** Where the floating button (sound / +) attaches, in the chair's own space (× chair scale). */
  label: [number, number, number];
  /** CRT / VHS post-process (src/lib/crt.ts). `look: CLEAN_LOOK` for the plain render. */
  look: CRTLook;
};

export const scenes = {
  // Home page: the original crowd circling the presidential seat.
  home: {
    oval: 0.45,
    tilt: 32,
    radius: 1.15,
    patchReach: 1.24,
    blades: { desktop: 70_000, touch: 40_000 },
    grass: { brightness: 0.75 },
    chair: { scale: 0.9, x: 0, z: -0.145, turn: -28 },
    walkers: { count: 6, scale: 0.62, outfits: ['#e4ad7b', '#ffffff', '#e4ad7b', '#ffffff', '#e4ad7b', '#ffffff'], motions: ['/models/dance-graceful.glb'], groove: { amount: 1, bpm: 112 } },
    fit: { width: 1, pad: 0.4, minHeight: 3.6, lift: -0.2 }, // raised: the box nav sits along the bottom now
    label: [0.3, 0.95, 0],
    look: CLEAN_LOOK, // TV effect paused; VHS_LOOK turns it back on
  },
  // State seat page (/seats/state/kogi): the chair alone on a small, flat patch, centred on it
  // (OVRA Figma 630:232, the red dashed ring).
  state: {
    oval: 0.34,
    tilt: 32,
    radius: 1.15,
    patchReach: 0.87,
    blades: { desktop: 45_000, touch: 28_000 },
    grass: { brightness: 0.75 },
    chair: { scale: 0.9, x: 0, z: 0, turn: -28 },
    walkers: { count: 0, scale: 0.62, outfits: [], motions: [], groove: { amount: 0, bpm: 112 } },
    fit: { width: 1.15, pad: 0, minHeight: 2.4, lift: 0.25 },
    label: [0.3, 0.95, 0],
    look: CLEAN_LOOK, // TV effect paused; VHS_LOOK turns it back on
  },
} satisfies Record<string, SceneConfig>;

export type ScenePreset = keyof typeof scenes;
export { CLEAN_LOOK, VHS_LOOK };

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? (T[K] extends unknown[] ? T[K] : DeepPartial<T[K]>) : T[K] };
export type SceneOverrides = DeepPartial<SceneConfig>;

export function sceneConfig(preset: ScenePreset, overrides: SceneOverrides = {}): SceneConfig {
  const base: SceneConfig = structuredClone(scenes[preset]);
  for (const [k, v] of Object.entries(overrides) as [keyof SceneConfig, unknown][]) {
    if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(base[k] as object, v);
    else if (v !== undefined) (base as Record<string, unknown>)[k] = v;
  }
  return base;
}
