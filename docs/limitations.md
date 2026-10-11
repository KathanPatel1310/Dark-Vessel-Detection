# Limitations and Operational Sensor Boundaries

## 1. Truthfulness Over Spectacle
The DVD-MDA platform operates on strict evidential integrity. In maritime surveillance, over-claiming certainty produces severe operational and diplomatic liabilities.

### Key Truths:
1. **Radar Hull Detection ≠ Illicit Intent**: A synthetic aperture radar (SAR) target without concurrent AIS is an *unmatched radar contact*, not an unqualified "dark vessel". It may be an artisanal fishing boat legally exempt under SOLAS Chapter V Regulation 19, a terrestrial AIS blind spot, or a vessel experiencing satellite transponder latency.
2. **Synthetic vs. Empirical Datasets**: While the sanctions index parses real official OFAC SDN XML (1,540 vessels) and UN XML (23 vessels), and sovereign EEZ borders derive from official UNCLOS boundary treaties, several SAR-AIS paired benchmark chips are synthetic simulation fixtures designed to rigorously test edge-case agentic behavior.
3. **Rule-Based & Statistical Risk Scoring**: Evidential anomaly ratings combine deterministic mathematical features (Haversine spatial delta, heading circular variance, target-to-clutter ratio) rather than opaque black-box assumptions.

## 2. Sensor Boundaries
- **Sentinel-1 C-Band (5.405 GHz)**: Resolution is 10 meters/pixel. Small objects (&lt; 15 meters) near rough sea surface clutter cannot be reliably separated from wave crests.
- **Atmospheric Ducting & Azimuth Ambiguities**: Strong radar returns from high-dielectric structures on land or large ships can create ghost artifacts along the satellite track.
- **Human-in-the-Loop Mandate**: High-risk findings (anomaly score ≥ 0.70 or sanctions matches) trigger mandatory operator review before interdiction directives can be published.
