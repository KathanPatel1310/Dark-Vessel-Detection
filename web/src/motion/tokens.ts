/**
 * DVD-MDA Motion Tokens & Choreography Language
 * Single source of truth for all timings, easings, and spring dynamics.
 */

export const MOTION_EASINGS = {
  easeOutExpo: 'cubic-bezier(0.16, 1, 0.3, 1)',
  easeInOutQuart: 'cubic-bezier(0.76, 0, 0.24, 1)',
  linear: 'linear',
  springSoft: { stiffness: 170, damping: 26 },
  springSnappy: { stiffness: 400, damping: 30 },
} as const;

export const MOTION_DURATIONS = {
  microMs: 120,
  uiMs: 240,
  revealMs: 800,
  sectionMs: 1000,
  heroIntroMs: 2400,
} as const;

export const MOTION_STAGGERS = {
  listItemMs: 50,
  headlineWordMs: 100,
  characterMs: 25,
} as const;

export const COLOR_TOKENS = {
  bg0: '#070B14',
  bg1: '#0C1424',
  bg2: '#111C33',
  radarCyan: '#00E5FF',
  cautionAmber: '#F59E0B',
  interdictionRed: '#EF4444',
  nominalGreen: '#22C55E',
  hypothesisPurple: '#A78BFA',
} as const;
