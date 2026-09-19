"""Offline re-scorer for attack-path logs (scoring v2).

Re-runs the LIVE evaluator (:meth:`AttackHarness.evaluate_success`) over the
JSONL audit logs of finished runs so ``results.csv`` can be regenerated
without re-running any LLM.  Events are served to the evaluator by
overriding ``_get_trial_events`` per trial, which guarantees the offline
verdict is identical to what a fresh attack run would produce.

Usage::

    python -m analysis.reevaluate_logs --group A --domain cyberops
    python -m analysis.reevaluate_logs --all                  # every group x domain on disk
    python -m analysis.reevaluate_logs --group A --domain cyberops --suffix-dir _disabled_P3
    python -m analysis.reevaluate_logs --all --dry-run        # report flips, write nothing

Outputs (per group x domain):

    results/eval_attacks/group_<G><suffix>/<domain>/results.csv
        Domain, AP, Variant, Trial, Config, Group, Succeeded, Step,
        Mechanism, Outcome, Measurable

    results/eval_attacks/rescoring_changelog.csv  (appended; one row per
        group x domain x config with the verdict flips relative to the
        results.csv that was on disk before the re-score)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from config import BASE_DIR
from attacks.harness import AttackHarness, RESULT_COLUMNS
from host.manifest_enforcer import ManifestEnforcer

DOMAINS = ("cyberops", "healthcare", "finance", "legal")
_LOG_DIR_RE = re.compile(r"^(cyberops|healthcare|finance|legal)_eval_attacks_([A-Z])(.*)$")


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
    """Return (ap, variant_id_full, trial_num, config) or None.

    Examples: ``cyberops_ap11_v3_t1_agenticcyops``, ``cyberops_ap8_v2_t5_flat``.
    """
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


def discover_runs() -> list[tuple[str, str, str]]:
    """Return every (group, domain, suffix) that has an attack log dir on disk."""
    runs = []
    for d in sorted((BASE_DIR / "logs").iterdir()):
        if not d.is_dir():
            continue
        m = _LOG_DIR_RE.match(d.name)
        if not m:
            continue
        domain, group, suffix = m.group(1), m.group(2), m.group(3)
        if suffix and not suffix.startswith("_disabled_"):
            continue
        if any(d.glob("*.jsonl")):
            runs.append((group, domain, suffix))
    return runs


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
        self.enforcer = ManifestEnforcer(domain=domain, logger=None)
        self.last_outcome = {}
        self._events_for_trial: list[dict] = []

    def set_trial_events(self, events: list[dict]) -> None:
        self._events_for_trial = events

    def _get_trial_events(self) -> list[dict]:  # override
        return self._events_for_trial


# --------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------- #


def _read_existing(csv_path: Path) -> dict[tuple, dict]:
    if not csv_path.exists():
        return {}
    out = {}
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r.get("AP"), str(r.get("Variant")), str(r.get("Trial")), r.get("Config"))
            out[key] = r
    return out


def reevaluate(group: str, domain: str, suffix: str = "",
               dry_run: bool = False, changelog: list[dict] | None = None) -> list[dict]:
    log_dir = BASE_DIR / "logs" / f"{domain}_eval_attacks_{group}{suffix}"
    out_dir = BASE_DIR / "results" / "eval_attacks" / f"group_{group}{suffix}" / domain
    out_csv = out_dir / "results.csv"

    print(f"[{group}/{domain}{suffix}] loading {log_dir}")
    trials = _load_logs(log_dir)
    payloads = _load_payloads(domain)
    print(f"  {len(trials)} trial_ids, {len(payloads)} (ap, variant) payloads")

    before = _read_existing(out_csv)

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
            outcome = h.last_outcome.get("outcome", "")
            measurable = h.last_outcome.get("measurable", True)
        except Exception as exc:
            succeeded, step = False, 0
            mechanism = f"evaluator_error:{exc.__class__.__name__}"
            outcome, measurable = "evaluator_error", False

        rows.append({
            "Domain": domain, "AP": ap, "Variant": variant_num,
            "Trial": trial_num, "Config": config, "Group": group,
            "Succeeded": succeeded, "Step": step, "Mechanism": mechanism,
            "Outcome": outcome, "Measurable": measurable,
        })

    # ---- changelog vs. what was on disk --------------------------------
    per_cfg: dict[str, dict] = defaultdict(lambda: {
        "n": 0, "legacy_succeeded": 0, "new_succeeded": 0,
        "flip_success_to_blocked": 0, "flip_blocked_to_success": 0,
        "not_measurable": 0, "error": 0, "agent_refused": 0, "blocked": 0,
    })
    for r in rows:
        c = per_cfg[r["Config"]]
        c["n"] += 1
        c["new_succeeded"] += int(r["Succeeded"])
        c["not_measurable"] += int(r["Outcome"] == "not_measurable")
        c["error"] += int(r["Outcome"] == "error")
        c["agent_refused"] += int(r["Outcome"] == "agent_refused")
        c["blocked"] += int(r["Outcome"] == "blocked")
        old = before.get((r["AP"], str(r["Variant"]), str(r["Trial"]), r["Config"]))
        if old is not None:
            old_s = str(old.get("Succeeded", "")).strip() == "True"
            c["legacy_succeeded"] += int(old_s)
            if old_s and not r["Succeeded"]:
                c["flip_success_to_blocked"] += 1
            if (not old_s) and r["Succeeded"]:
                c["flip_blocked_to_success"] += 1
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for cfg, c in sorted(per_cfg.items()):
        entry = {"timestamp": stamp, "group": group, "domain": domain,
                 "suffix": suffix, "config": cfg, **c}
        if changelog is not None:
            changelog.append(entry)
        print(f"  {cfg:<13} n={c['n']:<4} legacy_succ={c['legacy_succeeded']:<4} "
              f"new_succ={c['new_succeeded']:<4} s->b={c['flip_success_to_blocked']:<3} "
              f"b->s={c['flip_blocked_to_success']:<3} blocked={c['blocked']:<4} "
              f"refused={c['agent_refused']:<4} not_measurable={c['not_measurable']:<4} "
              f"error={c['error']}")

    if dry_run:
        print("  (dry-run: nothing written)")
        return rows

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {out_csv} ({len(rows)} rows)")

    # Per-AP summary (agenticcyops only, measurable trials only)
    agg = defaultdict(lambda: {"total": 0, "succ": 0, "nm": 0})
    for r in rows:
        if r["Config"] != "agenticcyops":
            continue
        a = agg[r["AP"]]
        if r["Outcome"] in ("not_measurable", "error"):
            a["nm"] += 1
            continue
        a["total"] += 1
        a["succ"] += int(r["Succeeded"])
    print("  Per-AP AgenticCyOps ASR (measurable trials):")
    for ap in [f"ap{i}" for i in range(1, 16)]:
        a = agg.get(ap)
        if not a:
            continue
        if a["total"] == 0:
            print(f"    {ap:<5} N/A (not measurable, {a['nm']} trials)")
        else:
            print(f"    {ap:<5} {a['succ']:>3}/{a['total']:<3} ASR={100*a['succ']/a['total']:5.1f}%"
                  + (f"  (+{a['nm']} not measurable)" if a["nm"] else ""))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--group", default=None, help="Single group letter, e.g. A")
    ap.add_argument("--domain", default=None,
                    help="cyberops | healthcare | finance | legal | all")
    ap.add_argument("--suffix-dir", default="",
                    help="Log/result dir suffix for ablation runs, e.g. _disabled_P3")
    ap.add_argument("--all", action="store_true",
                    help="Re-score every group x domain with logs on disk")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.all:
        runs = discover_runs()
    else:
        if not args.group:
            raise SystemExit("--group is required unless --all is given")
        domains = DOMAINS if (args.domain in (None, "all")) else (args.domain,)
        runs = [(args.group.upper(), d, args.suffix_dir) for d in domains]

    changelog: list[dict] = []
    for group, domain, suffix in runs:
        reevaluate(group, domain, suffix, dry_run=args.dry_run, changelog=changelog)

    if changelog and not args.dry_run:
        path = BASE_DIR / "results" / "eval_attacks" / "rescoring_changelog.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(changelog[0].keys()))
            if new_file:
                w.writeheader()
            w.writerows(changelog)
        print(f"\nchangelog appended: {path} (+{len(changelog)} rows)")


if __name__ == "__main__":
    main()
