"""Offline re-evaluator for Eval A attack logs.

Reuses the LIVE :meth:`AttackHarness.evaluate_success` so the offline
re-evaluation is guaranteed identical to what a fresh attack run would
produce. We feed pre-recorded events into the evaluator by monkey-
patching its ``_get_trial_events`` method per trial.

Usage::

    python -m analysis.reevaluate_logs --group A --domain cyberops
    python -m analysis.reevaluate_logs --group A --domain cyberops \\
                                       --suffix _reeval
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from config import BASE_DIR
from attacks.harness import AttackHarness


# --------------------------------------------------------------------- #
#  Data loading
# --------------------------------------------------------------------- #


def _load_logs(log_dir: Path) -> dict[str, list[dict]]:
    trials: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(log_dir.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                tid = e.get("trial_id")
                if tid:
                    trials[tid].append(e)
    return trials


def _load_payloads(domain: str) -> dict[tuple[str, str], dict]:
    out: dict[tuple, dict] = {}
    for ap_num in range(1, 16):
        name = f"ap{ap_num}"
        for glob in (f"{name}_variants.json", f"{name}_payloads.json"):
            p = BASE_DIR / "domains" / domain / "payloads" / glob
            if p.exists():
                with open(p) as f:
                    data = json.load(f)
                payloads = data if isinstance(data, list) else data.get("variants", [])
                for v in payloads:
                    vid = v.get("variant_id", "")
                    out[(name, vid)] = v
                break
    return out


def _parse_trial_id(tid: str) -> tuple[str, str, int, str] | None:
    """Return (ap, variant_id_full, trial_num, config) or None."""
    # Examples: cyberops_ap11_v3_t1_agenticcyops, cyberops_ap8_v2_t5_flat
    parts = tid.split("_")
    if len(parts) < 5:
        return None
    ap = parts[1]
    variant_tok = parts[2]
    vid_full = f"{ap}_{variant_tok}"
    try:
        trial_num = int(parts[3].lstrip("t"))
    except ValueError:
        trial_num = 0
    try:
        int(variant_tok.lstrip("v"))
    except ValueError:
        return None
    config = "_".join(parts[4:])
    return ap, vid_full, trial_num, config


# --------------------------------------------------------------------- #
#  Offline shim over AttackHarness
# --------------------------------------------------------------------- #


class OfflineHarness(AttackHarness):
    """AttackHarness variant that serves events from a pre-recorded dict."""

    def __init__(self, config: str, group: str, domain: str):
        # Intentionally skip parent __init__ -- we only need evaluator methods.
        self.config = config
        self.group = group
        self.domain = domain
        self.logger = None
        self._events_for_trial: list[dict] = []

    def set_trial_events(self, events: list[dict]) -> None:
        self._events_for_trial = events

    def _get_trial_events(self) -> list[dict]:  # override
        return self._events_for_trial


# --------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------- #


def reevaluate(group: str, domain: str, suffix: str = "") -> None:
    log_dir = BASE_DIR / "logs" / f"{domain}_eval_attacks_{group}"
    out_dir = BASE_DIR / "results" / "eval_attacks" / f"group_{group}" / domain
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading logs from {log_dir}")
    trials = _load_logs(log_dir)
    print(f"  -> {len(trials)} trial_ids")
    payloads = _load_payloads(domain)
    print(f"  -> {len(payloads)} (ap, variant) payloads")

    rows = []
    harnesses: dict[str, OfflineHarness] = {}
    for tid, events in sorted(trials.items()):
        parsed = _parse_trial_id(tid)
        if parsed is None:
            continue
        ap, vid, trial_num, config = parsed
        try:
            variant_num = int(vid.split("_v")[-1])
        except ValueError:
            continue

        payload = payloads.get((ap, vid))
        if payload is None:
            payload = next((p for k, p in payloads.items() if k[0] == ap), {})

        h = harnesses.setdefault(
            config, OfflineHarness(config=config, group=group, domain=domain))
        h.set_trial_events(events)
        try:
            succeeded, step, mechanism = h.evaluate_success(ap, payload, {})
        except Exception as exc:
            succeeded, step, mechanism = False, 0, f"evaluator_error:{exc.__class__.__name__}"

        rows.append({
            "Domain": domain, "AP": ap, "Variant": variant_num,
            "Trial": trial_num, "Config": config, "Group": group,
            "Succeeded": succeeded, "Step": step, "Mechanism": mechanism,
        })

    out_csv = out_dir / f"results{suffix}.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Domain", "AP", "Variant", "Trial",
                                          "Config", "Group", "Succeeded",
                                          "Step", "Mechanism"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv} ({len(rows)} rows)")

    # Per-AP summary (agenticcyops only)
    agg = defaultdict(lambda: {"total": 0, "succ": 0})
    for r in rows:
        if r["Config"] != "agenticcyops":
            continue
        k = r["AP"]
        agg[k]["total"] += 1
        if r["Succeeded"]:
            agg[k]["succ"] += 1

    print("\nPer-AP AgenticCyOps ASR (post-fix re-evaluation):")
    ap_order = [f"ap{i}" for i in range(1, 16)]
    total_s = 0; total_t = 0
    for ap in ap_order:
        a = agg.get(ap, {"total": 0, "succ": 0})
        asr = 100 * a["succ"] / a["total"] if a["total"] else 0
        total_s += a["succ"]; total_t += a["total"]
        print(f"  {ap}:  {a['succ']:>3}/{a['total']:<3}  ASR={asr:>5.1f}%")
    if total_t:
        print(f"  MEAN ASR across APs: {100*total_s/total_t:.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="A")
    ap.add_argument("--domain", default="cyberops")
    ap.add_argument("--suffix", default="",
                    help="Optional filename suffix (default: none, writes results.csv)")
    args = ap.parse_args()
    reevaluate(args.group, args.domain, args.suffix)


if __name__ == "__main__":
    main()
