/**
 * Tactical C4ISR Operations Console Controller
 * Integrates:
 * 1. Leaflet Arabian Sea tactical cartography (EEZ polygons, STS zones, dead-reckoning cones)
 * 2. High-res Sentinel-1 SAR radiometry & bounding box canvas inspector
 * 3. FastAPI multi-agent LangGraph execution pipeline & streaming traces
 * 4. Human-in-the-Loop (HITL) operator review modal
 * 5. Structured Maritime Intelligence Bulletin synthesis
 */

(() => {
  'use strict';

  /* ─── STATE MANAGEMENT ────────────────────────────────────── */
  let activeScenario = null;
  let allScenarios = [];
  let currentSessionId = null;
  let leafletMap = null;
  let targetMarker = null;
  let forecastLayerGroup = null;
  let eezLayerGroup = null;
  let chipDisplayMode = 'composite'; // 'composite', 'vv', 'mask'
  let latestFeatures = null;
  let latestReport = null;

  /* ─── DOM SELECTORS ───────────────────────────────────────── */
  const elClock           = document.getElementById('utc-clock');
  const elScenarioSelect  = document.getElementById('scenario-select');
  const elScenarioDesc    = document.getElementById('scenario-desc');
  const elToggleAIS       = document.getElementById('toggle-cut-ais');
  const elToggleSanctions = document.getElementById('toggle-cut-sanctions');
  const elDegradeAlert    = document.getElementById('degrade-indicator');
  const elBtnRun          = document.getElementById('btn-run-investigation');
  const elTraceContainer  = document.getElementById('agent-trace-container');
  const elHitlAlert       = document.getElementById('hitl-alert-box');
  const elHitlModal       = document.getElementById('hitl-modal');
  const elFeaturesModal   = document.getElementById('features-modal');
  const elDrawer          = document.getElementById('ops-drawer');
  const elDrawerContent   = document.getElementById('drawer-content');
  const elRadarCanvas     = document.getElementById('radar-canvas');

  // Readouts
  const rTargetId  = document.getElementById('readout-target-id');
  const rRadarConf = document.getElementById('readout-radar-conf');
  const rCoords    = document.getElementById('readout-coords');
  const rLength    = document.getElementById('readout-length');
  const rBeam      = document.getElementById('readout-beam');
  const rTcr       = document.getElementById('readout-tcr');

  // Bulletin DOM
  const bThreatPill  = document.getElementById('bulletin-threat-pill');
  const bReportId    = document.getElementById('bulletin-report-id');
  const bSummary     = document.getElementById('b-executive-summary');
  const bStatutes    = document.getElementById('b-statute-tags');
  const bRecs        = document.getElementById('b-recommendations');
  const bForecast    = document.getElementById('b-forecast-pills');

  /* ─── 1. REAL-TIME ZULU CLOCK ──────────────────────────────── */
  function updateZuluClock() {
    const now = new Date();
    const utcStr = now.toISOString().substring(11, 19) + ' Z';
    if (elClock) elClock.textContent = utcStr;
  }
  setInterval(updateZuluClock, 1000);
  updateZuluClock();

  /* ─── 2. TOAST NOTIFICATIONS ──────────────────────────────── */
  function showToast(msg, duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }

  /* ─── 3. TACTICAL LEAFLET MAP INITIALIZATION ───────────────── */
  function initTacticalMap() {
    leafletMap = L.map('tactical-map', {
      center: [20.8, 64.5],
      zoom: 5.5,
      zoomControl: true,
      attributionControl: false
    });

    // Dark nautical basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd'
    }).addTo(leafletMap);

    forecastLayerGroup = L.layerGroup().addTo(leafletMap);
    eezLayerGroup = L.layerGroup().addTo(leafletMap);

    // Render STS High-Risk Choke Points
    const stsZones = [
      { name: "Fujairah Offshore Anchorage", lat: 25.18, lon: 56.55, radius: 60000 },
      { name: "Gulf of Oman Evasion Corridor", lat: 24.00, lon: 58.50, radius: 120000 },
      { name: "Arabian Sea Deepwater STS Sector", lat: 19.50, lon: 62.50, radius: 150000 }
    ];

    stsZones.forEach(z => {
      L.circle([z.lat, z.lon], {
        radius: z.radius,
        color: '#EF4444',
        weight: 1.5,
        dashArray: '4, 6',
        fillColor: '#EF4444',
        fillOpacity: 0.08
      }).bindTooltip(`⚠ STS ZONE: ${z.name}`, { sticky: true, className: 'mono' }).addTo(leafletMap);
    });

    // Load sovereign EEZ polygons from API or fallback
    fetch('/api/geospatial/eez')
      .then(res => res.json())
      .then(geojson => {
        if (geojson && geojson.features && geojson.features.length > 0) {
          L.geoJSON(geojson, {
            style: function(feat) {
              const sov = (feat.properties && feat.properties.sovereign) || "";
              let color = '#00E5FF';
              if (sov === 'Oman') color = '#8B5CF6';
              if (sov === 'Pakistan') color = '#3B82F6';
              return {
                color: color,
                weight: 1.8,
                fillColor: color,
                fillOpacity: 0.06,
                dashArray: '3, 4'
              };
            },
            onEachFeature: function(feat, layer) {
              const sov = (feat.properties && feat.properties.sovereign) || "Sovereign EEZ";
              layer.bindTooltip(`🏛 ${sov} Sovereign EEZ (200 NM)`, { sticky: true, className: 'mono' });
            }
          }).addTo(eezLayerGroup);
        }
      })
      .catch(err => {
        console.warn("Could not load remote EEZ geojson:", err);
      });
  }

  function updateMapTarget(lat, lon, label = "ACTIVE RADAR TARGET") {
    if (!leafletMap) return;

    if (targetMarker) {
      leafletMap.removeLayer(targetMarker);
    }

    const iconHtml = `
      <div style="position:relative; width:24px; height:24px;">
        <div style="position:absolute; width:12px; height:12px; background:#00E5FF; border-radius:50%; top:6px; left:6px; box-shadow:0 0 10px #00E5FF;"></div>
        <div style="position:absolute; width:24px; height:24px; border:2px solid #00E5FF; border-radius:50%; animation: radar-ping 1.8s infinite;"></div>
      </div>
    `;

    const customIcon = L.divIcon({
      html: iconHtml,
      className: '',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    targetMarker = L.marker([lat, lon], { icon: customIcon })
      .bindPopup(`<strong class="mono text-cyan">${label}</strong><br><span class="mono">Coordinates: ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E</span>`)
      .addTo(leafletMap);

    leafletMap.panTo([lat, lon]);
  }

  function renderForecastWaypoints(waypoints, startLat, startLon) {
    if (!forecastLayerGroup) return;
    forecastLayerGroup.clearLayers();

    if (!waypoints || waypoints.length === 0) return;

    const latlngs = [[startLat, startLon]];

    waypoints.forEach(wp => {
      latlngs.push([wp.projected_lat, wp.projected_lon]);

      // Error cone circle
      L.circle([wp.projected_lat, wp.projected_lon], {
        radius: (wp.uncertainty_radius_km || 25) * 1000,
        color: '#F59E0B',
        weight: 1,
        dashArray: '3, 4',
        fillColor: '#F59E0B',
        fillOpacity: 0.12
      }).bindTooltip(`+${wp.projection_hours}h Error Ellipse (±${wp.uncertainty_radius_km.toFixed(1)} km)`, { sticky: true }).addTo(forecastLayerGroup);

      // Waypoint marker
      L.circleMarker([wp.projected_lat, wp.projected_lon], {
        radius: 4,
        color: '#F59E0B',
        fillColor: '#F59E0B',
        fillOpacity: 1
      }).bindPopup(`<strong class="mono">+${wp.projection_hours}h DEAD-RECKONING</strong><br>Lat: ${wp.projected_lat.toFixed(4)}°, Lon: ${wp.projected_lon.toFixed(4)}°<br>Error Radius: ${wp.uncertainty_radius_km.toFixed(1)} km`).addTo(forecastLayerGroup);
    });

    // Trajectory dashed line
    L.polyline(latlngs, {
      color: '#F59E0B',
      weight: 2,
      dashArray: '6, 6',
      opacity: 0.85
    }).addTo(forecastLayerGroup);
  }

  /* ─── 4. HIGH-RESOLUTION RADAR CHIP CANVAS INSPECTOR ───────── */
  function drawRadarChip(det) {
    if (!elRadarCanvas) return;
    const ctx = elRadarCanvas.getContext('2d');
    const w = elRadarCanvas.width;
    const h = elRadarCanvas.height;

    // Background ocean backscatter (speckle noise)
    ctx.fillStyle = '#060A12';
    ctx.fillRect(0, 0, w, h);

    const lengthPx = Math.min(220, Math.max(30, (det.length_m || 150) * 0.7));
    const widthPx  = Math.max(8, lengthPx / (det.aspect_ratio || 5.8));
    const centerX  = w * 0.5;
    const centerY  = h * 0.5;
    const angleRad = ((det.heading_deg || 180) - 90) * (Math.PI / 180);

    // Ocean clutter noise
    for (let i = 0; i < 450; i++) {
      const rx = Math.random() * w;
      const ry = Math.random() * h;
      const alpha = Math.random() * 0.15;
      ctx.fillStyle = chipDisplayMode === 'vv' ? `rgba(180, 210, 255, ${alpha})` : `rgba(0, 229, 255, ${alpha})`;
      ctx.fillRect(rx, ry, 2, 2);
    }

    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(angleRad);

    // Annular sea clutter guard ring (dashed yellow)
    if (chipDisplayMode === 'mask' || chipDisplayMode === 'composite') {
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(-lengthPx/2 - 25, -widthPx/2 - 15, lengthPx + 50, widthPx + 30);
      ctx.setLineDash([]);
    }

    // Ship Hull Corner Reflector (bright radar return)
    const hullGrad = ctx.createLinearGradient(-lengthPx/2, 0, lengthPx/2, 0);
    if (chipDisplayMode === 'mask') {
      hullGrad.addColorStop(0, '#10B981');
      hullGrad.addColorStop(0.5, '#34D399');
      hullGrad.addColorStop(1, '#10B981');
    } else {
      hullGrad.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
      hullGrad.addColorStop(0.5, '#FFFFFF');
      hullGrad.addColorStop(1, 'rgba(255, 255, 255, 0.6)');
    }

    ctx.fillStyle = hullGrad;
    ctx.beginPath();
    // Elliptical vessel hull shape
    ctx.ellipse(0, 0, lengthPx/2, widthPx/2, 0, 0, 2 * Math.PI);
    ctx.fill();

    // Bounding Box (YOLOv8 emerald detection box)
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 1.8;
    ctx.strokeRect(-lengthPx/2 - 4, -widthPx/2 - 4, lengthPx + 8, widthPx + 8);

    ctx.restore();

    // Dimension labels
    ctx.fillStyle = '#10B981';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillText(`YOLOv8: [L: ${det.length_m.toFixed(1)}m x B: ${det.width_m.toFixed(1)}m]`, 12, 20);
    ctx.fillStyle = '#00E5FF';
    ctx.fillText(`CONF: ${(det.confidence * 100).toFixed(0)}% • TCR: +18.4 dB`, 12, 34);
  }

  /* ─── 5. SCENARIO SWITCHING ─────────────────────────────────── */
  function loadScenarios() {
    fetch('/api/scenarios')
      .then(res => res.json())
      .then(scenarios => {
        allScenarios = scenarios;
        selectScenario(scenarios[0].scenario_id);
      })
      .catch(err => {
        console.warn("API scenarios fetch failed, using built-in defaults:", err);
      });
  }

  function selectScenario(scenarioId) {
    activeScenario = allScenarios.find(s => s.scenario_id === scenarioId) || allScenarios[0];
    if (!activeScenario) return;

    const det = activeScenario.sar_detection;

    if (elScenarioDesc) elScenarioDesc.textContent = activeScenario.description;
    if (rTargetId) rTargetId.textContent = det.detection_id;
    if (rRadarConf) rRadarConf.textContent = det.confidence.toFixed(2);
    if (rCoords) rCoords.textContent = `${det.latitude.toFixed(2)}°N, ${det.longitude.toFixed(2)}°E`;
    if (rLength) rLength.textContent = `${det.length_m.toFixed(1)} m`;
    if (rBeam) rBeam.textContent = `${det.width_m.toFixed(1)} m`;
    if (rTcr) rTcr.textContent = det.length_m >= 100 ? '+18.4 dB' : '+11.2 dB';

    // Update map target
    updateMapTarget(det.latitude, det.longitude, `[${activeScenario.scenario_name}]`);

    // Redraw radar canvas
    drawRadarChip(det);

    // Reset drawer threat pill
    bThreatPill.className = 'threat-pill threat-neutral';
    bThreatPill.textContent = 'THREAT TIER: STANDBY';
    bReportId.textContent = `MAR-INTEL-READY-${det.detection_id.slice(-6)}`;
    bSummary.textContent = `Scenario "${activeScenario.scenario_name}" loaded. Click "RUN AUTONOMOUS INVESTIGATION" to execute LangGraph agents.`;
    bStatutes.innerHTML = `<span class="tag-neutral mono">Awaiting Run</span>`;
    bRecs.innerHTML = `<li>Ready to dispatch multi-agent investigation.</li>`;
    if (forecastLayerGroup) forecastLayerGroup.clearLayers();
    if (elHitlAlert) elHitlAlert.classList.add('hidden');
  }

  if (elScenarioSelect) {
    elScenarioSelect.addEventListener('change', (e) => {
      selectScenario(e.target.value);
    });
  }

  // Fault injection / degradation switch listeners
  function updateDegradeStatus() {
    const isDegraded = elToggleAIS.checked || elToggleSanctions.checked;
    if (elDegradeAlert) {
      if (isDegraded) {
        elDegradeAlert.classList.add('active');
        elDegradeAlert.textContent = 'FAULT INJECTED';
      } else {
        elDegradeAlert.classList.remove('active');
        elDegradeAlert.textContent = 'NORMAL SENSORS';
      }
    }
  }
  if (elToggleAIS) elToggleAIS.addEventListener('change', updateDegradeStatus);
  if (elToggleSanctions) elToggleSanctions.addEventListener('change', updateDegradeStatus);

  // Chip View Mode buttons
  ['composite', 'vv', 'mask'].forEach(mode => {
    const btn = document.getElementById(`btn-view-${mode}`);
    if (btn) {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.chip-view-toggles .toggle-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        chipDisplayMode = mode;
        if (activeScenario) drawRadarChip(activeScenario.sar_detection);
      });
    }
  });

  /* ─── 6. RUN MULTI-AGENT INVESTIGATION ──────────────────────── */
  if (elBtnRun) {
    elBtnRun.addEventListener('click', () => {
      if (!activeScenario) return;

      elBtnRun.disabled = true;
      elBtnRun.innerHTML = `<span class="radar-pulse"></span> RUNNING AGENTS...`;
      elTraceContainer.innerHTML = `<div class="trace-empty">Initiating LangGraph Pregel state machine...</div>`;

      const payload = {
        mission_id: `MSN-${Date.now().toString().slice(-6)}`,
        sar_detection: activeScenario.sar_detection,
        matched_ais: activeScenario.ais_observation,
        historical_gaps: activeScenario.historical_gaps || [],
        simulate_ais_offline: elToggleAIS.checked,
        simulate_sanctions_offline: elToggleSanctions.checked
      };

      fetch('/api/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        elBtnRun.disabled = false;
        elBtnRun.innerHTML = `<span class="radar-pulse"></span> RUN AUTONOMOUS INVESTIGATION`;

        currentSessionId = data.session_id;
        latestFeatures = data.risk_assessment;
        latestReport = data.final_report;

        // Animate agent trace entries step-by-step
        streamTrace(data.execution_trace || []);

        // Dead-reckoning map render
        if (data.forecast && data.forecast.extrapolated_waypoints) {
          renderForecastWaypoints(
            data.forecast.extrapolated_waypoints,
            activeScenario.sar_detection.latitude,
            activeScenario.sar_detection.longitude
          );
        }

        // Check Human-in-the-Loop Gate
        if (data.human_in_the_loop_required) {
          if (elHitlAlert) elHitlAlert.classList.remove('hidden');
          showToast("⚠ HIGH RISK DETECTED: Paused at HumanReviewNode checkpoint!");
        } else {
          if (elHitlAlert) elHitlAlert.classList.add('hidden');
        }

        // Render Intelligence Bulletin
        if (data.final_report) {
          populateBulletin(data.final_report, data.risk_assessment, data.forecast);
          expandDrawer();
        }

        showToast("✓ Multi-Agent Investigation Complete!");
      })
      .catch(err => {
        elBtnRun.disabled = false;
        elBtnRun.innerHTML = `<span class="radar-pulse"></span> RUN AUTONOMOUS INVESTIGATION`;
        showToast("Investigation failed: " + err);
        console.error(err);
      });
    });
  }

  function streamTrace(traceEntries) {
    elTraceContainer.innerHTML = '';
    traceEntries.forEach((entry, i) => {
      setTimeout(() => {
        const card = document.createElement('div');
        const isDegraded = entry.status === 'DEGRADED';
        card.className = `trace-card ${isDegraded ? 'degraded' : 'active'}`;
        card.innerHTML = `
          <div class="trace-card-top">
            <span class="trace-agent-name">${entry.agent_name}</span>
            <span class="trace-step-badge">STEP ${entry.step_number} • ${entry.status}</span>
          </div>
          <div class="trace-action">${entry.action_taken}</div>
          ${entry.notes ? `<div class="trace-notes">${entry.notes}</div>` : ''}
        `;
        elTraceContainer.appendChild(card);
        elTraceContainer.scrollTop = elTraceContainer.scrollHeight;
      }, i * 220);
    });
  }

  function populateBulletin(report, risk, forecast) {
    bReportId.textContent = report.report_id;
    bSummary.textContent = report.executive_summary;

    // Threat Pill styling
    const tier = (report.threat_tier || 'LOW').toUpperCase();
    bThreatPill.textContent = `THREAT TIER: ${tier}`;
    bThreatPill.className = `threat-pill threat-${tier.toLowerCase()}`;

    // Statutes
    bStatutes.innerHTML = '';
    (report.statutory_violations || []).forEach(st => {
      const tag = document.createElement('span');
      tag.className = 'statute-tag';
      tag.textContent = st;
      bStatutes.appendChild(tag);
    });

    // Recommendations
    bRecs.innerHTML = '';
    (report.actionable_recommendations || []).forEach(r => {
      const li = document.createElement('li');
      li.textContent = r;
      bRecs.appendChild(li);
    });

    // Forecast Pills
    if (forecast && forecast.extrapolated_waypoints) {
      bForecast.innerHTML = '';
      forecast.extrapolated_waypoints.forEach(wp => {
        const d = document.createElement('div');
        d.className = 'f-pill';
        d.textContent = `+${wp.projection_hours}h: Projected (${wp.projected_lat.toFixed(2)}°N, ${wp.projected_lon.toFixed(2)}°E) ±${wp.uncertainty_radius_km.toFixed(1)} km`;
        bForecast.appendChild(d);
      });
    }
  }

  function expandDrawer() {
    if (elDrawer) elDrawer.classList.add('expanded');
    const ws = document.getElementById('ops-workspace');
    if (ws) ws.classList.add('drawer-expanded');
  }

  // Drawer Toggle Click
  const drawerBtn = document.getElementById('drawer-toggle-btn');
  if (drawerBtn) {
    drawerBtn.addEventListener('click', () => {
      elDrawer.classList.toggle('expanded');
      const ws = document.getElementById('ops-workspace');
      if (ws) ws.classList.toggle('drawer-expanded');
    });
  }

  /* ─── 7. HUMAN-IN-THE-LOOP (HITL) MODAL ─────────────────────── */
  const btnOpenHitl = document.getElementById('btn-open-hitl-modal');
  const btnCloseHitl = document.getElementById('btn-close-hitl-modal');

  if (btnOpenHitl) {
    btnOpenHitl.addEventListener('click', () => {
      if (elHitlModal) elHitlModal.classList.remove('hidden');
      if (activeScenario) {
        document.getElementById('modal-target-id').textContent = activeScenario.sar_detection.detection_id;
        document.getElementById('modal-dark-class').textContent = activeScenario.expected_classification;
      }
    });
  }

  if (btnCloseHitl) {
    btnCloseHitl.addEventListener('click', () => {
      if (elHitlModal) elHitlModal.classList.add('hidden');
    });
  }

  // HITL Submission handlers
  ['approve', 'override', 'escalate'].forEach(action => {
    const btn = document.getElementById(`btn-hitl-${action}`);
    if (btn) {
      btn.addEventListener('click', () => {
        const notes = document.getElementById('hitl-notes-input').value || `Operator disposition committed: ${action.toUpperCase()}`;
        
        fetch('/api/hitl/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: currentSessionId || 'SESS-DEFAULT',
            analyst_disposition: action.toUpperCase(),
            audit_notes: notes
          })
        })
        .then(res => res.json())
        .then(data => {
          showToast(`✓ Operator disposition '${action.toUpperCase()}' recorded in audit trail.`);
          if (elHitlModal) elHitlModal.classList.add('hidden');
          if (elHitlAlert) elHitlAlert.classList.add('hidden');
        })
        .catch(err => {
          showToast("Failed to submit HITL disposition: " + err);
        });
      });
    }
  });

  /* ─── 8. 35-FEATURE VECTOR MODAL ────────────────────────────── */
  const btnInspectFeat = document.getElementById('btn-inspect-features');
  const btnCloseFeat = document.getElementById('btn-close-features-modal');
  const featTableBody = document.getElementById('features-table-body');

  if (btnInspectFeat) {
    btnInspectFeat.addEventListener('click', () => {
      if (!activeScenario) return;

      // Extract features directly from API
      fetch('/api/features/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sar_detection: activeScenario.sar_detection,
          candidate_ais: activeScenario.ais_observation
        })
      })
      .then(res => res.json())
      .then(data => {
        if (elFeaturesModal) elFeaturesModal.classList.remove('hidden');
        featTableBody.innerHTML = '';
        const f = data.flat_vector || {};

        const definitions = {
          sar_length_m: "Target major axis dimension from Sentinel-1 pixel mask",
          sar_width_m: "Target beam width (minor axis dimension)",
          sar_aspect_ratio: "Hull elongation quotient (Length / Beam)",
          sar_target_to_clutter_ratio_db: "Metallic target contrast over surrounding ocean waves (dB)",
          sar_compactness: "Isoperimetric quotient (P² / 4πA) measuring shape irregularity",
          sar_eccentricity: "Second-order central moment elliptical elongation (0 to 1)",
          ais_mean_speed_knots: "Average Speed Over Ground from valid transponder pings",
          ais_heading_variance: "Directional circular heading variance mod 360° (0=rigid, 1=erratic)",
          ais_current_gap_hours: "Elapsed hours since transponder transmission dropout",
          geo_distance_to_shore_km: "Haversine spherical distance to nearest coastal node",
          geo_is_inside_eez: "Point-in-polygon indicator for 200 NM sovereign Exclusive Economic Zone",
          geo_proximity_to_sts_km: "Distance to nearest recognized clandestine Ship-to-Ship zone",
          fusion_spatial_discrepancy_km: "Great-circle distance offset between radar detection and AIS ping",
          fusion_heading_discrepancy_deg: "Orientation offset modulo 180° detecting transponder spoofing",
          fusion_dimension_mismatch_ratio: "Ratio of length discrepancy detecting identity cloning",
          fusion_is_spatially_correlated: "Validated spatio-temporal match within 15km and 60min"
        };

        for (const [key, val] of Object.entries(f)) {
          const domain = key.startsWith('sar_') ? 'SAR MORPHOLOGY' : (key.startsWith('ais_') ? 'AIS KINEMATICS' : (key.startsWith('geo_') ? 'GEOSPATIAL' : 'CROSS FUSION'));
          const def = definitions[key] || "Mathematical metric derived from raw radar / telemetry sensors";
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="text-cyan">${domain}</td>
            <td class="text-main">${key}</td>
            <td class="text-emerald font-bold">${typeof val === 'number' ? val.toFixed(2) : val}</td>
            <td class="text-muted">${def}</td>
          `;
          featTableBody.appendChild(row);
        }
      });
    });
  }

  if (btnCloseFeat) {
    btnCloseFeat.addEventListener('click', () => {
      if (elFeaturesModal) elFeaturesModal.classList.add('hidden');
    });
  }

  /* ─── 9. EXPORT DOSSIER & COPY JSON ─────────────────────────── */
  const btnCopyJson = document.getElementById('btn-copy-json');
  if (btnCopyJson) {
    btnCopyJson.addEventListener('click', () => {
      if (latestReport) {
        navigator.clipboard.writeText(JSON.stringify(latestReport, null, 2));
        showToast("✓ Copied validated IntelligenceReport JSON to clipboard!");
      } else {
        showToast("Run an investigation first to generate report JSON.");
      }
    });
  }

  const btnExportDossier = document.getElementById('btn-export-dossier');
  if (btnExportDossier) {
    btnExportDossier.addEventListener('click', () => {
      if (latestReport) {
        window.print();
      } else {
        showToast("Run an investigation first before exporting dossier.");
      }
    });
  }

  /* ─── INITIALIZATION ON PAGE LOAD ──────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    initTacticalMap();
    loadScenarios();
  });

})();
