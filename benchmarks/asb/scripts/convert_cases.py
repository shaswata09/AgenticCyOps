"""Convert upstream ASB YAML configs/scenarios into per-case JSON.

Upstream layout (after ``ingest_upstream.sh`` runs)::

    benchmarks/asb/data/upstream/
    ├── config/                      # YAML matrices: scenario × attack × defense
    │   ├── DPI.yml, IPI.yml, MP.yml, PoT.yml, ...
    ├── data/                        # per-scenario test cases
    └── LICENSE / README

Output (consumed by ``run_static.py``)::

    benchmarks/asb/data/
    ├── tools.json                   # canonical tool catalogue
    ├── cases/
    │   ├── dpi.json                 # all DPI cases
    │   ├── ipi.json
    │   ├── mp.json                  # memory poisoning
    │   └── pot.json                 # plan-of-thought backdoor
    └── representative_cases.json    # 50-case stratified subset (optional)

Output schema (per case) -- intentionally aligned with InjecAgent's
``test_cases_*_base.json`` so both benchmarks share the same trial
driver shape::

    {
      "asb_case_id":          "dpi_e_commerce_0001",
      "scenario":             "e_commerce",
      "attack_type":          "DPI" | "IPI" | "MemoryPoisoning" | "PoT",
      "User Tool":            "<scenario>_<tool>",
      "User Instruction":     "<benign user task>",
      "Attacker Tools":       ["<scenario>_<malicious_tool>"],
      "Attacker Instruction": "<embedded attacker prompt>",
      "Tool Response":        "<observation seen by the agent>",
      "Tool Parameters":      "<JSON-serialised params for the user tool>",
      "_family":              "asb"
    }

The actual converter logic depends on the precise upstream YAML
schema, which we don't try to anticipate -- this stub will be filled
in once an upstream snapshot exists locally.  Running it without a
snapshot prints a clear hint and exits non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPSTREAM_DIR = DATA_DIR / "upstream"
CASES_DIR = DATA_DIR / "cases"
TOOLS_OUT = DATA_DIR / "tools.json"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert upstream ASB YAML/scenarios to per-case JSON.")
    ap.add_argument("--upstream-dir", type=Path, default=UPSTREAM_DIR)
    ap.add_argument("--out-dir", type=Path, default=DATA_DIR)
    args = ap.parse_args()

    if not args.upstream_dir.exists():
        print(
            f"[fail] No upstream snapshot found at {args.upstream_dir}.\n"
            "Run the ingest first:\n"
            "  ./benchmarks/asb/scripts/ingest_upstream.sh\n",
            file=sys.stderr)
        sys.exit(1)

    print(f"[convert] upstream={args.upstream_dir}  out={args.out_dir}")
    print(f"[convert] reading config/, data/ ...")

    # TODO -- implement once we have an upstream snapshot to inspect.
    # The conversion is mechanical: walk the upstream YAML matrices,
    # join them with the per-scenario user/attacker tasks in data/,
    # emit one JSON object per (scenario, attack_type, sample_idx) into
    # cases/{dpi,ipi,mp,pot}.json.  Tools registered into a single
    # tools.json with shape::
    #     [{"scenario": str, "tools": [{name, description, parameters,
    #                                    returns}]}]
    #
    # Schema-aligned with benchmarks/injecagent/data/test_cases_*.json
    # so the static driver can pick either with no code changes.

    print(
        "[stub] Converter body is intentionally unimplemented.\n"
        "       Steps to fill in (run after ingest_upstream.sh has\n"
        "       populated benchmarks/asb/data/upstream/):\n"
        "       1. Inspect upstream config/*.yml to determine the\n"
        "          attack-type matrix shape.\n"
        "       2. Inspect upstream data/ to find user-task JSON / YAML.\n"
        "       3. Map each (scenario, attack, sample) to the schema\n"
        "          documented at the top of this module.\n"
        "       4. Write tools.json + cases/{dpi,ipi,mp,pot}.json.\n"
        "       5. Optionally generate a 50-case stratified subset.\n",
        file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
