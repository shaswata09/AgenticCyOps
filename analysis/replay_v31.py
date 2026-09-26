"""The judgment boundary at defense-freeze-v3.1 (the audit fixes), live.

Group ``q235_local2_v31``: Qwen3-235B, all five boundary configurations, four
domains, local2 panel live (Mistral-Small, Gemma-4). Panel-free
configurations (FLAT, ACL, NOJUDGE) are reported as run; JUDGEONLY and FULL as
the direct outcome under Local4, from the logged panel rounds re-judged
offline (votes cached by message hash in ``cache/validators/``), with the live
local2 value alongside. The reported numbers (``results/replay_tables.json``,
v2.2 code, Local4) are shown for comparison. Only the variants of the
reported runs count (the payload files also carry the E2 siblings).

    python -m analysis.replay_v31 build     # -> cache/replay_v31/{rounds,messages}.jsonl
    python -m analysis.replay_run query --replay-dir cache/replay_v31 --validator L1_mistral --url ...
    python -m analysis.replay_v31 tables    # -> results/replay_v31.json, .md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict

from analysis.p3_eligibility import _payload, trials
from analysis.replay_panels import asr, load_all_votes, outcomes
from attacks.effects import build_calls, evaluate_effects
from config import BASE_DIR

OUT = BASE_DIR / "cache" / "replay_v31"
GROUP = "q235_local2_v31"
D4 = ("cyberops", "healthcare", "finance", "legal")
PANEL_FREE = {"FLAT": "flat", "ACL": "acl_hardened", "NOJUDGE": "symbolic_only"}
JUDGED = {"JUDGEONLY": ("llm_judge", "v31_judgeonly"), "FULL": ("agenticcyops", "v31_full")}
# (label, group, config, domains, suffix, include_unjudged)
ARMS = [("v31_full", GROUP, "agenticcyops", D4, "", True),
        ("v31_judgeonly", GROUP, "llm_judge", D4, "", False)]


def build() -> None:
    from analysis.replay import rounds
    OUT.mkdir(parents=True, exist_ok=True)
    messages: dict[str, str] = {}
    with open(OUT / "rounds.jsonl", "w") as fr:
        for label, group, config, domains, suffix, unjudged in ARMS:
            n = 0
            for r in rounds(group, config, domains, suffix, include_unjudged=unjudged):
                messages.setdefault(r.key, r.message)
                row = asdict(r)
                row.pop("message")
                row["arm"] = label
                fr.write(json.dumps(row) + "\n")
                n += 1
            print(f"{label:16s} {n:6d} rounds", flush=True)
    with open(OUT / "messages.jsonl", "w") as fm:
        for k, m in messages.items():
            fm.write(json.dumps({"key": k, "message": m}) + "\n")
    print(f"distinct messages: {len(messages)}")


def _keep(domain: str) -> set[tuple[str, str]]:
    return {tuple(t.split("_")[1:3]) for t in trials("q235_div4", domain, "agenticcyops")
            if "_benign_" not in t}


def _ci(ts: list[dict]) -> str:
    p, lo, hi, n = asr(ts)
    return f"{100 * p:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]" if n else "n/a"


def _as_run(domain: str, config: str, keep) -> tuple[list[dict], Counter]:
    attack, benign = [], Counter()
    for tid, ev in trials(GROUP, domain, config).items():
        calls = [c for c in build_calls(ev) if c.kind == "tool"]
        if "_benign_" in tid:
            benign["proposed"] += len(calls)
            benign["denied"] += sum(c.denied for c in calls)
            continue
        ap, var = tid.split("_")[1:3]
        p = _payload(domain, tid)
        if (ap, var) not in keep or not p:
            continue
        v = evaluate_effects(p[1], ev, config=config)
        if v.outcome in ("executed", "blocked", "not_attempted"):
            attack.append({"ap": ap, "variant": var, "outcome": v.outcome})
    return attack, benign


def _row(attack, benign) -> dict:
    pct = lambda a, b: round(100 * a / b, 1) if b else None
    return {"asr": _ci(attack), "n": len(attack),
            "benign_denied": pct(benign.get("denied", 0), benign.get("proposed", 0))}


def tables() -> dict:
    V = load_all_votes()
    R: dict[str, list[dict]] = {}
    for ln in open(OUT / "rounds.jsonl"):
        r = json.loads(ln)
        R.setdefault(r["arm"], []).append(r)
    reported = json.loads((BASE_DIR / "results" / "replay_tables.json").read_text())["domains"]
    res: dict = {}
    for d in D4:
        keep = _keep(d)
        row: dict = {}
        for label, cfg in PANEL_FREE.items():
            row[label] = _row(*_as_run(d, cfg, keep))
        for label, (cfg, arm) in JUDGED.items():
            live = _row(*_as_run(d, cfg, keep))
            o = outcomes(arm, GROUP, cfg, (d,), "", "Local4", V, R.get(arm, []))
            a4 = [t for t in o["domains"][d]["attack"] if (t["ap"], t["variant"]) in keep]
            row[label] = {**_row(a4, Counter(o["domains"][d]["benign"])),
                          "missing_votes": o["missing_votes"], "live_local2": live}
        row["reported_v22_local4"] = reported.get(d, {})
        res[d] = row
    (BASE_DIR / "results" / "replay_v31.json").write_text(json.dumps(res, indent=1))
    lines = ["# The judgment boundary at defense-freeze-v3.1 (audit fixes), Qwen3-235B", "",
             "Generated by `python -m analysis.replay_v31 tables`. FLAT, ACL and NOJUDGE as run; "
             "JUDGEONLY and FULL as the direct outcome under Local4 (live local2 in parentheses). "
             "Reported = the v2.2 runs under Local4. ASR % [95% CI]; benign = legitimate tool "
             "proposals denied or escalated %.", ""]
    for d, row in res.items():
        rep = row["reported_v22_local4"]
        lines += [f"## {d}", "", "| Config | v3.1 ASR | v3.1 benign denied | reported ASR |",
                  "|---|---|---|---|"]
        for label in ("FLAT", "ACL", "JUDGEONLY", "NOJUDGE", "FULL"):
            r = row[label]
            live = f" ({r['live_local2']['asr']})" if "live_local2" in r else ""
            rep_v = rep.get({"FLAT": "flat", "ACL": "acl", "FULL": "full"}.get(label, ""), "")
            lines.append(f"| {label} | {r['asr']}{live} | {r['benign_denied']} | {rep_v} |")
        lines.append("")
    (BASE_DIR / "results" / "replay_v31.md").write_text("\n".join(lines))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "tables"])
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        tables()
        print((BASE_DIR / "results" / "replay_v31.md").read_text())
