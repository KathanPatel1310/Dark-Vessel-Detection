# UX Design System & Motion Specification: "Cyber-Maritime, Apple-Disciplined"

## 1. Dual-Soul Architecture
- **`/` Showcase**: A cinematic, buttery-smooth product film using Lenis smooth inertia, canvas progressive frame rendering (150 dual-pol Sentinel-1 frames), and masked typography reveals.
- **`/ops` Operations Center**: A dense, trustworthy, zero-scroll-jacking tactical console engineered for naval analysts and maritime patrol officers.

## 2. Color Palette Tokens
| Token | Hex Value | Semantic Purpose |
|---|---|---|
| `--bg-0` | `#070B14` | Deep oceanic void surface |
| `--bg-1` | `#0C1424` | Elevated glass card surface |
| `--bg-2` | `#111C33` | Panel borders and hover states |
| `--radar` | `#00E5FF` | Active radar sweep & target reticles |
| `--caution` | `#F59E0B` | Human-in-the-Loop checkpoints |
| `--interdiction` | `#EF4444` | High-risk evasion & sanctions matches |
| `--nominal` | `#22C55E` | Correlated transponders & system health |
| `--hypothesis` | `#A78BFA` | Synthetic simulation fixtures |

## 3. Typography Hierarchy
1. **Display / Headlines**: *Inter Tight* (700 weight, tracking -0.04em, line-height 0.95–1.05)
2. **Emotional Accent**: *Instrument Serif* italic (gradient fill cyan→white with single-pass underline sweep)
3. **UI & Forms**: *Inter* (400/500/600 weight)
4. **Telemetry & Timestamps**: *JetBrains Mono* (tabular numbers, uppercase tracking 0.12em)
5. **Numerals & Metrics**: *Space Grotesk* (bold instrument counters)

## 4. Motion Tokens
- `easeOutExpo`: `cubic-bezier(0.16, 1, 0.3, 1)` (element entrances)
- `easeInOutQuart`: `cubic-bezier(0.76, 0, 0.24, 1)` (section chapter transitions)
- `springSnappy`: `{ stiffness: 400, damping: 30 }` (button clicks & toggles)
- `springSoft`: `{ stiffness: 170, damping: 26 }` (floating cards & glass panels)
