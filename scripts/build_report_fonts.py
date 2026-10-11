"""One-time build of the static TTF fonts embedded in the PDF dossier.

Source: the open-licence (SIL OFL 1.1) Fontsource packages installed under web/node_modules.
  Inter (variable)           -> Regular 400, Medium 500, SemiBold 600
  JetBrains Mono (variable)  -> Regular 400, Medium 500
  Instrument Serif           -> Regular, Italic
Output: src/reporting/fonts/*.ttf (committed so report generation needs no Node install).
Requires: fonttools and brotli.
"""

import os
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NM = os.path.join(ROOT, "web", "node_modules")
OUT = os.path.join(ROOT, "src", "reporting", "fonts")
os.makedirs(OUT, exist_ok=True)


def instance(src: str, wght: int, name: str) -> None:
    f = TTFont(src)
    inst = instancer.instantiateVariableFont(f, {"wght": wght}, inplace=False)
    inst.flavor = None
    inst.save(os.path.join(OUT, name))
    print("wrote", name)


def convert(src: str, name: str) -> None:
    f = TTFont(src)
    f.flavor = None
    f.save(os.path.join(OUT, name))
    print("wrote", name)


inter = os.path.join(NM, "@fontsource-variable", "inter", "files", "inter-latin-wght-normal.woff2")
jb = os.path.join(NM, "@fontsource-variable", "jetbrains-mono", "files", "jetbrains-mono-latin-wght-normal.woff2")
serif = os.path.join(NM, "@fontsource", "instrument-serif", "files")
for w, n in ((400, "Inter-Regular.ttf"), (500, "Inter-Medium.ttf"), (600, "Inter-SemiBold.ttf")):
    instance(inter, w, n)
for w, n in ((400, "JetBrainsMono-Regular.ttf"), (500, "JetBrainsMono-Medium.ttf")):
    instance(jb, w, n)
convert(os.path.join(serif, "instrument-serif-latin-400-normal.woff"), "InstrumentSerif-Regular.ttf")
convert(os.path.join(serif, "instrument-serif-latin-400-italic.woff"), "InstrumentSerif-Italic.ttf")
