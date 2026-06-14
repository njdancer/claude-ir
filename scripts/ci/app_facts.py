#!/usr/bin/env python3
"""Parse captured Vitest + build logs into app facts for the PR comment.

Vitest's summary line looks like:
    Tests  42 passed (42)
  or, on failure:
    Tests  2 failed | 40 passed (42)

Build size: total bytes of app/build/client (client bundle the user ships).

Usage: python3 scripts/ci/app_facts.py <vitest.log> <build_dir> <out.json>
Tolerant: missing inputs yield nulls so the comment job never fails here.
"""

import json
import os
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
PASSED = re.compile(r"(\d+)\s+passed")
FAILED = re.compile(r"(\d+)\s+failed")


def parse_tests(log):
    if not os.path.exists(log):
        return {}
    passed = failed = None
    for raw in open(log, errors="replace"):
        line = ANSI.sub("", raw)
        if re.search(r"^\s*Tests\s", line):
            p = PASSED.search(line)
            f = FAILED.search(line)
            passed = int(p.group(1)) if p else passed
            failed = int(f.group(1)) if f else (0 if p else failed)
    return {"passed": passed, "failed": failed}


def dir_bytes(d):
    if not os.path.isdir(d):
        return None
    total = 0
    for root, _, files in os.walk(d):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return total


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: app_facts.py <vitest.log> <build_dir> <out.json>")
    vitest, build_dir, out = sys.argv[1:4]
    facts = {"tests": parse_tests(vitest), "client_bytes": dir_bytes(build_dir)}
    json.dump(facts, open(out, "w"), indent=1)
    print(f"app facts: {json.dumps(facts)}")


if __name__ == "__main__":
    main()
