# Bundled report fonts

Static TTFs embedded in the PDF dossier, all under the SIL Open Font License 1.1:

| File | Family | Source |
|---|---|---|
| Inter-Regular / Medium / SemiBold.ttf | Inter (Rasmus Andersson) | `@fontsource-variable/inter`, instanced at wght 400 / 500 / 600 |
| JetBrainsMono-Regular / Medium.ttf | JetBrains Mono (JetBrains) | `@fontsource-variable/jetbrains-mono`, wght 400 / 500 |
| InstrumentSerif-Regular / Italic.ttf | Instrument Serif (Rodrigo Fuenzalida, Jordan Egstad) | `@fontsource/instrument-serif` |

Rebuild with `python scripts/build_report_fonts.py` (needs `fonttools` and `brotli`). These are Latin subsets,
so the renderer maps a few symbols (>=, pi, theta) to plain text.
