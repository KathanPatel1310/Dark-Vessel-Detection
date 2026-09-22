"""Pillar 1: AIS Feature Engineering Module.
Extracts kinematic metrics, circular heading variances, trajectory curvature,
and transmission gap anomalies from AIS streams and historical outage logs.
"""

import math
from datetime import datetime
from typing import List, Optional
import numpy as np
from src.schemas.ais import AISObservation, AISGap
from src.schemas.features import AISFeatures
from src.geospatial.eez_checker import haversine_km

def compute_circular_heading_variance(headings_deg: List[float]) -> float:
    """
    Computes circular variance of directional headings (0 to 1).
    Var_circ = 1 - R, where R = sqrt(mean(cos(theta))^2 + mean(sin(theta))^2).
    A straight line course has variance ~0.0; erratic zig-zag has variance near 1.0.
    """
    if len(headings_deg) < 2:
        return 0.0
    rads = [math.radians(h) for h in headings_deg if 0.0 <= h <= 360.0]
    if not rads:
        return 0.0
    mean_cos = float(np.mean([math.cos(r) for r in rads]))
    mean_sin = float(np.mean([math.sin(r) for r in rads]))
    R = math.sqrt(mean_cos ** 2 + mean_sin ** 2)
    return round(float(1.0 - min(1.0, R)), 4)

def compute_trajectory_curvature(observations: List[AISObservation]) -> float:
    """
    Computes tortuosity / trajectory curvature:
    Curvature = Cumulative_Track_Length_km / Straight_Line_Endpoint_Displacement_km.
    Curvature = 1.0 indicates a perfectly direct transit. Higher values indicate search, loitering, or evasive maneuvering.
    """
    if len(observations) < 2:
        return 1.0
    cumulative_km = 0.0
    for i in range(len(observations) - 1):
        p1, p2 = observations[i], observations[i + 1]
        cumulative_km += haversine_km(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
    
    first, last = observations[0], observations[-1]
    endpoint_km = haversine_km(first.latitude, first.longitude, last.latitude, last.longitude)
    if endpoint_km <= 0.1:
        return round(max(1.0, cumulative_km / 0.1), 2)
    return round(cumulative_km / endpoint_km, 3)

def extract_ais_features(
    observations: List[AISObservation],
    gaps: Optional[List[AISGap]] = None,
    current_time: Optional[datetime] = None
) -> AISFeatures:
    """
    Computes comprehensive AIS behavioral and transmission integrity features.
    """
    if not observations:
        # Default features when vessel has no recent AIS (e.g. completely dark)
        gap_count = len(gaps) if gaps else 0
        longest_gap = max([g.duration_hours for g in gaps], default=0.0) if gaps else 0.0
        mean_gap = float(np.mean([g.duration_hours for g in gaps])) if (gaps and len(gaps) > 0) else 0.0
        current_gap = gaps[-1].duration_hours if (gaps and len(gaps) > 0) else 48.0
        return AISFeatures(
            mean_speed_knots=0.0,
            speed_variance=0.0,
            max_speed_knots=0.0,
            speed_acceleration_kph2=0.0,
            heading_variance=0.0,
            mean_turn_rate_deg_min=0.0,
            trajectory_curvature=1.0,
            total_distance_km=0.0,
            ais_gap_count_30d=gap_count,
            longest_ais_gap_hours=round(longest_gap, 1),
            mean_ais_gap_hours=round(mean_gap, 1),
            current_gap_duration_hours=round(current_gap, 1),
            loitering_duration_hours=0.0
        )

    # Sort observations chronologically
    sorted_obs = sorted(observations, key=lambda x: x.timestamp)
    speeds = [o.sog for o in sorted_obs]
    headings = [o.heading if (o.heading is not None and o.heading < 360) else o.cog for o in sorted_obs]

    mean_sog = float(np.mean(speeds))
    var_sog = float(np.var(speeds))
    max_sog = float(np.max(speeds))
    circ_var = compute_circular_heading_variance(headings)
    curvature = compute_trajectory_curvature(sorted_obs)

    # Cumulative distance
    total_dist = 0.0
    for i in range(len(sorted_obs) - 1):
        total_dist += haversine_km(sorted_obs[i].latitude, sorted_obs[i].longitude,
                                   sorted_obs[i+1].latitude, sorted_obs[i+1].longitude)

    # Turn rate (degrees per minute)
    turn_rates = []
    for i in range(len(sorted_obs) - 1):
        dt_minutes = (sorted_obs[i+1].timestamp - sorted_obs[i].timestamp).total_seconds() / 60.0
        if dt_minutes > 0.1:
            dh = abs(sorted_obs[i+1].cog - sorted_obs[i].cog)
            if dh > 180:
                dh = 360 - dh
            turn_rates.append(dh / dt_minutes)
    mean_turn = float(np.mean(turn_rates)) if turn_rates else 0.0

    # Loitering (duration with speed < 2.5 knots)
    loiter_hours = 0.0
    for i in range(len(sorted_obs) - 1):
        if sorted_obs[i].sog < 2.5:
            dt_h = (sorted_obs[i+1].timestamp - sorted_obs[i].timestamp).total_seconds() / 3600.0
            loiter_hours += max(0.0, dt_h)

    # Gap metrics
    gap_count = len(gaps) if gaps else 0
    longest_gap = max([g.duration_hours for g in gaps], default=0.0) if gaps else 0.0
    mean_gap = float(np.mean([g.duration_hours for g in gaps])) if (gaps and len(gaps) > 0) else 0.0

    current_gap = 0.0
    if current_time and sorted_obs:
        delta = (current_time - sorted_obs[-1].timestamp).total_seconds() / 3600.0
        current_gap = max(0.0, delta)
    elif gaps:
        current_gap = gaps[-1].duration_hours

    return AISFeatures(
        mean_speed_knots=round(mean_sog, 2),
        speed_variance=round(var_sog, 2),
        max_speed_knots=round(max_sog, 2),
        speed_acceleration_kph2=0.0,
        heading_variance=circ_var,
        mean_turn_rate_deg_min=round(mean_turn, 2),
        trajectory_curvature=curvature,
        total_distance_km=round(total_dist, 1),
        ais_gap_count_30d=gap_count,
        longest_ais_gap_hours=round(longest_gap, 1),
        mean_ais_gap_hours=round(mean_gap, 1),
        current_gap_duration_hours=round(current_gap, 1),
        loitering_duration_hours=round(loiter_hours, 2)
    )
