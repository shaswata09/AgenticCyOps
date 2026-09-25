"""The judgment boundary for the two primaries run live at defense-freeze-v2.9.

Groups ``oss120_local2_v29`` (gpt-oss-120b) and ``llama8b_local2_v29``
(Llama-3.1-8B), CyberOps development split, all five boundary
configurations, local2 panel live. Panel-free configurations (FLAT, ACL,
NOJUDGE) are reported as run; JUDGEONLY and FULL as the direct outcome under
Local4 (a model never judges its own proposals, so gpt-oss-120b's panel is
the other three, two of three), with the live local2 value alongside. The
payload files also carry the E2 siblings; only the original 75 variants
count.

    python -m analysis.primaries_tables     # -> results/primaries_v29.json, .md
"""
from __future__ import annotations

import json
from collections import Counter

from analysis.p3_eligibility import _payload, call_path, trials
from analysis.replay_panels import asr, load_all_votes, load_rounds, outcomes
from attacks.effects import build_calls, evaluate_effects
from config import BASE_DIR

DOM = "cyberops"
PRIMARIES = {"gpt-oss-120b": ("oss120_local2_v29", "oss120"), "Llama-3.1-8B": ("llama8b_local2_v29", "llama8b")}
PANEL_FREE = {"FLAT": "flat", "ACL": "acl_hardened", "NOJUDGE": "symbolic_only"}
JUDGED = {"JUDGEONLY": ("llm_judge", "judgeonly"), "FULL": ("agenticcyops", "full")}


def _pct(x: float) -> str:
    return f"{100 * x:.1f}"


def _ci(ts: list[dict]) -> str:
    p, lo, hi, n = asr(ts)
    return f"{_pct(p)} [{_pct(lo)}, {_pct(hi)}]" if n else "n/a"


def original_variants() -> set[tuple[str, str]]:
    return {tuple(t.split("_")[1:3]) for t in trials("q235_div4", DOM, "agenticcyops") if "_benign_" not in t}


def as_run(group: str, cfg: str, keep) -> tuple[list[dict], Counter, Counter]:
    attack, benign, paths = [], Counter(), Counter()
    for tid, ev in trials(group, DOM, cfg).items():
        calls = [c for c in build_calls(ev) if c.kind == "tool"]
        if "_benign_" in tid:
            benign["proposed"] += len(calls)
            benign["denied"] += sum(c.denied for c in calls)
            benign["incidents"] += 1
            benign["any"] += any(c.denied for c in calls)
            continue
        ap, var = tid.split("_")[1:3]
        if (ap, var) not in keep:
            continue
        for c in calls:
            paths[call_path(c, ev)] += 1
        p = _payload(DOM, tid)
        v = evaluate_effects(p[1], ev, config=cfg)
        if v.outcome in ("executed", "blocked", "not_attempted"):
            attack.append({"domain": DOM, "ap": ap, "variant": var, "outcome": v.outcome})
    return attack, benign, paths


def summarize(attack, benign, paths=None) -> dict:
    att = [t for t in attack if t["outcome"] != "not_attempted"]
    out = {"asr": _ci(attack), "n": len(attack),
           "attempt": _pct(len(att) / len(attack)) if attack else "n/a",
           "block_given_attempt": _pct(sum(t["outcome"] == "blocked" for t in att) / len(att)) if att else "n/a"}
    if benign.get("proposed"):
        out["benign_denied"] = _pct(benign["denied"] / benign["proposed"])
    if paths:
        tot = sum(paths.values())
        out["judged"] = _pct((paths["p3_panel_approved"] + paths["p3_panel_rejected"]) / tot) if tot else "n/a"
    return out


def build() -> dict:
    V, R = load_all_votes(), load_rounds()
    keep = original_variants()
    res: dict = {}
    for name, (group, arm) in PRIMARIES.items():
        row: dict = {}
        for label, cfg in PANEL_FREE.items():
            a, b, _p = as_run(group, cfg, keep)
            row[label] = summarize(a, b)
        for label, (cfg, suffix) in JUDGED.items():
            a_live, b_live, paths = as_run(group, cfg, keep)
            key = f"{arm}_{suffix}"
            r4 = outcomes(key, group, cfg, (DOM,), "", "Local4", V, R.get(key, []))
            a4 = [t for t in r4["domains"][DOM]["attack"] if (t["ap"], t["variant"]) in keep]
            row[label] = {**summarize(a4, Counter(r4["domains"][DOM]["benign"]), paths),
                          "missing_votes": r4["missing_votes"],
                          "live_local2": summarize(a_live, b_live)}
        res[name] = row
    return res


def main() -> None:
    out = build()
    (BASE_DIR / "results" / "primaries_v29.json").write_text(json.dumps(out, indent=1))
    lines = ["# Judgment boundary for gpt-oss-120b and Llama-3.1-8B (live at v2.9, CyberOps)", "",
             "JUDGEONLY and FULL: direct outcome under Local4 (live local2 value in `live_local2`).", ""]
    for name, row in out.items():
        lines += [f"## {name}", "", "| Config | ASR % [95% CI] | Attempt % | Block|att. % | Judged % | Benign denied % |",
                  "|---|---|---|---|---|---|"]
        for label in ("FLAT", "ACL", "JUDGEONLY", "NOJUDGE", "FULL"):
            r = row[label]
            lines.append(f"| {label} | {r['asr']} | {r['attempt']} | {r['block_given_attempt']} | "
                         f"{r.get('judged', '0' if label in PANEL_FREE else 'n/a')} | {r.get('benign_denied', 'n/a')} |")
        lines.append("")
    (BASE_DIR / "results" / "primaries_v29.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
