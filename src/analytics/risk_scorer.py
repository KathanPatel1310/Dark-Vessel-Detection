"""Baseline Analytics & Multi-Factor Maritime Risk Scorer.
Replaces naive binary heuristics with traceable, multi-dimensional evidential reasoning:
1. Probabilistic dark vessel classification (distinguishing small craft / coverage gaps from deliberate evasion)
2. Sanctions and regulatory risk rating
3. Sovereign EEZ threat level assessment
4. Kinematic dead-reckoning trajectory extrapolation (+6h, +12h, +24h) with error cones
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from src.schemas.features import EngineeredFeatures
from src.schemas.geospatial import GeoContext
from src.schemas.sanctions import SanctionsResult
from src.schemas.intelligence import (
    RiskAssessment,
    PredictiveForecast,
    TrajectoryPoint,
)

class MaritimeRiskScorer:
    """Computes quantitative risk scores and kinematic dead-reckoning predictions."""

    @staticmethod
    def evaluate_dark_vessel_probability(
        features: EngineeredFeatures,
        geo_context: GeoContext
    ) -> Tuple[float, str, List[str]]:
        """
        Calculates probability that absence of AIS represents deliberate illicit evasion.
        Returns: (probability, classification_tag, risk_factors)
        """
        risk_factors: List[str] = []
        sar = features.sar
        ais = features.ais
        fusion = features.fusion
        length = sar.length_m

        # Case 1: Correlated target with active AIS broadcast
        if fusion.is_spatially_correlated:
            return 0.05, "CORRELATED_BENIGN", ["Vessel transmitting valid AIS broadcasts."]

        # Case 2: Unmatched target - evaluate multi-source evidence
        prob = 0.50 # Neutral prior for unmatched radar target

        # Size factor (SOLAS Chapter V Regulation 19 threshold is 300 GT, approx 45-50m length)
        if length < 30.0:
            prob -= 0.35
            risk_factors.append(f"Small craft ({length:.1f}m) legally exempt from AIS under SOLAS.")
            if geo_context.distance_to_coast_km < 30.0:
                return round(max(0.05, prob), 2), "SMALL_CRAFT_EXEMPT", risk_factors
        elif length >= 100.0:
            prob += 0.30
            risk_factors.append(f"Commercial hull ({length:.1f}m) legally mandated to broadcast AIS under SOLAS V/19.")

        # Offshore / Deepwater factor
        if geo_context.distance_to_coast_km > 100.0:
            prob += 0.15
            risk_factors.append(f"Operating in deep international waters ({geo_context.distance_to_coast_km:.1f}km offshore).")

        # Proximity to designated STS transfer corridor
        if geo_context.distance_to_sts_zone_km and geo_context.distance_to_sts_zone_km < 80.0:
            prob += 0.15
            risk_factors.append(f"Within {geo_context.distance_to_sts_zone_km:.1f}km of {geo_context.nearest_sts_zone_name}.")

        # Prior historical gap patterns
        if ais and ais.current_gap_duration_hours >= 12.0:
            prob += 0.10
            risk_factors.append(f"Active AIS outage duration exceeds {ais.current_gap_duration_hours:.1f} hours.")

        prob = min(0.98, max(0.05, prob))
        tag = "DELIBERATE_DARK_EVASION" if prob >= 0.70 else ("AIS_SHADOW_ZONE" if prob >= 0.40 else "SMALL_CRAFT_EXEMPT")
        return round(prob, 2), tag, risk_factors

    @classmethod
    def compute_risk_assessment(
        cls,
        features: EngineeredFeatures,
        sanctions_result: SanctionsResult,
        geo_context: GeoContext
    ) -> RiskAssessment:
        """
        Unifies dark vessel classification, sanctions screening, and EEZ sovereignty threat.
        """
        dark_prob, dark_class, factors = cls.evaluate_dark_vessel_probability(features, geo_context)

        # Sanctions risk
        sanctions_level = "CLEAN"
        if sanctions_result.is_sanctioned:
            sanctions_level = "CRITICAL" if sanctions_result.overall_sanctions_risk == "CONFIRMED" else "HIGH"
            factors.append(f"Confirmed sanctions match against {sanctions_result.query_target} ({sanctions_result.screening_notes})")
        elif geo_context.distance_to_sts_zone_km and geo_context.distance_to_sts_zone_km < 50.0:
            sanctions_level = "ELEVATED"
            factors.append(f"Proximity to high-risk sanctions evasion STS zone: {geo_context.nearest_sts_zone_name}")

        # EEZ threat level
        eez_threat = "NONE"
        if geo_context.inside_eez:
            if dark_prob >= 0.70:
                eez_threat = "CRITICAL" if geo_context.eez_country == "India" else "HIGH"
                factors.append(f"Unidentified dark commercial vessel operating inside {geo_context.eez_country} sovereign EEZ.")
            else:
                eez_threat = "LOW"
        else:
            if geo_context.distance_to_eez_boundary_km < 30.0:
                eez_threat = "MODERATE"
                factors.append(f"Vessel within {geo_context.distance_to_eez_boundary_km:.1f}km of sovereign EEZ border.")

        # Composite anomaly score
        anomaly_score = round(0.5 * dark_prob + (0.35 if sanctions_result.is_sanctioned else 0.05) + (0.15 if geo_context.inside_eez else 0.0), 2)

        return RiskAssessment(
            dark_vessel_probability=dark_prob,
            dark_vessel_classification=dark_class,
            sanctions_risk_level=sanctions_level,
            eez_threat_level=eez_threat,
            overall_anomaly_score=min(1.0, anomaly_score),
            risk_factors=factors
        )

    @staticmethod
    def extrapolate_trajectory(
        lat: float,
        lon: float,
        speed_knots: float,
        heading_deg: float,
        start_time: Optional[datetime] = None,
        forecast_horizons_hours: List[float] = [6.0, 12.0, 24.0]
    ) -> PredictiveForecast:
        """
        Computes kinematic dead-reckoning trajectory extrapolation using spherical earth trigonometry.
        Generates expanding uncertainty cones representing speed jitter and ocean drift.
        """
        now = start_time or datetime.now(timezone.utc)
        waypoints: List[TrajectoryPoint] = []
        heading_rad = math.radians(heading_deg)
        speed_kmh = speed_knots * 1.852 # 1 knot = 1.852 km/h

        for hours in forecast_horizons_hours:
            dist_km = speed_kmh * hours
            # Spherical boundaries: clamp latitude to [-90.0, 90.0]
            dlat = (dist_km * math.cos(heading_rad)) / 111.12
            new_lat = max(-90.0, min(90.0, lat + dlat))
            cos_lat = math.cos(math.radians(new_lat))
            dlon = (dist_km * math.sin(heading_rad)) / (111.12 * max(0.01, cos_lat))
            # Longitude antimeridian wrapping to [-180.0, 180.0]
            wrapped_lon = ((lon + dlon + 180.0) % 360.0) - 180.0

            # Expanding error cone (assumes 1.5 km/h drift + 10% speed variance)
            uncertainty_km = round(dist_km * 0.12 + 1.5 * hours, 1)
            future_time = now + timedelta(hours=hours)

            waypoints.append(TrajectoryPoint(
                projection_hours=hours,
                projected_lat=round(new_lat, 3),
                projected_lon=round(wrapped_lon, 3),
                uncertainty_radius_km=uncertainty_km,
                projected_timestamp=future_time
            ))

        return PredictiveForecast(
            extrapolated_waypoints=waypoints,
            projected_eez_incursion=False,
            projected_eez_eta_hours=None,
            projected_activity="Deepwater transit along designated navigation corridor",
            forecast_confidence=0.82 if speed_knots > 5.0 else 0.55,
            methodology_notes=f"Kinematic dead-reckoning based on SOG {speed_knots:.1f} kts, heading {heading_deg:.1f} deg with 12% expanding variance cone."
        )
