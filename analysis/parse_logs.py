"""Rebuild results.csv (scoring v3) and run metadata from the JSONL logs (H12).

Every attack / benign run writes ``logs/<domain>_eval_attacks_<group>[_disabled_X]/
<config>_<ts>.jsonl``.  This script turns those logs into:

    results/eval_attacks/group_<group>[_disabled_X]/<domain>/results.csv   (v3 columns)
    results/eval_attacks/group_<group>[_disabled_X]/<domain>/trials.jsonl  (rows + oracle details)
    results/eval_attacks/all_trials.csv     every trial of every run, with group/domain/suffix
    results/eval_attacks/runs.csv           one row per log file: header fields (git SHA,
                                            freeze tag, model, panel, temperature, seed, state mode)

By default the ``trial_complete`` rows written at run time are used
(the oracle ran on the same events).  ``--rescore`` re-runs the effects
oracle on the events with the payloads now on disk.

Usage::

    python -m analysis.parse_logs                 # every run under LOGS_DIR
    python -m analysis.parse_logs --group q235_div4 --domain cyberops
    python -m analysis.parse_logs --rescore
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from attacks.harness import RESULT_COLUMNS
from config import LOGS_DIR, RESULTS_DIR
from logging_utils.run_metadata import HEADER_FIELDS

DOMAINS = ("cyberops", "healthcare", "finance", "legal")
_DIR_RE = re.compile(r"^(cyberops|healthcare|finance|legal)_eval_attacks_(.+?)(_disabled_[A-Z0-9]+)?$")
# the run directory names the run (group carries the run tag, e.g. _persistent);
# the header's own group/config/domain are the same except for the tag
RUN_COLUMNS = ["log_file", "domain", "group", "suffix", "config"] + [
    k for k in HEADER_FIELDS if k not in ("domain", "group", "config")]


def discover_runs(logs_dir: Path = LOGS_DIR) -> list[tuple[str, str, str, Path]]:
    """(domain, group, suffix, dir) for every attack/benign log directory."""
    out = []
    if not logs_dir.exists():
        return out
    for d in sorted(logs_dir.iterdir()):
        m = _DIR_RE.match(d.name)
        if d.is_dir() and m and any(d.glob("*.jsonl")):
            out.append((m.group(1), m.group(2), m.group(3) or "", d))
    return out


def read_events(path: Path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def parse_run_dir(domain: str, group: str, suffix: str, log_dir: Path,
                  rescore: bool = False) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (result rows, trial detail rows, run header rows)."""
    rows: dict[tuple, dict] = {}
    details: dict[tuple, dict] = {}
    runs: list[dict] = []
    events_by_trial: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(log_dir.glob("*.jsonl")):
        for e in read_events(path):
            if e.get("action") == "run_header":
                runs.append({**{k: e.get(k) for k in HEADER_FIELDS}, "log_file": path.name,
                             "domain": domain, "group": group, "suffix": suffix})
                continue
            tid = e.get("trial_id")
            if tid:
                events_by_trial[tid].append(e)
            if e.get("action") == "trial_complete" and not rescore:
                key = (e.get("ap"), str(e.get("variant")), str(e.get("trial")), e.get("config"))
                row = {c: e.get(c, "") for c in RESULT_COLUMNS}
                row.update({"domain": domain, "group": group})
                rows[key] = row                      # last write wins (resumed runs)
                details[key] = {**row, "suffix": suffix, "details": e.get("details"),
                                "error": e.get("error"), "trial_id": tid}
    if rescore:
        from analysis.reevaluate_logs import OfflineHarness, _load_payloads, _parse_trial_id
        from attacks.effects import evaluate_benign, trial_costs
        from attacks.harness import load_payloads
        payloads = _load_payloads(domain)
        benign = load_payloads(domain, "benign_alerts.json") or load_payloads(domain, "benign_workflows.json")
        harnesses: dict[str, OfflineHarness] = {}
        for tid, events in events_by_trial.items():
            parsed = _parse_trial_id(tid)
            if parsed is None:
                if "_benign_" not in tid:
                    continue
                # <domain>_benign_v<scenario>_t<trial>_<config>
                parts = tid.split("_")
                ap, vid, config = "benign", parts[2], "_".join(parts[4:])
                trial_num = int(parts[3].lstrip("t"))
                variant_num = int(vid.lstrip("v"))
                payload = benign[variant_num - 1] if 0 < variant_num <= len(benign) else {}
            else:
                ap, vid, trial_num, config = parsed
                variant_num = int(vid.split("_v")[-1])
                payload = payloads.get((ap, vid)) or {}
            h = harnesses.setdefault(config, OfflineHarness(config=config, group=group, domain=domain))
            h.set_trial_events(events)
            if ap == "benign":
                v = evaluate_benign(payload, events)
                lo = {**v.as_dict(), **trial_costs(events)}
            else:
                h.evaluate_success(ap, payload, {})
                lo = h.last_outcome
            header = next((e for e in events if e.get("action") == "run_header"), {})
            key = (ap, str(variant_num), str(trial_num), config)
            row = {"domain": domain, "ap": ap, "variant": variant_num, "trial": trial_num,
                   "config": config, "group": group, "outcome": lo.get("outcome", ""),
                   "blocked_by": lo.get("blocked_by", ""),
                   "collateral_denials": int(lo.get("collateral_denials") or 0),
                   "task_completed": "" if lo.get("task_completed") is None else lo.get("task_completed"),
                   "latency_s": round(lo.get("span_s") or 0.0, 3),
                   "primary_tokens": int(lo.get("primary_tokens") or 0),
                   "validator_tokens": int(lo.get("validator_tokens") or 0),
                   "seed": header.get("seed", "")}
            rows[key] = row
            details[key] = {**row, "suffix": suffix, "details": lo.get("details"), "trial_id": tid}
    ordered = sorted(rows.values(), key=lambda r: (str(r["config"]), str(r["ap"]), int(r["variant"] or 0), int(r["trial"] or 0)))
    return ordered, list(details.values()), runs


def write_run(domain: str, group: str, suffix: str, rows: list[dict], details: list[dict],
              results_dir: Path = RESULTS_DIR) -> Path:
    out_dir = results_dir / "eval_attacks" / f"group_{group}{suffix}" / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(out_dir / "trials.jsonl", "w") as f:
        for d in details:
            f.write(json.dumps(d, default=str) + "\n")
    return out_dir / "results.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--group", default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--logs-dir", type=Path, default=LOGS_DIR)
    ap.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = ap.parse_args()

    all_rows: list[dict] = []
    all_runs: list[dict] = []
    for domain, group, suffix, d in discover_runs(args.logs_dir):
        if args.group and group != args.group:
            continue
        if args.domain and domain != args.domain:
            continue
        rows, details, runs = parse_run_dir(domain, group, suffix, d, rescore=args.rescore)
        if not rows:
            continue
        path = write_run(domain, group, suffix, rows, details, args.results_dir)
        print(f"[{group}{suffix}/{domain}] {len(rows)} trials -> {path}")
        all_rows.extend({**r, "suffix": suffix} for r in rows)
        all_runs.extend(runs)

    if all_rows:
        out = args.results_dir / "eval_attacks"
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "all_trials.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RESULT_COLUMNS + ["suffix"], extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
        with open(out / "runs.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RUN_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in all_runs:
                w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
        print(f"wrote {out / 'all_trials.csv'} ({len(all_rows)} rows) and runs.csv ({len(all_runs)} log files)")
    else:
        print("no runs found")


if __name__ == "__main__":
    main()
