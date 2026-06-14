#!/usr/bin/env bash

#
# hardware-check.sh - Run ERC and regenerate the netlist for the KiCad schematic
#
# Runs on the host (like flash.sh/monitor.sh) since KiCad lives there.
#
# Usage:
#   ./scripts/hardware-check.sh
#   KICAD_CLI=/path/to/kicad-cli ./scripts/hardware-check.sh   # Manual override
#
# After a schematic change, run this and commit the regenerated .net file
# alongside the schematic - the netlist diff is the reviewable record of
# what changed electrically.
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCH="$PROJECT_ROOT/hardware/esp32-ir-remote.kicad_sch"
NETLIST="$PROJECT_ROOT/hardware/esp32-ir-remote.net"
ERC_REPORT="$PROJECT_ROOT/hardware/erc-report.txt"

echo "============================================"
echo "KiCad Schematic Check"
echo "============================================"

# --- Locate kicad-cli ---------------------------------------------------
find_kicad_cli() {
    if [ -n "$KICAD_CLI" ]; then
        echo "$KICAD_CLI"
        return
    fi
    # Prefer the macOS app-bundle install: it ships the standard symbol/
    # footprint libraries with working library tables. A Homebrew kicad-cli
    # on PATH can shadow it but resolve libraries to a nonexistent
    # SharedSupport/symbols path, producing ~150 bogus lib_symbol_issues /
    # footprint_link_issues that drown out real ERC violations.
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
    echo -e "${RED}✗ kicad-cli not found${NC}"
    echo "  Looked in PATH and /Applications/KiCad/KiCad.app/Contents/MacOS/"
    echo "  Install KiCad 7+ or set KICAD_CLI=/path/to/kicad-cli"
    exit 1
fi

echo -e "${GREEN}✓ Using $KICAD_CLI_BIN${NC} ($("$KICAD_CLI_BIN" version))"

# --- Ensure global library tables ---------------------------------------
# Without the global sym/fp lib tables, headless ERC drowns in ~170 bogus
# lib_symbol_issues / footprint_link_issues ("configuration does not include
# library X"). The app GUI creates them on first run, but a CLI-only bench
# (or a freshly-upgraded KiCad with a new versioned config dir) has none.
# This mirrors CI's "Install KiCad global library tables" step. Idempotent.
ensure_lib_tables() {
    local ver cfg tpl
    ver="$("$KICAD_CLI_BIN" version 2>/dev/null | grep -oE '^[0-9]+\.[0-9]+')"
    [ -n "$ver" ] || return 0
    if [ "$(uname)" = "Darwin" ]; then
        cfg="$HOME/Library/Preferences/kicad/$ver"
    else
        cfg="${XDG_CONFIG_HOME:-$HOME/.config}/kicad/$ver"
    fi
    [ -f "$cfg/sym-lib-table" ] && [ -f "$cfg/fp-lib-table" ] && return 0
    for tpl in \
        "$(dirname "$KICAD_CLI_BIN")/../SharedSupport/template" \
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/template" \
        "/usr/share/kicad/template"; do
        if [ -f "$tpl/sym-lib-table" ]; then
            mkdir -p "$cfg"
            [ -f "$cfg/sym-lib-table" ] || cp "$tpl/sym-lib-table" "$cfg/"
            [ -f "$cfg/fp-lib-table" ] || cp "$tpl/fp-lib-table" "$cfg/"
            echo -e "${GREEN}✓ Installed global KiCad lib tables → ${cfg/#$HOME/~}${NC}"
            return 0
        fi
    done
}
ensure_lib_tables

# --- ERC -----------------------------------------------------------------
echo ""
echo "Running ERC..."
if "$KICAD_CLI_BIN" sch erc \
    --severity-error --severity-warning \
    --exit-code-violations \
    -o "$ERC_REPORT" \
    "$SCH"; then
    echo -e "${GREEN}✓ ERC passed${NC}"
else
    echo -e "${RED}✗ ERC violations found - see $ERC_REPORT${NC}"
    ERC_FAILED=1
fi

# --- Netlist export ------------------------------------------------------
echo ""
echo "Exporting netlist..."
"$KICAD_CLI_BIN" sch export netlist \
    --format kicadsexpr \
    -o "$NETLIST" \
    "$SCH"
echo -e "${GREEN}✓ Netlist written to ${NETLIST#$PROJECT_ROOT/}${NC}"

# --- Show what changed electrically --------------------------------------
echo ""
# -I ignores the (date ...) and (source ...) lines, which change on every
# export/machine without any electrical meaning
if git -C "$PROJECT_ROOT" diff --quiet -I'^\s*\((date|source) ' -- "$NETLIST" 2>/dev/null; then
    echo -e "${GREEN}✓ Netlist unchanged - no electrical changes${NC}"
else
    echo -e "${YELLOW}Netlist changed since last commit:${NC}"
    git -C "$PROJECT_ROOT" diff --stat -- "$NETLIST" || true
    echo "  Review with: git diff hardware/esp32-ir-remote.net"
fi

[ -z "$ERC_FAILED" ] || exit 1
