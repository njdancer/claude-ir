# Autoresearch loop for board layout + routing

> Nick (2026-06-16): "take a look at Andrej Karpathy's autoresearch project and
> see if there's anything we might try to replicate here in terms of iteratively
> improving the board layout and routing. I'm happy to give you plenty of time
> to iterate. Also if it helps we can totally remap GPIO — I don't care what
> pins we use."

## What Karpathy's autoresearch is

[autoresearch](https://github.com/karpathy/autoresearch) (released 2026-03) is a
**ratchet loop** for autonomous ML research. Three-file contract:

| File | Owner | Role |
|------|-------|------|
| `prepare.py` | nobody (immutable) | data + the **single fitness metric** (`val_bpb`). Never edited, so every experiment is measured identically. |
| `train.py` | the agent | the ~630-line artifact under optimisation (model + training loop). The agent rewrites it freely. |
| `program.md` | the human | research directions, constraints, exact run commands, and the rule **"NEVER STOP — don't pause to ask the human."** |
| `results.tsv` | the harness | audit trail: commit, score, pass/fail, description. The agent reads it to inform the next hypothesis. |

The **loop**: read `program.md` + `results.tsv` → propose a hypothesis → edit
`train.py` → run a **fixed-budget** experiment → evaluate the one metric → **keep
the commit if it improved, else `git reset` it**. Unidirectional: experiments
either advance the artifact or vanish. The LLM is *both* the mutation operator
(proposes edits) *and* the selection pressure (decides what to try from history);
the harness only enforces the immutable metric + the budget. ~12 experiments/hr.

## The 1:1 mapping onto this board

We already had the **dumb** version of this (`pcb_search.py`: random `rng.choice`
over placement zones — an AutoML fixed parameter space). Autoresearch's lessons
upgrade it on two axes: a wider, *physically-meaningful* search space, and an
*intelligent, history-aware* mutation operator instead of a random sampler.

| autoresearch | here | artifact |
|--------------|------|----------|
| `prepare.py` (immutable metric) | the route+legality+score **oracle** | `pcb_experiment.py` runs `floorplan → gpio_remap → place_v2 → rip → route_fr → pour → DRC → pcb_score`. FreeRouting is the routability oracle (~12 s, deterministic), `pcb_score` the fitness, kicad-cli DRC the legality gate. **Edit only with care — it is the ruler.** |
| `train.py` (editable artifact) | the **candidate spec** = floorplan anchors **+ GPIO→pad assignment** | `pcb_floorplan.ANCHORS` + a GPIO map (`pcb_gpio_remap.py`). Nick opened up GPIO remap, which is the big new degree of freedom (below). |
| `program.md` (direction + protocol) | this note's **Protocol** section | goal, hard constraints, run commands, ratchet rule. |
| `results.tsv` | experiment log | `hardware/fab/experiments.jsonl` (gitignored; one line per candidate: tag, score, drc, unrouted, usb metrics, the spec). |
| the LLM (mutation + selection) | **the agent driving the loop** | reads the log + the routed board's *which-nets-are-unrouted/long*, reasons geometrically, proposes the next spec. This is the faithful replication — the agent IS the loop, exactly as autoresearch uses an external LLM to edit `train.py`. |
| keep-if-better ratchet | keep the best board aside, restore pristine otherwise | the driver keeps `/tmp/ar_best.kicad_pcb`; the working tree stays pristine until a winner is finalised through the normal ritual. |

## The new lever: GPIO remap (Nick unlocked it)

On a 2-layer board, routability is dominated by **which module pad each net
attaches to** — a signal whose module pad faces *away* from its peripheral zone
forces a crossing (this is exactly why the USB pair is stuck: IO18/IO19 are
hardware-fixed and face away from the USB-C). The ESP32-C3's GPIO matrix means
*almost every peripheral function can be assigned to almost any GPIO*, so we can
permute net→pad to make each signal exit the side facing its zone.

U3 (ESP32-C3-WROOM-02) pad map (from the netlist), classed by remappability:

| class | pads (GPIO) | nets | search role |
|-------|-------------|------|-------------|
| **free** | 3(IO4) 4(IO5) 5(IO6) 6(IO7) 10(IO10) 15(IO3) | USER_LED2, IR_TX, IR_RX, SDA, SCL, USER_LED1 | permute freely |
| **spare** | 11(IO20) 12(IO21) 17(IO1) 18(IO0) | SPARE_RX/TX/IO1/IO0 → J4 | permute (J4 just breaks out whatever lands here) |
| **strap** | 7(IO8) 16(IO2) | strap pull-ups | leave fixed (boot-level risk) |
| **fixed** | 1(3V3) 2(EN) 8(IO9/BOOT) 9/19(GND) 13(IO18/USB-) 14(IO19/USB+) | power / reset / boot / USB | never touch (USB is hardware) |

So 6 peripheral signals (and 4 spares) permute over 10 pads spread across all
four module edges. The placement re-seat (`pcb_place_v2`) is **net-driven**, so
it automatically re-clusters each peripheral's support parts (R13/R19, pull-ups,
RC) against the new pad — remap + re-place is self-consistent.

**Caveat — reflecting a remap into the sources of truth.** A GPIO remap is a real
schematic change (a different module pad wired to the peripheral) + a firmware
`build_flags` change. The *search* manipulates PCB net assignments in-container
(cheap routability probing); a *winning* remap is then reflected as: firmware
`-D *_PIN=` (trivial), schematic net reattach (KiCad GUI / Mac, or a validated
surgical script), netlist regen → CI parity. The search's job is to prove a
remap is worth that reflection before we spend it.

## Protocol (the "program.md")

**Goal.** Minimise `pcb_score` on a **2-layer** board subject to the hard gates
**0 DRC errors + 0 unrouted**, with a strong preference for **USB D± on F.Cu, 0
vias** (the SI win that motivated the whole U3-rotation thread). Beat the merged
baseline (USB-on-B.Cu 56 mm, score ~710).

**Hard constraints (never violated by a candidate).**
- 2 layers only (no 4-layer escape).
- Physics-fixed anchors stay put: antenna over a board edge (RF keepout clear),
  IR LED fan firing E, TSOP lens clear of the fan, USB-C on the edge by U3's USB
  pads.
- USB pads 13/14 (IO18/19) never remapped; strap/boot/power pads never remapped.

**Run commands.**
```bash
export JAVA25=/tmp/fr/jdk-25.0.3+9-jre/bin/java
export FREEROUTING_JAR=/tmp/fr/freerouting-2.2.4.jar
# one candidate (floorplan from pcb_floorplan.ANCHORS, optional gpio map json):
/usr/bin/python3.12 scripts/pcb_experiment.py --tag <name> [--gpio gpio.json]
# logs a line to hardware/fab/experiments.jsonl, keeps best at /tmp/ar_best.*
```

**Loop (the agent runs this, NEVER STOP mid-search).**
1. Read `experiments.jsonl` + the last routed board's unrouted/long nets.
2. Form a hypothesis: a placement nudge and/or a GPIO swap that removes a
   specific crossing (geometric reasoning, not random).
3. Edit the spec (ANCHORS and/or the gpio map), run `pcb_experiment.py`.
4. Ratchet: if score improved (and gates pass) keep it as the new base; else
   discard and try the next hypothesis.
5. Repeat until a candidate clears the gates with USB on F.Cu, or the space is
   demonstrably exhausted (then report the best + why).

**Finalise the winner** through the normal ritual (ldo_pour, silk, stamp,
`hardware_validate.py`, baseline refresh in `kicad/kicad:10.0.2`), render for a
human serviceability call, and write up the GPIO-remap reflection (firmware +
schematic) if the win needed one.
