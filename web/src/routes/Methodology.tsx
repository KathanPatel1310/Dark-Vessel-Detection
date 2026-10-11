import { BookOpen, AlertTriangle } from 'lucide-react';
import { ProvenanceChip } from '../components/ProvenanceChip';

export const Methodology = () => {
  return (
    <div className="flex-1 bg-[#070B14] p-6 sm:p-12 text-slate-100 max-w-5xl mx-auto w-full font-sans">
      <div className="pb-6 border-b border-slate-800">
        <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase mb-1">
          <BookOpen className="w-4 h-4" />
          <span>SCIENTIFIC & STATUTORY GROUNDING</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white">
          Methodology & Sensor Boundaries
        </h1>
        <p className="text-xs text-slate-400 mt-2 leading-relaxed">
          The Dark Vessel Detection system adheres to the principle of <em>truthfulness over spectacle</em>. Every output carries an explicit provenance tag and citation.
        </p>
      </div>

      <div className="mt-8 space-y-8 text-sm">
        {/* Section 1: Provenance Taxonomy */}
        <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
          <h2 className="text-lg font-bold font-display text-white mb-3">1. Provenance Taxonomy</h2>
          <p className="text-xs text-slate-300 leading-relaxed mb-4">
            To prevent operational hallucination and distinguish ground-truth empirical data from heuristics, every datum presented in our platform belongs to one of five explicit classifications:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-[#070B14] border border-emerald-500/30">
              <div className="flex items-center gap-2 mb-1">
                <ProvenanceChip provenance="REAL" />
              </div>
              <p className="text-xs text-slate-400">
                Empirical records parsed from official publications: U.S. OFAC SDN XML, UN Consolidated Sanctions, and sovereign EEZ treaties.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-[#070B14] border border-cyan-500/30">
              <div className="flex items-center gap-2 mb-1">
                <ProvenanceChip provenance="DERIVED" />
              </div>
              <p className="text-xs text-slate-400">
                Mathematically calculated through deterministic physics: Haversine distance, OpenCV PCA bounding boxes, and target-to-clutter ratios.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-[#070B14] border border-purple-500/30">
              <div className="flex items-center gap-2 mb-1">
                <ProvenanceChip provenance="SYNTHETIC" />
              </div>
              <p className="text-xs text-slate-400">
                Procedurally generated radar chip scenarios and simulated AIS gap tracks used to benchmark pipeline performance.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-[#070B14] border border-amber-500/30">
              <div className="flex items-center gap-2 mb-1">
                <ProvenanceChip provenance="HEURISTIC" />
              </div>
              <p className="text-xs text-slate-400">
                Probabilistic expert system classifications derived from SOLAS thresholds and spatial proximity gates.
              </p>
            </div>
          </div>
        </section>

        {/* Section 2: Statutory Conventions */}
        <section className="p-6 rounded-2xl bg-[#0C1424] border border-slate-800">
          <h2 className="text-lg font-bold font-display text-white mb-3">2. International Statutory Authorities</h2>
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
              <div className="text-cyan-400 font-bold">SOLAS CHAPTER V, REGULATION 19</div>
              <p className="text-xs text-slate-400 mt-1 font-sans">
                Mandates that all passenger ships, all cargo ships of 500 gross tonnage and upwards not on international voyages, and all ships of 300 gross tonnage and upwards on international voyages shall maintain continuous automatic identification systems (AIS). Vessels &lt;30m operating near coastlines are exempt.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
              <div className="text-cyan-400 font-bold">UNCLOS ARTICLE 73 (EEZ ENFORCEMENT)</div>
              <p className="text-xs text-slate-400 mt-1 font-sans">
                Affirms the sovereign coastal State's rights in its 200 nautical mile Exclusive Economic Zone (EEZ) to take enforcement measures, including boarding, inspection, arrest, and judicial proceedings.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-[#070B14] border border-slate-800">
              <div className="text-cyan-400 font-bold">UNCLOS ARTICLE 110 (RIGHT OF VISIT)</div>
              <p className="text-xs text-slate-400 mt-1 font-sans">
                Confers the authority upon commissioned naval warships to board foreign merchant vessels reasonably suspected of sailing without nationality or concealing identification.
              </p>
            </div>
          </div>
        </section>

        {/* Section 3: Limitations Statement */}
        <section className="p-6 rounded-2xl bg-amber-950/20 border border-amber-500/30 text-xs">
          <div className="flex items-center gap-2 text-amber-400 font-bold mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span>EXPLICIT LIMITATIONS & SENSOR BOUNDS</span>
          </div>
          <p className="text-slate-300 leading-relaxed">
            SAR radar detection detects electrical conductivity and physical surface roughness; it does <strong>not</strong> observe electronic transponder IDs or vessel flag states. Atmospheric ducting, azimuth ambiguous ghost returns, and sea clutter can cause false positives. The platform therefore outputs a <em>dark vessel hypothesis with confidence probability</em> and enforces Human-in-the-Loop review before operational interdiction.
          </p>
        </section>
      </div>
    </div>
  );
};
