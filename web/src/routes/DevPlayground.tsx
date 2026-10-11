import { useState } from 'react';
import { Sliders } from 'lucide-react';
import { MOTION_EASINGS, MOTION_DURATIONS } from '../motion/tokens';

export const DevPlayground = () => {
  const [activeTab, setActiveTab] = useState<'type' | 'motion'>('type');
  const [buttonPressed, setButtonPressed] = useState(false);
  const [toggleActive, setToggleActive] = useState(false);

  return (
    <div className="flex-1 bg-[#070B14] p-6 sm:p-12 text-slate-100 max-w-6xl mx-auto w-full font-sans">
      <div className="flex items-center justify-between pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase mb-1">
            <Sliders className="w-4 h-4" />
            <span>DESIGN SYSTEM QA & VERIFICATION</span>
          </div>
          <h1 className="text-3xl font-bold font-display text-white">
            Design Tokens & Motion Playground
          </h1>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg bg-[#0C1424] border border-slate-800">
          <button
            onClick={() => setActiveTab('type')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase ${
              activeTab === 'type' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40' : 'text-slate-400'
            }`}
          >
            Typography QA (/dev/type)
          </button>
          <button
            onClick={() => setActiveTab('motion')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase ${
              activeTab === 'motion' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40' : 'text-slate-400'
            }`}
          >
            Motion Dynamics (/dev/motion)
          </button>
        </div>
      </div>

      {activeTab === 'type' && (
        <div className="mt-8 space-y-8">
          {/* Display Font */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <span className="text-xs font-mono text-slate-500 uppercase block mb-2">
              Role: Display / Headlines • Face: Inter Tight 700 • Tracking: -0.04em
            </span>
            <h1 className="font-display text-5xl sm:text-6xl font-bold text-white tracking-tight leading-none">
              Autonomous Maritime Domain Awareness
            </h1>
          </section>

          {/* Accent Highlight Word */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <span className="text-xs font-mono text-slate-500 uppercase block mb-2">
              Role: Emotional Accent • Face: Instrument Serif Italic • Text Gradient + Underline
            </span>
            <div className="font-display text-4xl sm:text-5xl text-white">
              Seeing the <span className="accent-word">invisible</span> across international straits.
            </div>
          </section>

          {/* Stat Numbers */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <span className="text-xs font-mono text-slate-500 uppercase block mb-2">
              Role: Numerals & Gauges • Face: Space Grotesk 700 • Distinct Instrument Quality
            </span>
            <div className="flex gap-8 font-stat text-4xl sm:text-5xl font-bold text-cyan-400">
              <span>92.4%</span>
              <span className="text-amber-400">103,120</span>
              <span className="text-emerald-400">&lt; 0.8ms</span>
            </div>
          </section>

          {/* Monospace Telemetry */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <span className="text-xs font-mono text-slate-500 uppercase block mb-2">
              Role: Coordinates & Timestamps • Face: JetBrains Mono • Tabular Nums
            </span>
            <div className="font-mono text-sm text-cyan-300 space-y-1">
              <div>LAT: 21.3800° N | LON: 64.1800° E | UTC: 2026-09-20T12:00:00Z</div>
              <div>HASH: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</div>
            </div>
          </section>
        </div>
      )}

      {activeTab === 'motion' && (
        <div className="mt-8 space-y-8">
          {/* Easing Curves */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <h3 className="text-sm font-mono font-bold text-cyan-400 uppercase mb-4">
              EASING CURVES & TIMING TOKENS
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
                <span className="text-slate-400">easeOutExpo</span>
                <div className="text-[11px] text-cyan-300 mt-1">{MOTION_EASINGS.easeOutExpo}</div>
                <div className="text-[10px] text-slate-500 mt-1">Duration: {MOTION_DURATIONS.revealMs}ms</div>
              </div>
              <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
                <span className="text-slate-400">easeInOutQuart</span>
                <div className="text-[11px] text-cyan-300 mt-1">{MOTION_EASINGS.easeInOutQuart}</div>
                <div className="text-[10px] text-slate-500 mt-1">Duration: {MOTION_DURATIONS.sectionMs}ms</div>
              </div>
              <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
                <span className="text-slate-400">springSnappy</span>
                <div className="text-[11px] text-amber-300 mt-1">stiffness 400 / damping 30</div>
                <div className="text-[10px] text-slate-500 mt-1">Tactile Clicks: {MOTION_DURATIONS.microMs}ms</div>
              </div>
              <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
                <span className="text-slate-400">springSoft</span>
                <div className="text-[11px] text-emerald-300 mt-1">stiffness 170 / damping 26</div>
                <div className="text-[10px] text-slate-500 mt-1">UI Smooth: {MOTION_DURATIONS.uiMs}ms</div>
              </div>
            </div>
          </section>

          {/* Interactive Tactile Micro-Interactions */}
          <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
            <h3 className="text-sm font-mono font-bold text-cyan-400 uppercase mb-4">
              TACTILE MICRO-INTERACTION TESTS
            </h3>
            <div className="flex flex-wrap items-center gap-6">
              {/* Button */}
              <button
                onMouseDown={() => setButtonPressed(true)}
                onMouseUp={() => setButtonPressed(false)}
                className={`px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 text-slate-950 font-bold text-xs uppercase tracking-wider transition-all duration-150 ${
                  buttonPressed ? 'scale-95 shadow-[0_0_10px_#00E5FF]' : 'hover:scale-105 shadow-[0_0_20px_rgba(0,229,255,0.4)]'
                }`}
              >
                Pressable Action Button
              </button>

              {/* Toggle Switch */}
              <div
                onClick={() => setToggleActive(!toggleActive)}
                className={`w-14 h-7 rounded-full p-1 cursor-pointer transition-colors duration-300 flex items-center ${
                  toggleActive ? 'bg-cyan-500 justify-end' : 'bg-slate-800 justify-start'
                }`}
              >
                <div className="w-5 h-5 rounded-full bg-white shadow-md transform transition-transform" />
              </div>

              {/* Card Tilt Simulation */}
              <div className="p-4 rounded-xl glass-panel hover:-translate-y-1 hover:border-cyan-400 transition-all duration-300 cursor-pointer">
                <span className="text-xs font-mono text-cyan-300 font-bold">HOVERABLE GLASS CARD</span>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
