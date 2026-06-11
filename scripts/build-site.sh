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
# kicad-cli omits PBR factors (spec default = full metal -> washed-out white
# in model-viewer); rewrite them
python3 scripts/fix_glb_materials.py "$OUT/hardware/pcb/board.glb"
# join primitives + draco-compress: 19 MB / 20k draw calls -> ~0.7 MB / ~200
# (--palette false keeps plain colored materials, verifiable without a GPU)
npx -y @gltf-transform/cli optimize "$OUT/hardware/pcb/board.glb"     "$OUT/hardware/pcb/board.glb" --compress draco --texture-compress false     --palette false
# interactive viewer page: 3D (model-viewer) + toggleable 2D layer stack.
# Asset URLs carry ?v=<commit> so browsers re-fetch after every deploy
# (board.glb is large and otherwise cache-sticky).
REV="$(git rev-parse --short HEAD)"
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
  <span>esp32-ir-remote rev 1.2 - drag to orbit, scroll to zoom
    <svg viewBox="0 0 24 24" width="15" height="15" style="vertical-align:-2px;margin-left:.6rem">
      <path fill="#D97757" d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z"/>
    </svg>
    <span style="color:#D97757">designed by Claude</span>
  </span>
  <a href="../../index.html">back to docs</a>
</header>
<model-viewer src="board.glb?v=__REV__" camera-controls auto-rotate auto-rotate-delay="1500"
  environment-image="neutral" tone-mapping="aces" exposure="1.15"
  shadow-intensity="0.8" shadow-softness="0.7"
  camera-orbit="20deg 65deg auto" min-camera-orbit="auto auto 5%">
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
  img.src = `layer-${file}.svg?v=__REV__`;
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
# stamp the commit into the cache-busting asset URLs
sed -i.bak "s/__REV__/$REV/g" "$OUT/hardware/pcb/viewer.html"
rm -f "$OUT/hardware/pcb/viewer.html.bak"

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
  .claude-badge { display: inline-flex; align-items: center; gap: .45rem;
           background: #faf3ee; border: 1px solid #ecd9cc; border-radius: 999px;
           padding: .25rem .8rem; font-size: .9rem; color: #b05730;
           margin: .2rem 0 .6rem; }
</style>
</head>
<body>
<h1>claude-ir</h1>
<p class="claude-badge">
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path fill="#D97757" d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z"/>
  </svg>
  designed end-to-end by <a href="https://claude.ai" style="color:inherit"><strong>Claude</strong></a>
</p>
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

<footer>Built from <code>$commit</code> on $built by GitHub Actions.<br>
Reverse engineering, schematic, PCB layout, firmware and these docs were
produced autonomously by <a href="https://claude.ai" style="color:#b05730">Claude</a>
(Anthropic), directed by Nick Dancer. Non-commercial hobby project; the spark
mark is an original homage to Claude's logo.</footer>
</body>
</html>
EOF

echo "Site built in $OUT/ ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"
