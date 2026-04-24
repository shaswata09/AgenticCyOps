"""Adaptive (GCG-suffixed) InjecAgent sweep through AgenticCyOps.

Prerequisite: ``benchmarks/injecagent/adaptive/strings/<model_alias>/``
is populated by ``gcg_runner.py`` with per-case adversarial suffix
files.

This script:

  1.  Loads the representative 50-case subset.
  2.  For each source model that has GCG strings available, appends
      the per-case suffix onto the Attacker Instruction / Tool Response
      of the case.
  3.  Runs the suffixed case through our P1-P5 deterministic pipeline
      for every (domain, config) pair -- mirrors ``run_static.py``.
  4.  Writes ``results/injecagent/injecagent_adaptive_{model}_results.csv``
      + ``_summary.csv`` + appends rows to the master summary.

Transfer attack
===============

For GLM-4.7-FP8 we cannot run GCG natively (FP8 blocks gradients).
Instead we evaluate ``--transfer-from llama4`` / ``qwen235`` -- the
suffix strings generated against one model are applied to the GLM-4.7
inference path (which is the same P1-P5 middleware here, since the
middleware does not invoke the primary LLM).  The transfer ASR number
therefore measures whether the adversarial *text* still bypasses the
middleware when generated against a different model -- a meaningful
robustness signal for the defense stack.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from config import BASE_DIR

from benchmarks.injecagent.harness.trial_driver import (
    DefensePipeline, run_case,
)

ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "adaptive" / "representative_cases.json"
STRINGS_DIR = ROOT / "adaptive" / "strings"
RESULTS_DIR = BASE_DIR / "results" / "injecagent" / "adaptive"


def load_cases() -> list[dict]:
    with open(CASES_PATH) as f:
        return json.load(f)


def load_suffixes(model_alias: str) -> dict[str, dict]:
    """Return {ia_case_id: {best_string, best_loss, ...}}."""
    out: dict[str, dict] = {}
    mdir = STRINGS_DIR / model_alias
    if not mdir.exists():
        return out
    for p in sorted(mdir.glob("*.json")):
        with open(p) as f:
            d = json.load(f)
        if "best_string" in d:
            out[d["ia_case_id"]] = d
    return out


def apply_suffix(case: dict, suffix: str) -> dict:
    """Return a copy of ``case`` with the GCG suffix appended to the
    attacker instruction *inside* the tool response."""
    c = dict(case)
    ai = c.get("Attacker Instruction", "")
    ai_with_suffix = f"{ai} {suffix}"
    c["Attacker Instruction"] = ai_with_suffix

    tool_resp = c.get("Tool Response", "")
    # The template uses the literal attacker instruction; replace in-place so
    # P2-L3 / P5-L5 see the poisoned text + suffix as one blob.
    if ai and ai in tool_resp:
        c["Tool Response"] = tool_resp.replace(ai, ai_with_suffix)
    else:
        c["Tool Response"] = tool_resp + f"\n\n{suffix}"
    return c


# --------------------------------------------------------------------- #
#  Sweep
# --------------------------------------------------------------------- #


def run_sweep(source_model: str,
              domains: list[str],
              configs: list[str],
              embedding_model=None) -> tuple[list[dict], dict]:
    suffixes = load_suffixes(source_model)
    if not suffixes:
        raise SystemExit(
            f"No adversarial strings found for model '{source_model}' under "
            f"{STRINGS_DIR / source_model}.  Generate them first:\n"
            f"   python -m benchmarks.injecagent.adaptive.gcg_runner "
            f"--model {source_model}")

    print(f"Loaded {len(suffixes)} GCG suffixes for model={source_model}")

    cases = load_cases()
    cases_with_suffix = []
    for c in cases:
        cid = c["ia_case_id"]
        if cid not in suffixes:
            continue
        cases_with_suffix.append(apply_suffix(c, suffixes[cid]["best_string"]))
    print(f"Suffixed {len(cases_with_suffix)} of {len(cases)} cases")

    pipelines: dict[tuple[str, str], DefensePipeline] = {}
    for dom in domains:
        for cfg in configs:
            print(f"  building pipeline  {dom:10s}  {cfg}")
            pipelines[(dom, cfg)] = DefensePipeline(
                domain=dom, config=cfg, embedding_model=embedding_model)

    rows: list[dict] = []
    for i, case in enumerate(cases_with_suffix):
        for (dom, cfg), pipe in pipelines.items():
            for r in run_case(case, pipe):
                r["source_model"] = source_model
                r["ia_case_id"] = case["ia_case_id"]
                r["family"] = case.get("_family", "")
                r["attack_type"] = case.get("Attack Type", "")
                rows.append(r)
        if (i + 1) % 10 == 0:
            print(f"   {i+1}/{len(cases_with_suffix)} cases evaluated")

    # Summary
    bucket = defaultdict(lambda: {"n": 0, "s": 0})
    for r in rows:
        k = (r["domain"], r["config"])
        bucket[k]["n"] += 1
        if r["allowed"]:
            bucket[k]["s"] += 1
    summary = []
    for (dom, cfg), v in sorted(bucket.items()):
        asr = 100 * v["s"] / v["n"] if v["n"] else 0.0
        summary.append({"source_model": source_model, "domain": dom,
                        "config": cfg, "n": v["n"], "succeeded": v["s"],
                        "blocked": v["n"] - v["s"],
                        "asr_pct": round(asr, 2)})
    return rows, summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-model", required=True,
                    help="Which GCG-trained suffix set to use "
                         "(directory name under adaptive/strings/)")
    ap.add_argument("--domains", default="cyberops,healthcare,finance,legal")
    ap.add_argument("--configs", default="flat,acl_hardened,agenticcyops")
    ap.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    ap.add_argument("--embedding-model", type=str,
                    default="/storage/data/AgenticCyOps_Private/models/Qwen/Qwen3-Embedding-0.6B")
    args = ap.parse_args()

    emb = None
    if args.embedding_model:
        from sentence_transformers import SentenceTransformer
        emb = SentenceTransformer(args.embedding_model)

    rows, summary = run_sweep(
        source_model=args.source_model,
        domains=args.domains.split(","),
        configs=args.configs.split(","),
        embedding_model=emb,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    det_path = args.out_dir / f"injecagent_adaptive_{args.source_model}_results.csv"
    summ_path = args.out_dir / f"injecagent_adaptive_{args.source_model}_summary.csv"

    with open(det_path, "w", newline="") as f:
        fields = ["source_model", "ia_case_id", "family", "attack_type",
                  "domain", "config",
                  "attacker_tool_ia", "attacker_tool_orig",
                  "allowed", "mechanism", "stage", "reason"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    with open(summ_path, "w", newline="") as f:
        fields = ["source_model", "domain", "config", "n", "succeeded",
                  "blocked", "asr_pct"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(summary)

    print(f"\nwrote {det_path}  ({len(rows)} rows)")
    print(f"wrote {summ_path}  ({len(summary)} rows)")

    print(f"\n=== Adaptive ASR  (source_model={args.source_model}) ===")
    for r in summary:
        print(f"  {r['domain']:10s}  {r['config']:14s}  "
              f"ASR={r['asr_pct']:6.2f}%  ({r['succeeded']}/{r['n']})")


if __name__ == "__main__":
    main()
