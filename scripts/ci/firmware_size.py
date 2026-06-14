#!/usr/bin/env python3
"""Parse a captured `pio run` log into firmware-size facts for the PR comment.

PlatformIO prints, per environment:
    Processing nodemcuv2 (platform: espressif8266; board: nodemcuv2; ...)
    ...
    RAM:   [====      ]  41.5% (used 34020 bytes from 81920 bytes)
    Flash: [===       ]  34.8% (used 363504 bytes from 1044464 bytes)

We associate each RAM/Flash line with the most recent "Processing <env>"
header and emit {env: {ram_used, ram_total, ram_pct, flash_used, ...}}.

Usage: python3 scripts/ci/firmware_size.py <pio.log> <out.json>
Tolerant by design: a log with no size lines yields {} so the comment job
never fails on a parsing miss.
"""

import json
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
ENV = re.compile(r"^Processing\s+(\S+)\s+\(")
MEM = re.compile(
    r"^(RAM|Flash):.*?([\d.]+)%\s+\(used\s+(\d+)\s+bytes\s+from\s+(\d+)\s+bytes\)"
)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: firmware_size.py <pio.log> <out.json>")
    log, out = sys.argv[1], sys.argv[2]
    envs = {}
    cur = None
    for raw in open(log, errors="replace"):
        line = ANSI.sub("", raw).rstrip()
        m = ENV.match(line)
        if m:
            cur = m.group(1)
            envs.setdefault(cur, {})
            continue
        m = MEM.match(line.strip())
        if m and cur:
            kind = "ram" if m.group(1) == "RAM" else "flash"
            envs[cur][f"{kind}_pct"] = float(m.group(2))
            envs[cur][f"{kind}_used"] = int(m.group(3))
            envs[cur][f"{kind}_total"] = int(m.group(4))
    json.dump({"envs": envs}, open(out, "w"), indent=1)
    print(f"firmware facts: {json.dumps(envs)}")


if __name__ == "__main__":
    main()
