/**
 * Oceanic Wave & Vessel Physics Simulation
 * Multi-layer procedural sinusoidal fluid with interactive hydrodynamic ripples,
 * dynamic vessel pitching, and scroll-responsive turbulence.
 */

class OceanSimulation {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');

    this.width = 0;
    this.height = 0;
    this.dpr = window.devicePixelRatio || 1;

    // Simulation Clock & Parameters
    this.time = 0;
    this.baseSpeed = 0.018;
    this.scrollSpeedMultiplier = 1;
    this.targetScrollMultiplier = 1;

    // Ocean Base Level (fraction of canvas height)
    this.waterBaseY = 0.62;

    // Interactive Click Ripples Array
    this.ripples = [];

    // Particle Spray / Splash Effects
    this.particles = [];

    // Animated Patrol Vessel Physics State
    this.vessel = {
      x: 0,
      y: 0,
      width: 140,
      height: 48,
      speed: 0.85,
      pitch: 0,
      targetPitch: 0,
      buoyancyOffset: 0,
      radarAngle: 0,
      wakeTimer: 0
    };

    // Wave Layers Definition (Deep swell -> Midground -> Foreground crystalline)
    this.layers = [
      {
        frequency: 0.0035,
        amplitude: 24,
        speed: 0.8,
        offset: 0,
        colorTop: 'rgba(186, 218, 238, 0.45)',
        colorBot: 'rgba(215, 235, 248, 0.25)',
        foam: 'rgba(255, 255, 255, 0.3)',
        yShift: 0
      },
      {
        frequency: 0.006,
        amplitude: 18,
        speed: -1.2,
        offset: Math.PI / 3,
        colorTop: 'rgba(145, 195, 226, 0.55)',
        colorBot: 'rgba(180, 215, 240, 0.35)',
        foam: 'rgba(255, 255, 255, 0.5)',
        yShift: 10
      },
      {
        frequency: 0.009,
        amplitude: 14,
        speed: 1.6,
        offset: Math.PI / 1.5,
        colorTop: 'rgba(105, 175, 215, 0.68)',
        colorBot: 'rgba(150, 205, 235, 0.45)',
        foam: 'rgba(255, 255, 255, 0.75)',
        yShift: 22
      }
    ];

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());

    // Position Vessel initial
    this.vessel.x = this.width * 0.25;

    // Setup User Click Interaction
    this.canvas.addEventListener('pointerdown', (e) => this.handlePointerDown(e));

    // Setup Window Scroll Parallax / Wave modulation
    window.addEventListener('scroll', () => this.handleScroll(), { passive: true });

    // Start Simulation Loop
    this.animate();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;

    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);
  }

  handlePointerDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Add Hydrodynamic Ripple disturbance
    this.ripples.push({
      x: clickX,
      y: clickY,
      radius: 0,
      maxRadius: Math.max(this.width * 0.45, 300),
      amplitude: 28,
      decay: 0.965,
      frequency: 0.045
    });

    // Add Water Splash Particles
    for (let i = 0; i < 16; i++) {
      const angle = (Math.PI * 2 * i) / 16 + (Math.random() - 0.5);
      const velocity = 2 + Math.random() * 4.5;
      this.particles.push({
        x: clickX,
        y: clickY,
        vx: Math.cos(angle) * velocity,
        vy: Math.sin(angle) * velocity - 2.5,
        radius: 2 + Math.random() * 2.5,
        alpha: 0.9,
        gravity: 0.16
      });
    }

    // Trigger visual feedback event
    const event = new CustomEvent('ocean-ripple', { detail: { x: clickX, y: clickY } });
    window.dispatchEvent(event);
  }

  handleScroll() {
    const scrollY = window.scrollY;
    // Accelerate wave turbulence slightly on active scrolling
    this.targetScrollMultiplier = 1 + Math.min(scrollY * 0.003, 2.5);
  }

  calculateWaveHeight(x, layerIndex, time) {
    const layer = this.layers[layerIndex];
    const baseLine = this.height * this.waterBaseY + layer.yShift;

    // Harmonic sum
    let y = Math.sin(x * layer.frequency + time * layer.speed + layer.offset) * layer.amplitude;
    y += Math.cos(x * layer.frequency * 1.8 - time * 0.6) * (layer.amplitude * 0.35);

    // Apply active ripples
    for (const r of this.ripples) {
      const dist = Math.abs(x - r.x);
      const waveFront = r.radius;
      const distToFront = Math.abs(dist - waveFront);

      if (distToFront < 80) {
        const falloff = (1 - distToFront / 80) * (r.amplitude / 28);
        y += Math.sin((dist - waveFront) * r.frequency) * r.amplitude * falloff;
      }
    }

    return baseLine + y;
  }

  updatePhysics() {
    // Smooth scroll multiplier damping
    this.scrollSpeedMultiplier += (this.targetScrollMultiplier - this.scrollSpeedMultiplier) * 0.06;
    this.targetScrollMultiplier += (1 - this.targetScrollMultiplier) * 0.04;

    this.time += this.baseSpeed * this.scrollSpeedMultiplier;

    // Update ripples
    for (let i = this.ripples.length - 1; i >= 0; i--) {
      const r = this.ripples[i];
      r.radius += 4.5;
      r.amplitude *= r.decay;
      if (r.amplitude < 0.15 || r.radius > r.maxRadius) {
        this.ripples.splice(i, 1);
      }
    }

    // Update particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += p.gravity;
      p.alpha -= 0.025;
      if (p.alpha <= 0) {
        this.particles.splice(i, 1);
      }
    }

    // Update Vessel position & sailing cycle
    this.vessel.x += this.vessel.speed;
    if (this.vessel.x > this.width + 100) {
      this.vessel.x = -150;
    }

    // Sample wave surface heights at bow and stern
    const sternX = this.vessel.x - this.vessel.width * 0.42;
    const bowX = this.vessel.x + this.vessel.width * 0.42;

    const yMid = this.calculateWaveHeight(this.vessel.x, 1, this.time);
    const yStern = this.calculateWaveHeight(sternX, 1, this.time);
    const yBow = this.calculateWaveHeight(bowX, 1, this.time);

    // Dynamic pitch angle calculation: theta = atan2(dy, dx)
    const dx = bowX - sternX;
    const dy = yBow - yStern;
    this.vessel.targetPitch = Math.atan2(dy, dx) * 0.85;
    this.vessel.pitch += (this.vessel.targetPitch - this.vessel.pitch) * 0.12;

    // Smooth Buoyancy heave
    this.vessel.buoyancyOffset = Math.sin(this.time * 2.8) * 2.5;
    this.vessel.y = yMid + this.vessel.buoyancyOffset - 4;

    // Spin radar scanner
    this.vessel.radarAngle += 0.06;

    // Spawn subtle wake bubbles
    this.vessel.wakeTimer++;
    if (this.vessel.wakeTimer % 5 === 0) {
      this.particles.push({
        x: sternX + (Math.random() - 0.5) * 8,
        y: yStern + 8,
        vx: -1.5 - Math.random() * 1.2,
        vy: (Math.random() - 0.5) * 0.8,
        radius: 1.5 + Math.random() * 2,
        alpha: 0.65,
        gravity: -0.015
      });
    }

    // Broadcast live telemetry
    if (window.updateTelemetryDisplay) {
      window.updateTelemetryDisplay({
        speed: (12.4 + Math.sin(this.time) * 0.4).toFixed(1),
        pitch: (this.vessel.pitch * (180 / Math.PI)).toFixed(1),
        seaState: 'State 3 (Slight)',
        waveHeight: ((this.layers[1].amplitude * 2) / 20).toFixed(2)
      });
    }
  }

  drawWaveLayer(layerIndex) {
    const layer = this.layers[layerIndex];
    const step = 6; // Sampling resolution in pixels

    this.ctx.beginPath();
    this.ctx.moveTo(0, this.height);

    for (let x = 0; x <= this.width + step; x += step) {
      const y = this.calculateWaveHeight(x, layerIndex, this.time);
      if (x === 0) {
        this.ctx.lineTo(x, y);
      } else {
        this.ctx.lineTo(x, y);
      }
    }

    this.ctx.lineTo(this.width, this.height);
    this.ctx.closePath();

    // Wave Body Gradient
    const grad = this.ctx.createLinearGradient(0, this.height * 0.5, 0, this.height);
    grad.addColorStop(0, layer.colorTop);
    grad.addColorStop(1, layer.colorBot);
    this.ctx.fillStyle = grad;
    this.ctx.fill();

    // Crest Foam Sheen Line
    this.ctx.beginPath();
    for (let x = 0; x <= this.width + step; x += step) {
      const y = this.calculateWaveHeight(x, layerIndex, this.time);
      if (x === 0) this.ctx.moveTo(x, y);
      else this.ctx.lineTo(x, y);
    }
    this.ctx.strokeStyle = layer.foam;
    this.ctx.lineWidth = 2.2;
    this.ctx.stroke();
  }

  drawVessel() {
    this.ctx.save();
    this.ctx.translate(this.vessel.x, this.vessel.y);
    this.ctx.rotate(this.vessel.pitch);

    // Vessel Shadow on Water
    this.ctx.fillStyle = 'rgba(20, 45, 75, 0.15)';
    this.ctx.beginPath();
    this.ctx.ellipse(0, 14, 55, 8, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // Hull Gradient (Sleek Arctic White & Deep Navy Waterline)
    const hullGrad = this.ctx.createLinearGradient(0, -15, 0, 15);
    hullGrad.addColorStop(0, '#FFFFFF');
    hullGrad.addColorStop(0.65, '#EDE8DF');
    hullGrad.addColorStop(1, '#0F172A');

    // Draw Sleek Hull
    this.ctx.beginPath();
    this.ctx.moveTo(-55, 0); // Stern top
    this.ctx.lineTo(-48, 12); // Stern waterline
    this.ctx.lineTo(48, 12);  // Keel to bow
    this.ctx.lineTo(65, -4);  // Bulbous bow rake
    this.ctx.lineTo(50, -4);  // Foredeck
    this.ctx.lineTo(15, -4);  // Middeck
    this.ctx.lineTo(-55, -4); // Main deck
    this.ctx.closePath();
    this.ctx.fillStyle = hullGrad;
    this.ctx.fill();
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.95)';
    this.ctx.lineWidth = 1.2;
    this.ctx.stroke();

    // Blue Stripe on Hull (Maritime Emblem)
    this.ctx.beginPath();
    this.ctx.moveTo(-50, 4);
    this.ctx.lineTo(52, 4);
    this.ctx.strokeStyle = '#0284C7';
    this.ctx.lineWidth = 2.5;
    this.ctx.stroke();

    // Superstructure / Bridge Tower
    const bridgeGrad = this.ctx.createLinearGradient(0, -25, 0, -4);
    bridgeGrad.addColorStop(0, '#FFFFFF');
    bridgeGrad.addColorStop(1, '#F3EFE6');

    this.ctx.beginPath();
    this.ctx.moveTo(-25, -4);
    this.ctx.lineTo(-25, -20);
    this.ctx.lineTo(12, -20);
    this.ctx.lineTo(18, -4);
    this.ctx.closePath();
    this.ctx.fillStyle = bridgeGrad;
    this.ctx.fill();
    this.ctx.strokeStyle = 'rgba(200, 190, 175, 0.6)';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();

    // Bridge Windows (Tinted Cyan Glass)
    this.ctx.fillStyle = '#0F172A';
    this.ctx.fillRect(-18, -17, 8, 4);
    this.ctx.fillRect(-7, -17, 8, 4);
    this.ctx.fillRect(4, -17, 8, 4);

    // Mast & Radar Tower
    this.ctx.strokeStyle = '#334155';
    this.ctx.lineWidth = 1.8;
    this.ctx.beginPath();
    this.ctx.moveTo(-5, -20);
    this.ctx.lineTo(-5, -34);
    this.ctx.stroke();

    // Rotating Radar Scanner Dish
    const radarX = -5;
    const radarY = -34;
    const sweepWidth = Math.cos(this.vessel.radarAngle) * 8;

    this.ctx.fillStyle = '#0284C7';
    this.ctx.beginPath();
    this.ctx.ellipse(radarX, radarY, Math.abs(sweepWidth) + 1, 3, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // Radar Scanning Beam Arc (Pulsing Cyan)
    this.ctx.save();
    this.ctx.translate(radarX, radarY);
    this.ctx.rotate(this.vessel.radarAngle);
    const beamGrad = this.ctx.createRadialGradient(0, 0, 0, 0, 0, 38);
    beamGrad.addColorStop(0, 'rgba(14, 165, 233, 0.45)');
    beamGrad.addColorStop(1, 'rgba(14, 165, 233, 0)');
    this.ctx.fillStyle = beamGrad;
    this.ctx.beginPath();
    this.ctx.moveTo(0, 0);
    this.ctx.arc(0, 0, 38, -0.25, 0.25);
    this.ctx.closePath();
    this.ctx.fill();
    this.ctx.restore();

    this.ctx.restore();
  }

  drawParticles() {
    for (const p of this.particles) {
      this.ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  drawRipples() {
    for (const r of this.ripples) {
      const alpha = Math.max(0, (1 - r.radius / r.maxRadius) * 0.45);
      this.ctx.strokeStyle = `rgba(14, 165, 233, ${alpha})`;
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.ellipse(r.x, r.y, r.radius, r.radius * 0.35, 0, 0, Math.PI * 2);
      this.ctx.stroke();
    }
  }

  animate() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    this.updatePhysics();

    // Render Layer 0 (Back Swell)
    this.drawWaveLayer(0);

    // Render Layer 1 (Midground Swell)
    this.drawWaveLayer(1);

    // Render Animated Vessel between Midground and Foreground
    this.drawVessel();

    // Render Layer 2 (Foreground Crystalline Wave)
    this.drawWaveLayer(2);

    // Render Interactive Ripples & Particles
    this.drawRipples();
    this.drawParticles();

    requestAnimationFrame(() => this.animate());
  }

  // Public controls for user interaction
  triggerSurge() {
    this.targetScrollMultiplier = 3.5;
    this.ripples.push({
      x: this.width * 0.5,
      y: this.height * this.waterBaseY,
      radius: 0,
      maxRadius: this.width * 0.6,
      amplitude: 36,
      decay: 0.97,
      frequency: 0.038
    });
  }

  setSpeed(speedVal) {
    this.vessel.speed = speedVal;
  }
}

window.OceanSimulation = OceanSimulation;
