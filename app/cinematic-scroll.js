/**
 * DARK VESSEL DETECTION — CINEMATIC SCROLL ENGINE
 * ─────────────────────────────────────────────────
 * Frame-accurate scroll-driven canvas animation.
 * Uses lerp interpolation for ultra-smooth Apple-level feel.
 * Supports retina/DPR, prefers-reduced-motion, progressive loading.
 */

(() => {
  'use strict';

  /* ─── CONFIG ─────────────────────────────────────────────── */
  const TOTAL_FRAMES    = 150;
  const FRAMES_DIR      = './frames/';
  const FRAME_EXT       = '.jpg';
  const SCROLL_HEIGHT   = '550vh';  // matches CSS #hero-scroll-section height
  const LERP_FACTOR     = 0.10;     // smoothing (lower = smoother/slower)
  const HERO_TEXT_START = 0.55;     // scroll % when hero text fades in
  const TELE_START      = 0.15;     // scroll % when telemetry fades in
  const HINT_HIDE       = 0.04;     // scroll % when hint disappears

  /* ─── ELEMENTS ───────────────────────────────────────────── */
  const canvas        = document.getElementById('hero-canvas');
  const ctx           = canvas.getContext('2d');
  const section       = document.getElementById('hero-scroll-section');
  const progressFill  = document.getElementById('scroll-progress-fill');
  const frameNum      = document.getElementById('frame-num');
  const heroText      = document.getElementById('hero-center-text');
  const teleStrip     = document.getElementById('telemetry-strip');
  const scrollHint    = document.getElementById('scroll-hint');
  const navLinks      = document.querySelector('.nav-links');

  /* ─── STATE ──────────────────────────────────────────────── */
  const images = new Array(TOTAL_FRAMES).fill(null);
  const loaded = new Array(TOTAL_FRAMES).fill(false);
  let   loadedCount   = 0;
  let   currentFrame  = 0;       // actual rendered frame (lerped)
  let   targetFrame   = 0;       // frame derived from scroll
  let   rafId         = null;
  let   isReady       = false;   // true once first frame is decoded
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ─── LOADING UI ──────────────────────────────────────────── */
  // Insert loading screen dynamically
  const loadingScreen = document.createElement('div');
  loadingScreen.id = 'loading-screen';
  loadingScreen.innerHTML = `
    <div class="loading-logo">◈ DARKVESSEL</div>
    <div class="loading-bar-track">
      <div class="loading-bar-fill" id="ldr-fill" style="width:0%"></div>
    </div>
    <div class="loading-pct" id="ldr-pct">INITIALIZING…</div>
  `;
  document.body.prepend(loadingScreen);
  const ldrFill = document.getElementById('ldr-fill');
  const ldrPct  = document.getElementById('ldr-pct');

  function updateLoadingUI(n) {
    const pct = Math.round((n / TOTAL_FRAMES) * 100);
    ldrFill.style.width = pct + '%';
    ldrPct.textContent  = `LOADING FRAMES — ${pct}%`;
  }

  function hideLoadingScreen() {
    loadingScreen.classList.add('fade-out');
    setTimeout(() => loadingScreen.remove(), 700);
  }

  /* ─── FRAME PATH ─────────────────────────────────────────── */
  function framePath(i) {
    // i is 0-indexed → file is frame-001.jpg through frame-150.jpg
    return `${FRAMES_DIR}frame-${String(i + 1).padStart(3, '0')}${FRAME_EXT}`;
  }

  /* ─── PROGRESSIVE LOADING ────────────────────────────────── */
  // Priority: load frames in this order:
  // 1. First frame immediately (needed to render before scroll)
  // 2. Rest in sequence

  function loadFrame(index) {
    return new Promise((resolve) => {
      const img = new Image();
      img.decoding = 'async';
      img.onload = img.onerror = () => {
        images[index] = img.complete ? img : null;
        loaded[index] = true;
        loadedCount++;
        updateLoadingUI(loadedCount);
        if (index === 0 && !isReady) {
          isReady = true;
          resizeCanvas();
          renderFrame(0);
          startLoop();
          hideLoadingScreen();
          teleStrip.classList.add('visible');
        }
        resolve();
      };
      img.src = framePath(index);
    });
  }

  async function loadAllFrames() {
    // Load frame 0 with highest priority
    await loadFrame(0);

    // Load remaining frames sequentially (batched for bandwidth)
    const BATCH = 10;
    for (let start = 1; start < TOTAL_FRAMES; start += BATCH) {
      const end = Math.min(start + BATCH, TOTAL_FRAMES);
      const batch = [];
      for (let i = start; i < end; i++) batch.push(loadFrame(i));
      await Promise.all(batch);
    }
  }

  /* ─── CANVAS SIZING ──────────────────────────────────────── */
  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const w   = window.innerWidth;
    const h   = window.innerHeight;
    canvas.width  = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width  = w + 'px';
    canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);
    // Re-render current frame after resize
    if (isReady) renderFrame(Math.round(currentFrame));
  }

  window.addEventListener('resize', resizeCanvas, { passive: true });

  /* ─── RENDER FRAME ───────────────────────────────────────── */
  function renderFrame(frameIdx) {
    const idx = Math.max(0, Math.min(TOTAL_FRAMES - 1, Math.round(frameIdx)));

    // Find nearest loaded frame (look backward, then forward)
    let img = null;
    for (let offset = 0; offset <= 5; offset++) {
      const fwd = idx + offset;
      const bwd = idx - offset;
      if (fwd < TOTAL_FRAMES && loaded[fwd] && images[fwd]) { img = images[fwd]; break; }
      if (bwd >= 0           && loaded[bwd] && images[bwd]) { img = images[bwd]; break; }
    }
    if (!img) return;

    const cw = window.innerWidth;
    const ch = window.innerHeight;

    // Cover fit (like object-fit: cover)
    const scale    = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
    const drawW    = img.naturalWidth  * scale;
    const drawH    = img.naturalHeight * scale;
    const offsetX  = (cw - drawW) / 2;
    const offsetY  = (ch - drawH) / 2;

    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
  }

  /* ─── SCROLL → FRAME INDEX ───────────────────────────────── */
  function getScrollProgress() {
    const sectionTop    = section.getBoundingClientRect().top + window.scrollY;
    const sectionHeight = section.offsetHeight - window.innerHeight;
    const scrolled      = window.scrollY - sectionTop;
    return Math.max(0, Math.min(1, scrolled / sectionHeight));
  }

  function progressToFrame(p) {
    return p * (TOTAL_FRAMES - 1);
  }

  /* ─── ANIMATION LOOP ─────────────────────────────────────── */
  function startLoop() {
    if (rafId) cancelAnimationFrame(rafId);

    function tick() {
      rafId = requestAnimationFrame(tick);

      if (reducedMotion) {
        // Instant seek, no lerp
        if (Math.round(currentFrame) !== Math.round(targetFrame)) {
          currentFrame = targetFrame;
          renderFrame(currentFrame);
          updateHUD(targetFrame / (TOTAL_FRAMES - 1));
        }
        return;
      }

      // Lerp current toward target
      const delta = targetFrame - currentFrame;
      if (Math.abs(delta) > 0.01) {
        currentFrame += delta * LERP_FACTOR;
        renderFrame(currentFrame);
        updateHUD(currentFrame / (TOTAL_FRAMES - 1));
      }
    }

    tick();
  }

  /* ─── HUD UPDATE ─────────────────────────────────────────── */
  function updateHUD(progress) {
    // Scroll progress rail
    if (progressFill) progressFill.style.height = (progress * 100).toFixed(1) + '%';

    // Frame counter
    const displayFrame = Math.round(currentFrame) + 1;
    if (frameNum) frameNum.textContent = String(displayFrame).padStart(3, '0');

    // Hero text
    if (heroText) {
      if (progress >= HERO_TEXT_START) {
        heroText.classList.add('visible');
      } else {
        heroText.classList.remove('visible');
      }
    }

    // Scroll hint
    if (scrollHint) {
      if (progress > HINT_HIDE) {
        scrollHint.classList.add('hidden');
      } else {
        scrollHint.classList.remove('hidden');
      }
    }

    // Telemetry strip + nav links — only show AFTER animation fully completes (100% scroll)
    const animDone = progress >= 0.99;
    if (teleStrip) {
      if (animDone) teleStrip.classList.add('visible');
      else teleStrip.classList.remove('visible');
    }
    if (navLinks) {
      if (animDone) navLinks.classList.add('nav-visible');
      else navLinks.classList.remove('nav-visible');
    }
  }

  /* ─── SCROLL LISTENER ────────────────────────────────────── */
  let ticking = false;
  function onScroll() {
    if (!isReady) return;
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(() => {
        const progress = getScrollProgress();
        targetFrame = progressToFrame(progress);
        updateHUD(progress);
        ticking = false;
      });
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });

  /* ─── METRIC BAR INTERSECTION OBSERVER ───────────────────── */
  const metricFills = document.querySelectorAll('.metric-fill');
  if (metricFills.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('animate');
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.3 });
    metricFills.forEach(el => observer.observe(el));
  }

  /* ─── PIPELINE STEP ENTRANCE ─────────────────────────────── */
  const pipelineSteps = document.querySelectorAll('.pipeline-step, .stat-card, .metric-bar-card');
  if (pipelineSteps.length) {
    const enterObserver = new IntersectionObserver((entries) => {
      entries.forEach((e, i) => {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = e.target.style.transform.replace('translateY(24px)', 'translateY(0)');
          enterObserver.unobserve(e.target);
        }
      });
    }, { threshold: 0.1 });

    pipelineSteps.forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform += ' translateY(24px)';
      el.style.transition = `opacity 0.6s ${i * 0.08}s ease-out, transform 0.6s ${i * 0.08}s ease-out`;
      enterObserver.observe(el);
    });
  }

  /* ─── INIT ───────────────────────────────────────────────── */
  // Telemetry and nav links are hidden until scroll animation completes (handled in updateHUD)

  // Kick off frame loading
  loadAllFrames().catch(console.error);

})();
