/**
 * Cinematic High-Speed Cargo Ship Entrance Sequence
 * Simulates high-speed vessel approach, camera swoop descent, 
 * hull screen-wipe engulfment, and seamless frosted glass transition.
 */

class CinematicIntro {
  constructor(containerId, onComplete) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.canvas = document.createElement('canvas');
    this.canvas.id = 'intro-canvas';
    this.container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    this.onComplete = onComplete;
    this.dpr = window.devicePixelRatio || 1;

    this.width = window.innerWidth;
    this.height = window.innerHeight;

    // Animation Timing & Phases
    this.startTime = null;
    this.duration = 4600; // 4.6 seconds total cinematic sequence
    this.isSkipped = false;
    this.animId = null;

    // Wake & Spray Particle System (3D perspective towards camera)
    this.particles = [];
    this.speedLines = [];

    // Horizon & Vanishing Point
    this.vpX = this.width * 0.5;
    this.vpY = this.height * 0.42;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());

    // Generate initial high-speed radial ocean wake streaks
    for (let i = 0; i < 90; i++) {
      this.speedLines.push({
        angle: (Math.random() - 0.5) * 2.8,
        z: Math.random(),
        speed: 0.02 + Math.random() * 0.035,
        length: 20 + Math.random() * 60,
        opacity: 0.3 + Math.random() * 0.5
      });
    }

    // Generate ocean spray particles
    for (let i = 0; i < 120; i++) {
      this.particles.push({
        x: (Math.random() - 0.5) * 600,
        y: Math.random() * 200,
        z: Math.random(),
        speed: 0.03 + Math.random() * 0.04,
        size: 1 + Math.random() * 3,
        alpha: Math.random() * 0.8
      });
    }

    // Skip trigger (click or ESC)
    this.container.addEventListener('pointerdown', (e) => {
      // Don't skip if clicking the explicit replay button later
      if (!e.target.closest('#btn-replay-intro')) {
        this.skip();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.skip();
    });

    this.start();
  }

  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);

    this.vpX = this.width * 0.5;
    this.vpY = this.height * 0.42;
  }

  start() {
    this.isSkipped = false;
    this.startTime = performance.now();
    this.container.style.display = 'block';
    this.container.style.opacity = '1';
    this.container.style.pointerEvents = 'auto';

    if (this.animId) cancelAnimationFrame(this.animId);
    this.animate(performance.now());
  }

  skip() {
    if (this.isSkipped) return;
    this.isSkipped = true;
    this.finishTransition();
  }

  finishTransition() {
    if (this.animId) cancelAnimationFrame(this.animId);

    // Smooth frosted fade & zoom out
    this.container.style.transition = 'opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), filter 0.8s ease';
    this.container.style.opacity = '0';
    this.container.style.filter = 'blur(16px)';
    this.container.style.pointerEvents = 'none';

    setTimeout(() => {
      this.container.style.display = 'none';
      this.container.style.filter = 'none';
      if (this.onComplete) this.onComplete();
    }, 800);
  }

  animate(now) {
    if (this.isSkipped) return;

    const elapsed = now - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);

    // Easing curve: Slow initial acceleration -> explosive high-speed surge -> full screen engulfment
    // progress in [0, 1]
    this.render(progress);

    if (progress >= 1) {
      this.finishTransition();
    } else {
      this.animId = requestAnimationFrame((t) => this.animate(t));
    }
  }

  render(t) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // Camera height swoops down as ship approaches
    // t: 0 -> high perspective; t: 1 -> low water-level perspective
    const cameraHeightFactor = 1 - Math.pow(t, 2) * 0.65;
    const currentVpY = this.vpY + Math.pow(t, 2.5) * (this.height * 0.22);

    // 1. ATMOSPHERIC OCEAN HORIZON & SKY
    const skyGrad = ctx.createLinearGradient(0, 0, 0, currentVpY);
    skyGrad.addColorStop(0, '#E2E8F0');
    skyGrad.addColorStop(0.6, '#F1F5F9');
    skyGrad.addColorStop(1, '#FFFFFF');
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, this.width, currentVpY);

    // Horizon sunlight glow
    const sunGrad = ctx.createRadialGradient(this.vpX, currentVpY, 0, this.vpX, currentVpY, this.width * 0.4);
    sunGrad.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
    sunGrad.addColorStop(0.3, 'rgba(254, 243, 199, 0.4)');
    sunGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = sunGrad;
    ctx.fillRect(0, 0, this.width, currentVpY + 50);

    // Ocean Water Deep Gradient
    const oceanGrad = ctx.createLinearGradient(0, currentVpY, 0, this.height);
    oceanGrad.addColorStop(0, '#0F2B48');
    oceanGrad.addColorStop(0.35, '#0A1E34');
    oceanGrad.addColorStop(1, '#05111E');
    ctx.fillStyle = oceanGrad;
    ctx.fillRect(0, currentVpY, this.width, this.height - currentVpY);

    // 2. HIGH SPEED RADIAL WAKE LINES (Ocean rushing past camera)
    const wakeSpeed = 0.04 + Math.pow(t, 2) * 0.08;
    for (const line of this.speedLines) {
      line.z -= wakeSpeed;
      if (line.z <= 0.01) line.z += 1;

      // Perspective projection
      const depth = Math.max(line.z, 0.05);
      const startDist = (1 - depth) * (this.height - currentVpY);
      const y = currentVpY + startDist;
      const spread = (y - currentVpY) * 2.8;
      const x = this.vpX + Math.sin(line.angle) * spread;

      const endY = y + line.length * (1 - depth) * 1.8;
      const endX = x + Math.sin(line.angle) * line.length * 2.2;

      ctx.strokeStyle = `rgba(186, 230, 253, ${line.opacity * (1 - depth)})`;
      ctx.lineWidth = Math.max(1, (1 - depth) * 3.5);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(endX, endY);
      ctx.stroke();
    }

    // 3. PERSPECTIVE CARGO SHIP MODEL
    // Ship Scale accelerates non-linearly: starts small at horizon, explodes to engulf screen
    // Using exponential / power curve for dramatic visual breakthrough
    const scale = Math.pow(t, 2.8) * 18 + 0.12; // 0.12 -> 18.0 (Massive coverage)
    const shipY = currentVpY + Math.pow(t, 1.8) * (this.height - currentVpY) * 0.72;
    const shipX = this.vpX + Math.sin(t * 8) * (scale * 2.5); // Subtle hydrodynamic sway

    this.drawCargoShip(ctx, shipX, shipY, scale, t);

    // 4. WATER CHURN, BOW WAVES & SPRAY PARTICLES
    this.drawBowWaves(ctx, shipX, shipY, scale, t);

    // Spray particles flying towards viewer lens
    for (const p of this.particles) {
      p.z -= 0.025 + Math.pow(t, 2) * 0.06;
      if (p.z <= 0.01) {
        p.z += 1;
        p.x = (Math.random() - 0.5) * 800;
        p.y = Math.random() * 300;
      }
      const invZ = 1 - p.z;
      const px = this.vpX + (p.x * scale * 0.15) / p.z;
      const py = shipY + (p.y * scale * 0.12) / p.z;
      const pSize = Math.max(1, (p.size * invZ * scale * 0.25));

      ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha * invZ})`;
      ctx.beginPath();
      ctx.arc(px, py, pSize, 0, Math.PI * 2);
      ctx.fill();
    }

    // 5. SCREEN-ENGULFING HULL FLASH & FADE (Phase when ship covers entire screen)
    if (t > 0.75) {
      // Transition from dark steel hull wipe into luminous ivory white
      const wipeT = (t - 0.75) / 0.25; // 0 to 1
      
      // Dramatic Hull Steel Shadow expanding
      const alphaHull = Math.min(wipeT * 1.4, 1);
      ctx.fillStyle = `rgba(15, 23, 42, ${alphaHull * 0.85})`;
      ctx.fillRect(0, 0, this.width, this.height);

      // Flash into Alabaster/Ivory frosted glow as landing page approaches
      const alphaGlow = Math.max(0, (wipeT - 0.35) / 0.65);
      const bloomGrad = ctx.createRadialGradient(
        this.width * 0.5, this.height * 0.5, 0,
        this.width * 0.5, this.height * 0.5, this.width * 0.7
      );
      bloomGrad.addColorStop(0, `rgba(255, 255, 255, ${alphaGlow})`);
      bloomGrad.addColorStop(0.5, `rgba(248, 246, 240, ${alphaGlow * 0.9})`);
      bloomGrad.addColorStop(1, `rgba(235, 230, 220, ${alphaGlow * 0.8})`);
      ctx.fillStyle = bloomGrad;
      ctx.fillRect(0, 0, this.width, this.height);
    }
  }

  drawCargoShip(ctx, x, y, scale, t) {
    ctx.save();
    ctx.translate(x, y);

    // Subtle pitch and roll from dynamic sea slicing
    const roll = Math.sin(t * 12) * 0.02;
    ctx.rotate(roll);

    // Dimension base at scale = 1
    const w = 180 * scale;
    const h = 75 * scale;

    // 1. TOWERING BULBOUS BOW & HULL PLATES
    // As ship nears camera, we see it from low angle (bow looming upwards)
    const hullGrad = ctx.createLinearGradient(0, -h * 0.8, 0, h * 0.5);
    hullGrad.addColorStop(0, '#334155');   // Upper freeboard steel
    hullGrad.addColorStop(0.4, '#1E293B'); // Mid-hull shadow
    hullGrad.addColorStop(0.7, '#0F172A'); // Waterline
    hullGrad.addColorStop(1, '#881337');   // Red antifouling boot-topping below waterline

    // Massive cutting bow profile
    ctx.beginPath();
    ctx.moveTo(0, h * 0.45);            // Keel bulbous tip
    ctx.lineTo(-w * 0.38, -h * 0.35);   // Port flare
    ctx.lineTo(-w * 0.32, -h * 0.65);   // Port forecastle deck
    ctx.lineTo(w * 0.32, -h * 0.65);    // Starboard forecastle deck
    ctx.lineTo(w * 0.38, -h * 0.35);    // Starboard flare
    ctx.closePath();
    ctx.fillStyle = hullGrad;
    ctx.fill();

    // Sharp Bow Stem Line (Center Crease of the Ship's Prow)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
    ctx.lineWidth = Math.max(1, 2.5 * scale * 0.2);
    ctx.beginPath();
    ctx.moveTo(0, -h * 0.65);
    ctx.lineTo(0, h * 0.45);
    ctx.stroke();

    // Bulbous bow underwater sphere protrusion
    const bulbGrad = ctx.createRadialGradient(0, h * 0.35, 0, 0, h * 0.35, w * 0.16);
    bulbGrad.addColorStop(0, '#BE123C');
    bulbGrad.addColorStop(1, '#4C0519');
    ctx.fillStyle = bulbGrad;
    ctx.beginPath();
    ctx.ellipse(0, h * 0.35, w * 0.15, h * 0.18, 0, 0, Math.PI * 2);
    ctx.fill();

    // 2. MULTI-COLORED CONTAINER CARGO STACKS
    const containerRows = 5;
    const containerCols = 6;
    const blockW = (w * 0.58) / containerCols;
    const blockH = (h * 0.22);

    const colors = ['#0284C7', '#B91C1C', '#047857', '#D97706', '#475569', '#0369A1'];

    for (let r = 0; r < containerRows; r++) {
      const rowY = -h * 0.65 - (r + 1) * blockH;
      for (let c = 0; c < containerCols; c++) {
        const colX = -w * 0.29 + c * blockW;
        const colorIdx = (r * 3 + c * 5) % colors.length;

        ctx.fillStyle = colors[colorIdx];
        ctx.fillRect(colX + 1, rowY + 1, blockW - 2, blockH - 2);

        // Container corrugated ridges highlight
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.lineWidth = 1;
        ctx.strokeRect(colX + 1, rowY + 1, blockW - 2, blockH - 2);
      }
    }

    // 3. BRIDGE SUPERSTRUCTURE & MAST TOWER
    const bridgeY = -h * 0.65 - containerRows * blockH - h * 0.35;
    const bridgeW = w * 0.28;
    const bridgeH = h * 0.35;

    ctx.fillStyle = '#F8FAFC';
    ctx.fillRect(-bridgeW * 0.5, bridgeY, bridgeW, bridgeH);
    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 1;
    ctx.strokeRect(-bridgeW * 0.5, bridgeY, bridgeW, bridgeH);

    // Bridge Windows (Black ribbon)
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(-bridgeW * 0.45, bridgeY + bridgeH * 0.2, bridgeW * 0.9, bridgeH * 0.22);

    // Radar Mast & Rotating Scanner
    const mastTop = bridgeY - h * 0.25;
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = Math.max(1.5, 2 * scale * 0.15);
    ctx.beginPath();
    ctx.moveTo(0, bridgeY);
    ctx.lineTo(0, mastTop);
    ctx.stroke();

    // Radar Dish Scanner
    const radarSweep = Math.sin(t * 30) * 12 * scale * 0.2;
    ctx.fillStyle = '#0284C7';
    ctx.beginPath();
    ctx.ellipse(0, mastTop, Math.abs(radarSweep) + 2, 2.5, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  drawBowWaves(ctx, x, y, scale, t) {
    ctx.save();
    ctx.translate(x, y);

    const waveWidth = 240 * scale;
    const waveHeight = 60 * scale;

    // Left (Port) Bow Wave Curl
    const portGrad = ctx.createLinearGradient(-waveWidth * 0.8, waveHeight, 0, 0);
    portGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
    portGrad.addColorStop(0.7, 'rgba(224, 242, 254, 0.7)');
    portGrad.addColorStop(1, 'rgba(255, 255, 255, 0.95)');

    ctx.fillStyle = portGrad;
    ctx.beginPath();
    ctx.moveTo(0, waveHeight * 0.3);
    ctx.quadraticCurveTo(-waveWidth * 0.5, waveHeight * 0.4, -waveWidth, waveHeight);
    ctx.quadraticCurveTo(-waveWidth * 0.4, waveHeight * 0.1, 0, 0);
    ctx.closePath();
    ctx.fill();

    // Right (Starboard) Bow Wave Curl
    const starGrad = ctx.createLinearGradient(waveWidth * 0.8, waveHeight, 0, 0);
    starGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
    starGrad.addColorStop(0.7, 'rgba(224, 242, 254, 0.7)');
    starGrad.addColorStop(1, 'rgba(255, 255, 255, 0.95)');

    ctx.fillStyle = starGrad;
    ctx.beginPath();
    ctx.moveTo(0, waveHeight * 0.3);
    ctx.quadraticCurveTo(waveWidth * 0.5, waveHeight * 0.4, waveWidth, waveHeight);
    ctx.quadraticCurveTo(waveWidth * 0.4, waveHeight * 0.1, 0, 0);
    ctx.closePath();
    ctx.fill();

    // Roaring White Foam Crest at Prow
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.ellipse(0, waveHeight * 0.25, 30 * scale, 12 * scale, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }
}

window.CinematicIntro = CinematicIntro;
