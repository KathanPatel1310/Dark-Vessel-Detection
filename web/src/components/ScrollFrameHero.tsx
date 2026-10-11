import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ChevronDown } from 'lucide-react';

const TOTAL = 150;
const LERP = 0.12;
const frameUrl = (i: number) => `/frames/frame-${String(i + 1).padStart(3, '0')}.jpg`;

/** Smoothstep window: 0 outside [a,d], 1 inside [b,c], eased ramps between. */
const win = (p: number, a: number, b: number, c: number, d: number) => {
  if (p <= a || p >= d) return 0;
  if (p < b) return (p - a) / (b - a);
  if (p > c) return 1 - (p - c) / (d - c);
  return 1;
};

interface Props {
  onLaunch: () => void;
}

/**
 * Scroll-scrubbed canvas frame sequence.
 * All per-frame work happens in refs + one rAF loop — React never re-renders while scrolling.
 */
export const ScrollFrameHero = ({ onLaunch }: Props) => {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const introRef = useRef<HTMLDivElement>(null);
  const midRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const hintRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const [loaded, setLoaded] = useState(0);
  const [ready, setReady] = useState(false);
  const reduced = useRef(
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  useEffect(() => {
    const canvas = canvasRef.current!;
    const section = sectionRef.current!;
    const ctx = canvas.getContext('2d')!;
    const images: (HTMLImageElement | null)[] = new Array(TOTAL).fill(null);
    let current = 0;
    let target = 0;
    let raf = 0;
    let cancelled = false;
    let lastDrawn = -1;
    let cssW = 0;
    let cssH = 0;

    const nearest = (idx: number) => {
      for (let o = 0; o < TOTAL; o++) {
        if (images[idx - o]) return images[idx - o];
        if (images[idx + o]) return images[idx + o];
      }
      return null;
    };

    const draw = (idx: number) => {
      const img = nearest(idx);
      if (!img) return;
      const s = Math.max(cssW / img.naturalWidth, cssH / img.naturalHeight);
      const w = img.naturalWidth * s;
      const h = img.naturalHeight * s;
      ctx.drawImage(img, (cssW - w) / 2, (cssH - h) / 2, w, h);
    };

    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cssW = canvas.clientWidth;
      cssH = canvas.clientHeight;
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // set, never stack
      lastDrawn = -1;
      draw(Math.round(current));
    };

    const progress = () => {
      const rect = section.getBoundingClientRect();
      const total = section.offsetHeight - window.innerHeight;
      return total <= 0 ? 0 : Math.max(0, Math.min(1, -rect.top / total));
    };

    const applyText = (p: number) => {
      const set = (el: HTMLDivElement | null, o: number) => {
        if (!el) return;
        el.style.opacity = String(o);
        el.style.transform = `translateY(${(1 - o) * 24}px)`;
        el.style.pointerEvents = o > 0.5 ? 'auto' : 'none';
      };
      set(introRef.current, win(p, -1, -0.5, 0.12, 0.26));
      set(midRef.current, win(p, 0.3, 0.42, 0.62, 0.74));
      set(endRef.current, win(p, 0.8, 0.9, 1.1, 1.2));
      if (hintRef.current) hintRef.current.style.opacity = String(Math.max(0, 1 - p * 12));
      if (barRef.current) barRef.current.style.transform = `scaleX(${p})`;
    };

    const tick = () => {
      raf = requestAnimationFrame(tick);
      const delta = target - current;
      if (Math.abs(delta) > 0.02) current += delta * LERP;
      else current = target;
      const idx = Math.round(current);
      if (idx !== lastDrawn) {
        lastDrawn = idx;
        draw(idx);
      }
    };

    const onScroll = () => {
      const p = progress();
      target = p * (TOTAL - 1);
      applyText(p);
    };

    const load = (i: number) =>
      new Promise<void>((resolve) => {
        const img = new Image();
        img.decoding = 'async';
        img.onload = () => {
          images[i] = img;
          resolve();
        };
        img.onerror = () => resolve();
        img.src = frameUrl(i);
      });

    (async () => {
      // Frame 0 (or a mid poster frame when motion is reduced) first so the hero paints immediately.
      const first = reduced.current ? Math.floor(TOTAL / 2) : 0;
      await load(first);
      if (cancelled) return;
      resize();
      setReady(true);
      setLoaded(1);
      onScroll();
      if (reduced.current) return;

      raf = requestAnimationFrame(tick);
      let count = 1;
      const BATCH = 8;
      for (let s = 0; s < TOTAL && !cancelled; s += BATCH) {
        const jobs: Promise<void>[] = [];
        for (let i = s; i < Math.min(s + BATCH, TOTAL); i++) if (i !== first) jobs.push(load(i));
        await Promise.all(jobs);
        count += jobs.length;
        if (!cancelled) setLoaded(Math.min(count, TOTAL));
      }
    })();

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', resize);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', resize);
    };
  }, []);

  const loading = loaded < TOTAL && !reduced.current;

  return (
    <section
      ref={sectionRef}
      id="hero"
      aria-label="Introduction"
      className={`relative ${reduced.current ? 'h-dvh' : 'h-[420vh]'}`}
    >
      <div className="sticky top-16 h-[calc(100dvh-4rem)] w-full overflow-hidden bg-[#070B14]">
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B14] via-[#070B14]/30 to-[#070B14]/50" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,#070B14_100%)] opacity-70" />

        {/* Beat 1 — title */}
        <div
          ref={introRef}
          className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center will-change-transform"
        >
          <p className="mb-5 font-mono text-xs tracking-[0.25em] text-cyan-400">MARITIME DOMAIN AWARENESS</p>
          <h1 className="font-display text-5xl font-semibold leading-[1.02] tracking-tight text-white sm:text-7xl lg:text-8xl">
            Seeing the <span className="accent-word">invisible</span>.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-slate-300 sm:text-xl">
            Radar-based detection of ships that switch off their transponders.
          </p>
        </div>

        {/* Beat 2 — idea */}
        <div
          ref={midRef}
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-6 text-center opacity-0 will-change-transform"
        >
          <h2 className="max-w-3xl font-display text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
            Radar sees through <span className="accent-word">night and cloud</span>.
          </h2>
          <p className="mt-5 max-w-lg text-lg text-slate-300">
            Where AIS goes silent, Sentinel-1 SAR still returns every steel hull.
          </p>
        </div>

        {/* Beat 3 — call to action */}
        <div
          ref={endRef}
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-6 text-center opacity-0 will-change-transform"
        >
          <h2 className="max-w-3xl font-display text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
            From a radar blip to a <span className="accent-word">legal bulletin</span>.
          </h2>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={onLaunch}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 active:scale-95"
            >
              Run a live investigation <ArrowRight className="h-4 w-4" />
            </button>
            <a
              href="#how-it-works"
              className="rounded-xl border border-white/20 px-6 py-3 font-medium text-slate-200 transition hover:bg-white/10"
              onClick={(e) => {
                e.preventDefault();
                document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              How it works
            </a>
          </div>
        </div>

        {/* Scroll hint */}
        <div
          ref={hintRef}
          className="absolute bottom-8 left-1/2 flex -translate-x-1/2 flex-col items-center gap-1 text-xs tracking-widest text-slate-400"
        >
          <span>SCROLL</span>
          <ChevronDown className="h-4 w-4 animate-bounce" />
        </div>

        {/* Progress bar */}
        {!reduced.current && (
          <div className="absolute inset-x-0 bottom-0 h-0.5 bg-white/5">
            <div ref={barRef} className="h-full origin-left bg-cyan-400" style={{ transform: 'scaleX(0)' }} />
          </div>
        )}

        {/* Loading indicator */}
        {(!ready || loading) && (
          <div className="absolute right-4 top-4 rounded-md bg-black/50 px-3 py-1.5 font-mono text-[11px] text-slate-300 backdrop-blur">
            Loading frames {Math.round((loaded / TOTAL) * 100)}%
          </div>
        )}
      </div>
    </section>
  );
};
