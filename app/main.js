/**
 * Main Application Controller
 * Handles glassmorphism interactive states, telemetry counters, and user triggers.
 */

document.addEventListener('DOMContentLoaded', () => {
  const mainPage = document.getElementById('main-page-wrapper');
  const btnReplayIntro = document.getElementById('btn-replay-intro');

  // Initialize Cinematic High-Speed Cargo Ship Entrance Sequence
  const cinematicIntro = new CinematicIntro('cinematic-intro-container', () => {
    // Reveal Landing Page smoothly once intro completes
    if (mainPage) {
      mainPage.classList.remove('page-reveal');
      void mainPage.offsetWidth; // Trigger reflow
      mainPage.classList.add('page-reveal');
    }
  });

  // Replay Intro Button
  if (btnReplayIntro) {
    btnReplayIntro.addEventListener('click', (e) => {
      e.stopPropagation();
      cinematicIntro.start();
    });
  }

  // Initialize Ocean & Vessel Physics
  const ocean = new OceanSimulation('ocean-canvas');

  // Split Stage Elements
  const splitStage = document.getElementById('split-stage');
  const btnToggleSplit = document.getElementById('btn-toggle-split');
  const btnInspectSAR = document.getElementById('btn-inspect-sar');
  const btnGenerateReport = document.getElementById('btn-generate-report');

  if (btnToggleSplit && splitStage) {
    btnToggleSplit.addEventListener('click', () => {
      splitStage.classList.toggle('layout-split');
      const isSplit = splitStage.classList.contains('layout-split');
      btnToggleSplit.innerHTML = `<span>🔄</span> Layout: ${isSplit ? 'Split View' : 'Full Stage'}`;
      
      // Re-measure ocean canvas after layout transition
      setTimeout(() => ocean.resize(), 200);
      setTimeout(() => ocean.resize(), 600);
      setTimeout(() => ocean.resize(), 1250);
      showToast(isSplit ? '📊 Shifted to Split Intelligence Mode' : '🌊 Expanded to Wide Stage');
    });
  }

  if (btnInspectSAR) {
    btnInspectSAR.addEventListener('click', () => {
      showToast('📡 Sentinel-1 SAR Chip: TCR +14.2 dB • Dual-Pol VV/VH Rendered');
    });
  }

  if (btnGenerateReport) {
    btnGenerateReport.addEventListener('click', () => {
      showToast('📄 Qwen 2.5 LoRA Bulletin: Zero Hallucination • Schema Compliant');
    });
  }

  // DOM Elements
  const telemetrySpeed = document.getElementById('telemetry-speed');
  const telemetryPitch = document.getElementById('telemetry-pitch');
  const telemetryState = document.getElementById('telemetry-state');
  const btnSurge = document.getElementById('btn-surge');
  const btnSpeed = document.getElementById('btn-speed-toggle');

  // Vessel Speed Toggle State
  let speedTier = 1;
  const speedTiers = [0.85, 1.6, 2.4];
  const speedLabels = ['1x', '2x', '3x'];

  // Global Telemetry Display Hook
  window.updateTelemetryDisplay = (data) => {
    if (telemetrySpeed) telemetrySpeed.textContent = `${data.speed} kts`;
    if (telemetryPitch) telemetryPitch.textContent = `${data.pitch}°`;
    if (telemetryState) telemetryState.textContent = data.seaState;
  };

  // Wave Surge Button
  if (btnSurge) {
    btnSurge.addEventListener('click', (e) => {
      e.stopPropagation();
      ocean.triggerSurge();
      showToast('🌊 Ocean Swell Perturbed: +3.5x Turbulence');
    });
  }

  // Speed Toggle Button
  if (btnSpeed) {
    btnSpeed.addEventListener('click', (e) => {
      e.stopPropagation();
      speedTier = (speedTier + 1) % speedTiers.length;
      ocean.setSpeed(speedTiers[speedTier]);
      btnSpeed.textContent = `⚡ Speed: ${speedLabels[speedTier]}`;
      showToast(`🚢 Vessel Engine: ${speedLabels[speedTier]}`);
    });
  }

  // Card Hover Sound Effect & Refraction Sheen
  const cards = document.querySelectorAll('.glass-panel');
  cards.forEach(card => {
    card.addEventListener('pointermove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });
  });

  // Listen to custom ripple event from canvas
  window.addEventListener('ocean-ripple', () => {
    const stageCard = document.querySelector('.stage-card');
    if (stageCard) {
      stageCard.style.borderColor = 'rgba(14, 165, 233, 0.7)';
      setTimeout(() => {
        stageCard.style.borderColor = 'var(--glass-border-crisp)';
      }, 350);
    }
  });

  // Simple Notification Toast
  function showToast(message) {
    let toast = document.getElementById('glass-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'glass-toast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.95);
        color: #0F172A;
        padding: 12px 22px;
        border-radius: 9999px;
        font-family: var(--font-sans);
        font-size: 0.88rem;
        font-weight: 600;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08);
        z-index: 9999;
        pointer-events: none;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        transform: translateY(20px);
        opacity: 0;
      `;
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.style.transform = 'translateY(0)';
    toast.style.opacity = '1';

    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
      toast.style.transform = 'translateY(20px)';
      toast.style.opacity = '0';
    }, 2400);
  }
});
