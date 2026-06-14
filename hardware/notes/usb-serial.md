# USB & serial (v2: native USB, no bridge)

> The v1 CH340C USB-UART bridge and its cross-coupled 2N7002 auto-reset
> circuit were **deleted** in the v2 ESP32-C3 redesign (see the v2 change set
> in [`ROADMAP.md`](../../ROADMAP.md)). The ESP32-C3 has a **native
> USB-Serial-JTAG** controller, so the console, firmware download, and reset/
> boot sequencing all run over the USB-C data lines directly — no bridge chip,
> no auto-reset FETs, no DTR/RTS links. `./scripts/flash.sh` and
> `./scripts/monitor.sh` talk straight to the C3 over USB-C.

## Data path

USB-C D+/D- connect straight to the C3's native USB pins: **D+ → IO19
(U3 pin 14)**, **D- → IO18 (U3 pin 13)**. CC1/CC2 each pull down through a
5.1 kΩ resistor (R1 on A5, R2 on B5) — standard UFP/sink config so a host
supplies VBUS. VBUS (A4/A9) feeds the input fuse F1 → +5 V rail → AMS1117 LDO.

## USB-C connector (J2) — assembly / DFM

J2 is the **XKB U262-16XN-4BVC11** (LCSC C393939), a 16-pin **SMD** Type-C
receptacle that also has through-board features. Three distinct kinds of
terminal, three different handling rules:

| Terminal | Qty | Pad type | Paste aperture | How it's soldered |
|----------|----:|----------|:--------------:|-------------------|
| Signal/power pads (A1…B12) | 12 | SMD (`F.Cu F.Mask F.Paste`) | yes | JLC machine paste + reflow |
| Shield legs `S1` (on GND) | 4 | plated THT (`*.Cu *.Mask`) | **no** | **hand-solder after assembly** |
| Locating pegs | 2 | non-plated `np_thru_hole` | no | mechanical only — not soldered |

**The four `S1` shield legs MUST be hand-soldered.** They bond the shell to
GND (EMI/ESD return) and are the primary mechanical anchor that takes cable
insertion/extraction loads — the loads that would otherwise fatigue and peel
the 12 small SMD pads. They are deliberately **not** on the paste layer: at
our JLCPCB tier there is no pin-in-paste / intrusive-reflow option, so giving
the stencil an aperture over a plated THT barrel would just smear paste
without forming a sound joint. No paste → JLC reflows the 12 SMD pads and
leaves the four GND legs bare → we hand-solder them (easy: all GND, generous
plated holes, lots of finger room). This is a post-assembly touch-up, not a
loose "hand-solder kit" part.

The two locating pegs are non-plated and need nothing — they only locate the
connector and resist lateral movement.

> **Order-time checklist:** confirm in the JLC preview that no solder paste is
> placed on the four J2 `S1` legs (it shouldn't be — the footprint has no
> `F.Paste` there), and remember to hand-solder those four GND legs after the
> board comes back. (3D-model note: the J2 STEP is the EasyEDA-derived C393939
> model on KiCad's native footprint — rotated 180° to face correctly; verify
> its offset visually.)
