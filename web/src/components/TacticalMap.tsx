import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { AISObservation, SARDetection, TrajectoryPoint } from '../lib/api';
import { fetchEEZGeoJSON } from '../lib/api';

interface Props {
  detection?: SARDetection;
  ais?: AISObservation | null;
  waypoints?: TrajectoryPoint[];
}

/** Leaflet map: EEZ polygons, SAR detection, AIS position, dead-reckoning track with uncertainty circles. */
export const TacticalMap = ({ detection, ais, waypoints }: Props) => {
  const elRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const dynamicRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!elRef.current || mapRef.current) return;
    const map = L.map(elRef.current, { center: [18, 66], zoom: 5, zoomControl: true, attributionControl: true });
    // Keyless OSM tiles, darkened with a CSS filter (see .dark-tiles in index.css).
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 10,
      className: 'dark-tiles',
    }).addTo(map);
    dynamicRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    fetchEEZGeoJSON()
      .then((gj) => {
        if (!mapRef.current) return;
        L.geoJSON(gj, {
          style: { color: '#00E5FF', weight: 1.2, fillColor: '#00E5FF', fillOpacity: 0.05, dashArray: '4 4' },
          onEachFeature: (f, layer) => {
            const p = f.properties ?? {};
            layer.bindTooltip(`${p.sovereign ?? 'Zone'} — ${p.zone_type ?? ''}`, { sticky: true });
          },
        }).addTo(map);
      })
      .catch(() => undefined);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const group = dynamicRef.current;
    if (!map || !group) return;
    group.clearLayers();
    const bounds: L.LatLngExpression[] = [];

    if (detection) {
      const p: L.LatLngTuple = [detection.latitude, detection.longitude];
      bounds.push(p);
      L.circleMarker(p, { radius: 8, color: '#EF4444', fillColor: '#EF4444', fillOpacity: 0.8, weight: 2 })
        .bindTooltip(`SAR ${detection.detection_id} · ${detection.length_m.toFixed(0)} m`)
        .addTo(group);
    }
    if (ais) {
      const p: L.LatLngTuple = [ais.latitude, ais.longitude];
      bounds.push(p);
      L.circleMarker(p, { radius: 6, color: '#22C55E', fillColor: '#22C55E', fillOpacity: 0.8, weight: 2 })
        .bindTooltip(`AIS ${ais.vessel_name ?? ais.mmsi}`)
        .addTo(group);
    }
    if (waypoints?.length) {
      const pts = waypoints.map((w) => [w.projected_lat, w.projected_lon] as L.LatLngTuple);
      if (detection) pts.unshift([detection.latitude, detection.longitude]);
      L.polyline(pts, { color: '#F59E0B', weight: 2, dashArray: '6 6' }).addTo(group);
      waypoints.forEach((w) => {
        const p: L.LatLngTuple = [w.projected_lat, w.projected_lon];
        bounds.push(p);
        L.circle(p, {
          radius: w.uncertainty_radius_km * 1000,
          color: '#F59E0B',
          weight: 1,
          fillColor: '#F59E0B',
          fillOpacity: 0.12,
        })
          .bindTooltip(`+${w.projection_hours} h · ±${w.uncertainty_radius_km.toFixed(1)} km`)
          .addTo(group);
      });
    }
    if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.4), { maxZoom: 8 });
  }, [detection, ais, waypoints]);

  // `isolate` keeps Leaflet's high z-index panes from covering dialogs and the navbar.
  return <div ref={elRef} className="isolate z-0 h-full w-full" role="application" aria-label="Tactical map" />;
};
