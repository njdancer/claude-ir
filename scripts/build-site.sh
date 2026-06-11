#!/usr/bin/env bash

#
# build-site.sh - Build the static site published to GitHub Pages
#
# Exports board artifacts from the KiCad schematic (PDF, per-sheet SVGs,
# BOM CSV) and renders every tracked markdown doc to HTML, then writes an
# index.html linking it all. Runs locally (macOS, KiCad app bundle) and in
# CI (kicad/kicad docker image). Requires kicad-cli, pandoc, and git.
#
# Usage:
#   ./scripts/build-site.sh [output-dir]    # default: _site
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

OUT="${1:-_site}"
SCH="hardware/esp32-ir-remote.kicad_sch"

# --- Locate kicad-cli (same preference order as hardware-check.sh) --------
find_kicad_cli() {
    if [ -n "${KICAD_CLI:-}" ]; then
        echo "$KICAD_CLI"
        return
    fi
    local mac_cli="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if [ -x "$mac_cli" ]; then
        echo "$mac_cli"
        return
    fi
    if command -v kicad-cli >/dev/null 2>&1; then
        command -v kicad-cli
        return
    fi
}

KICAD_CLI_BIN="$(find_kicad_cli)"
if [ -z "$KICAD_CLI_BIN" ]; then
    echo "ERROR: kicad-cli not found (PATH, app bundle, or \$KICAD_CLI)" >&2
    exit 1
fi
command -v pandoc >/dev/null 2>&1 || { echo "ERROR: pandoc not found" >&2; exit 1; }

echo "kicad-cli: $KICAD_CLI_BIN ($("$KICAD_CLI_BIN" version))"
echo "pandoc:    $(pandoc --version | head -1)"

rm -rf "$OUT"
mkdir -p "$OUT/hardware/schematic-svg"

# --- KiCad exports ---------------------------------------------------------
echo "Exporting schematic PDF..."
"$KICAD_CLI_BIN" sch export pdf -o "$OUT/hardware/schematic.pdf" "$SCH"

echo "Exporting schematic SVGs..."
"$KICAD_CLI_BIN" sch export svg -o "$OUT/hardware/schematic-svg" "$SCH"

echo "Exporting BOM CSV..."
"$KICAD_CLI_BIN" sch export bom \
    -o "$OUT/hardware/bom.csv" \
    --fields 'Reference,Value,Footprint,LCSC,${QUANTITY}' \
    --labels 'Refs,Value,Footprint,LCSC,Qty' \
    --group-by 'Value,Footprint,LCSC' \
    "$SCH"

echo "Exporting PCB renders + 3D model..."
PCB="hardware/esp32-ir-remote.kicad_pcb"
mkdir -p "$OUT/hardware/pcb"
"$KICAD_CLI_BIN" pcb render --side top -w 1600 -h 1200 \
    -o "$OUT/hardware/pcb/board-top.png" "$PCB"
"$KICAD_CLI_BIN" pcb render --side bottom -w 1600 -h 1200 \
    -o "$OUT/hardware/pcb/board-bottom.png" "$PCB"
"$KICAD_CLI_BIN" pcb render --perspective --rotate ' -25,0,35' -w 1600 -h 1200 \
    -o "$OUT/hardware/pcb/board-iso.png" "$PCB"
"$KICAD_CLI_BIN" pcb export svg --layers F.Cu,B.Cu,Edge.Cuts,F.SilkS \
    --page-size-mode 2 -o "$OUT/hardware/pcb/board-copper.svg" "$PCB"
# Per-layer SVGs for the toggleable 2D stack viewer. --page-size-mode 2 crops
# every export to the same board area, so the stacked overlays align.
for LAYER in F.Cu B.Cu F.Silkscreen B.Silkscreen F.Mask B.Mask Edge.Cuts; do
    "$KICAD_CLI_BIN" pcb export svg --layers "$LAYER" --page-size-mode 2 \
        -o "$OUT/hardware/pcb/layer-${LAYER//./_}.svg" "$PCB"
done
# GLB (binary glTF) for the interactive viewer; full board detail
"$KICAD_CLI_BIN" pcb export glb --subst-models --include-tracks --include-zones \
    --include-pads --include-silkscreen --include-soldermask \
    -o "$OUT/hardware/pcb/board.glb" "$PCB" || echo "WARN: glb export failed"
# interactive viewer page: 3D (model-viewer) + toggleable 2D layer stack
cat > "$OUT/hardware/pcb/viewer.html" <<'VIEWER'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>esp32-ir-remote - interactive board viewer</title>
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
<style>
  body { margin:0; font-family: system-ui, sans-serif; background:#1c1f24; color:#eee; }
  header { padding:.6rem 1rem; background:#14161a; display:flex; justify-content:space-between; }
  header a { color:#8ecbff; text-decoration:none; }
  model-viewer { width:100vw; height:calc(100vh - 3rem); background:#1c1f24; }
  #layers2d { padding:1rem; }
  #layers2d .controls { margin-bottom:.8rem; display:flex; flex-wrap:wrap; gap:.9rem; }
  #layers2d label { cursor:pointer; user-select:none; }
  #layers2d label span { padding-left:.3rem; }
  #stack { position:relative; width:100%; max-width:1100px; background:#000;
           border:1px solid #333; }
  #stack img { position:absolute; inset:0; width:100%; height:auto;
               mix-blend-mode:screen; pointer-events:none; }
  #stack img:first-child { position:relative; }
  h2 { font-size:1.05rem; }
</style>
</head>
<body>
<header>
  <span>esp32-ir-remote rev 1.2 - drag to orbit, scroll to zoom</span>
  <a href="../../index.html">back to docs</a>
</header>
<model-viewer src="board.glb" camera-controls auto-rotate auto-rotate-delay="1500"
  shadow-intensity="0.6" exposure="1.1" camera-orbit="30deg 65deg auto" min-camera-orbit="auto auto 5%">
</model-viewer>
<section id="layers2d">
  <h2>2D layer stack (top view; toggle layers)</h2>
  <div class="controls" id="layerControls"></div>
  <div id="stack"></div>
</section>
<script>
const LAYERS = [
  ["Edge_Cuts",     "Edge.Cuts",     true],
  ["F_Cu",          "F.Cu",          true],
  ["B_Cu",          "B.Cu",          false],
  ["F_Silkscreen",  "F.Silkscreen",  true],
  ["B_Silkscreen",  "B.Silkscreen",  false],
  ["F_Mask",        "F.Mask",        false],
  ["B_Mask",        "B.Mask",        false],
];
const stack = document.getElementById("stack");
const controls = document.getElementById("layerControls");
for (const [file, name, on] of LAYERS) {
  const img = document.createElement("img");
  img.src = `layer-${file}.svg`;
  img.dataset.layer = file;
  img.style.visibility = on ? "" : "hidden";
  stack.appendChild(img);
  const label = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = on;
  cb.addEventListener("change", () =>
    { img.style.visibility = cb.checked ? "" : "hidden"; });
  const span = document.createElement("span");
  span.textContent = name;
  label.append(cb, span);
  controls.appendChild(label);
}
</script>
</body>
</html>
VIEWER

# --- Render markdown docs --------------------------------------------------
# Mirror repo paths under docs/ so relative links between docs keep working
# after the .md -> .html rewrite below.
echo "Rendering markdown docs..."
DOCS=$(git ls-files '*.md' | grep -v '^\.claude/')
for f in $DOCS; do
    outf="$OUT/docs/${f%.md}.html"
    mkdir -p "$(dirname "$outf")"
    pandoc -s --from gfm --to html5 \
        --metadata title="${f#./}" \
        -o "$outf" "$f"
    # Rewrite relative .md links to the rendered .html ([^":]* keeps
    # scheme-qualified URLs like https://... untouched)
    sed -E -i.bak 's|href="([^":]*)\.md(#[^"]*)?"|href="\1.html\2"|g' "$outf"
    rm -f "$outf.bak"
done

# --- index.html --------------------------------------------------------------
echo "Writing index.html..."

svg_links=""
for svg in "$OUT"/hardware/schematic-svg/*.svg; do
    name="$(basename "$svg")"
    svg_links+="<li><a href=\"hardware/schematic-svg/$name\">$name</a></li>"
done

doc_links=""
for f in $DOCS; do
    doc_links+="<li><a href=\"docs/${f%.md}.html\">$f</a></li>"
done

commit="$(git rev-parse --short HEAD)"
built="$(date -u +'%Y-%m-%d %H:%M UTC')"

cat > "$OUT/index.html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>claude-ir — ESP32 IR remote board</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 46rem;
         margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }
  h1 { border-bottom: 2px solid #ddd; padding-bottom: .3rem; }
  h2 { margin-top: 2rem; }
  li { margin: .2rem 0; }
  footer { margin-top: 3rem; color: #777; font-size: .85rem;
           border-top: 1px solid #ddd; padding-top: .5rem; }
  code { background: #f2f2f2; padding: 0 .25em; border-radius: 3px; }
</style>
</head>
<body>
<h1>claude-ir</h1>
<p>ESP32 smart controller for an ActronAir (Midea) air conditioner. The IR
protocol is fully reverse-engineered; the custom dev board is in design.
Source: <a href="https://github.com/njdancer/claude-ir">github.com/njdancer/claude-ir</a></p>

<h2>Board artifacts</h2>
<ul>
  <li><a href="hardware/schematic.pdf"><strong>Schematic (PDF)</strong></a></li>
  <li><a href="hardware/bom.csv">BOM (CSV, grouped, with LCSC part numbers)</a></li>
  <li>Schematic sheets (SVG):<ul>$svg_links</ul></li>
</ul>
<h2>PCB</h2>
<p><a href="hardware/pcb/viewer.html"><strong>Interactive 3D board viewer</strong></a>
 (drag/zoom, in-browser)</p>
<ul>
  <li><a href="hardware/pcb/board-iso.png">3D render - isometric</a></li>
  <li><a href="hardware/pcb/board-top.png">3D render - top</a></li>
  <li><a href="hardware/pcb/board-bottom.png">3D render - bottom</a></li>
  <li><a href="hardware/pcb/board-copper.svg">Copper + silkscreen (SVG)</a></li>
</ul>

<h2>Key documents</h2>
<ul>
  <li><a href="docs/ROADMAP.html">Roadmap</a> — project state and next actions</li>
  <li><a href="docs/specs/hardware-dev-board-v1.html">Hardware spec — dev board v1</a></li>
  <li><a href="docs/re-findings.html">IR protocol reverse-engineering findings</a></li>
  <li><a href="docs/hardware/notes/README.html">Hardware design notes</a> — per-subsystem rationale</li>
  <li><a href="docs/hardware/notes/datasheet-review-h1.4.html">Datasheet review (H1.4)</a></li>
</ul>

<h2>All documents</h2>
<ul>$doc_links</ul>

<footer>Built from <code>$commit</code> on $built by GitHub Actions.</footer>
</body>
</html>
EOF

echo "Site built in $OUT/ ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"
