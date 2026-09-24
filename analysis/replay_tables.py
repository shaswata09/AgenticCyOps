"""Paper numbers under the all-local main panel (Local4), from the replay.

    python -m analysis.replay_tables          # writes results/replay_tables.md and .json

Configurations without a panel (FLAT, ACL, NOJUDGE, FULL minus P3) are
reported as run; every configuration with a panel is re-adjudicated by
Local4 (``analysis.replay_panels``). Outcomes are direct: the logged
proposals, decided by the replayed panel, re-scored by the oracle.
"""
from __future__ import annotations

import csv
import itertools
import json
from collections import Counter, defaultdict

from analysis import tiers
from analysis.replay_panels import (PANELS, asr, decide, load_all_votes, load_rounds,
                                    outcomes, panel_for)
from analysis.statistical_tests import cluster_bootstrap
from config import BASE_DIR

D4 = ("cyberops", "healthcare", "finance", "legal")
TR = D4[1:]
MAIN = "Local4"
T2_APS = {"ap5", "ap9", "ap10", "ap15"}
ALL_TRIALS = BASE_DIR / "results" / "eval_attacks" / "all_trials.csv"


def _pct(x):
    return f"{100 * x:.1f}"


def _ci(ts):
    p, lo, hi, n = asr(ts)
    return f"{_pct(p)} [{_pct(lo)}, {_pct(hi)}]", n


def _as_run(group, cfg, doms, suffix=""):
    """Attack trials of a panel-free configuration, as run."""
    out = []
    for t in csv.DictReader(open(ALL_TRIALS)):
        if (t["group"] == group and t["config"] == cfg and (t.get("suffix") or "") == suffix
                and t["domain"] in doms and t["ap"] != "benign"
                and t["outcome"] in ("executed", "blocked", "not_attempted")):
            out.append({"domain": t["domain"], "ap": t["ap"], "variant": f"v{t['variant']}",
                        "trial": f"t{t['trial']}", "outcome": t["outcome"], "blocked_by": t["blocked_by"],
                        "as_run": t["outcome"], "channel": t.get("channel", "")})
    return out


def _attempt(ts):
    a = [t for t in ts if t["outcome"] in ("executed", "blocked")]
    return len(a) / len(ts) if ts else float("nan"), (
        sum(t["outcome"] == "blocked" for t in a) / len(a) if a else float("nan"))


def build() -> dict:
    V, R = load_all_votes(), load_rounds()
    out: dict = {}

    full = outcomes("full", "q235_div4", "agenticcyops", D4, "", MAIN, V, R["full"])
    full_je = outcomes("full", "q235_div4", "agenticcyops", D4, "", MAIN, V, R["full"], judge_everything=True)
    judge = outcomes("judgeonly", "q235_div4", "llm_judge", ("cyberops",), "", MAIN, V, R["judgeonly"])
    A = lambda res, doms=D4: [t for d in doms for t in res["domains"].get(d, {}).get("attack", [])]
    ben = lambda res, doms=D4: Counter(sum((Counter(res["domains"][d]["benign"]) for d in doms if d in res["domains"]), Counter()))

    # ---- development split, every configuration
    dev = {}
    for label, ts in (("FLAT", _as_run("q235_div4", "flat", ("cyberops",))),
                      ("ACL", _as_run("q235_div4", "acl_hardened", ("cyberops",))),
                      ("JUDGEONLY", A(judge, ("cyberops",))),
                      ("NOJUDGE", _as_run("q235_div4", "symbolic_only", ("cyberops",))),
                      ("FULL", A(full, ("cyberops",)))):
        ci, n = _ci(ts)
        att, blk = _attempt(ts)
        dev[label] = {"asr": ci, "n": n, "attempt": _pct(att), "block_given_attempt": _pct(blk)}
    for label, res in (("JUDGEONLY", judge), ("FULL", full), ("FULL, judge everything after rules", full_je)):
        b = ben(res, ("cyberops",))
        dev.setdefault(label, {})["benign_denied"] = _pct(b["denied"] / b["proposed"])
    dev["FULL, judge everything after rules"]["asr"] = _ci(A(full_je, ("cyberops",)))[0]
    out["development"] = dev

    # ---- ablations on the variants shared by every arm
    abl = {i: outcomes(f"full_minus_p{i}", "q235_div4", "agenticcyops", ("cyberops",), f"_disabled_P{i}",
                       MAIN, V, R[f"full_minus_p{i}"]) for i in (1, 2, 4, 5)}
    p3 = _as_run("q235_div4", "agenticcyops", ("cyberops",), "_disabled_P3")
    arms = {"FULL": A(full, ("cyberops",)), **{f"minus P{i}": A(r, ("cyberops",)) for i, r in abl.items()},
            "minus P3": p3}
    key = lambda t: (t["ap"], t["variant"])
    shared = set.intersection(*[{key(t) for t in ts} for ts in arms.values()])
    out["ablation"] = {"shared_variants": len(shared)}
    for label, ts in arms.items():
        ci, n = _ci([t for t in ts if key(t) in shared])
        out["ablation"][label] = {"asr": ci, "n": n}
    for i, r in abl.items():
        b = ben(r, ("cyberops",))
        out["ablation"][f"minus P{i}"]["benign_denied"] = _pct(b["denied"] / b["proposed"]) if b["proposed"] else "n/a"

    # ---- domains, transfer, primaries
    out["domains"] = {}
    for d in D4:
        b = full["domains"][d]["benign"]
        out["domains"][d] = {"flat": _ci(_as_run("q235_div4", "flat", (d,)))[0],
                             "acl": _ci(_as_run("q235_div4", "acl_hardened", (d,)))[0],
                             "full": _ci(A(full, (d,)))[0],
                             "benign_denied": _pct(b["denied"] / b["proposed"])}
    out["transfer_full"] = _ci(A(full, TR))[0]
    out["all_domains_full"] = _ci(A(full))[0]
    prim = {}
    for arm, g in (("scout", "scout_div4"), ("mistral", "mistral_div3p"), ("llama8b", "llama8b_div4")):
        r = outcomes(arm, g, "agenticcyops", ("cyberops", "finance"), "", MAIN, V, R[arm])
        b = ben(r, ("cyberops",))
        prim[arm] = {"full_cyberops": _ci(A(r, ("cyberops",)))[0], "full_finance": _ci(A(r, ("finance",)))[0],
                     "benign_denied_cyberops": _pct(b["denied"] / b["proposed"])}
    q = [t for t in A(full, ("cyberops", "finance"))]
    pooled = q + [t for arm, g in (("scout", "scout_div4"), ("mistral", "mistral_div3p"), ("llama8b", "llama8b_div4"))
                  for t in A(outcomes(arm, g, "agenticcyops", ("cyberops", "finance"), "", MAIN, V, R[arm]))]
    prim["pooled_full"] = _ci(pooled)[0]
    out["primaries"] = prim

    # ---- first interception by tier and by principle
    def shares(ts):
        mech = [t["blocked_by"] for t in ts if t["outcome"] == "blocked"]
        s, n, _u = tiers.shares(mech)
        by_p = Counter("panel" if tiers.tier_of(m) == "panel" else m.split("_")[0] for m in mech)
        return {"n": n, **{t: _pct(v) for t, v in s.items()},
                **{f"principle_{k}": _pct(v / len(mech)) for k, v in by_p.items()}}
    out["tiers"] = {"development": shares(A(full, ("cyberops",))), "transfer": shares(A(full, TR))}

    # ---- paired JUDGEONLY vs FULL
    ever = lambda ts: {key(t): any(u["outcome"] == "executed" for u in ts if key(u) == key(t)) for t in ts}
    j, f = ever(A(judge, ("cyberops",))), ever(A(full, ("cyberops",)))
    common = set(j) & set(f)
    cls = Counter((j[v], f[v]) for v in common)
    jonly = [v for v in common if j[v] and not f[v]]
    out["paired"] = {"variants": len(common), "judgeonly_only": cls[(True, False)], "both": cls[(True, True)],
                     "full_only": cls[(False, True)], "judgeonly_only_on_memory_paths": sum(v[0] in ("ap4", "ap13") for v in jonly)}

    # ---- channels (four domains) and attacker tiers (development)
    ch = {(t["domain"], t["ap"], t["variant"], t["trial"]): t["channel"]
          for t in _as_run("q235_div4", "flat", D4)}
    by_ch = defaultdict(list)
    for t in A(full):
        by_ch[ch.get((t["domain"], t["ap"], t["variant"], t["trial"]), "")].append(t)
    out["channels_full"] = {c: _ci(ts)[0] for c, ts in by_ch.items() if c}
    fd = A(full, ("cyberops",))
    out["attacker_tiers_full_dev"] = {"T2": _ci([t for t in fd if t["ap"] in T2_APS])[0],
                                      "T1": _ci([t for t in fd if t["ap"] not in T2_APS])[0]}
    out["residuals"] = {
        "legal_ap2_full": f"{sum(t['outcome'] == 'executed' for t in A(full, ('legal',)) if t['ap'] == 'ap2')}/15",
        "finance_ap9_full": f"{sum(t['outcome'] == 'executed' for t in A(full, ('finance',)) if t['ap'] == 'ap9')}/15",
        "ap10_judgeonly": f"{sum(t['outcome'] == 'executed' for t in A(judge) if t['ap'] == 'ap10')}/15",
        "ap10_full": f"{sum(t['outcome'] == 'executed' for t in A(full, ('cyberops',)) if t['ap'] == 'ap10')}/15",
        "executed_full_by_domain_ap": dict(Counter(f"{t['domain']}:{t['ap']}" for t in A(full) if t["outcome"] == "executed")),
    }

    # ---- the judges themselves: agreement, strictness, quorum, benign rejection by domain
    m4, q4 = PANELS[MAIN]
    judged = [r for r in R["full"] if r["path"] != "allowed_no_p3"]
    votes = [{v: V[v].get(r["key"]) for v in m4} for r in judged]
    def kappa(a, b):
        xs = [(x[a] == "approve", x[b] == "approve") for x in votes]
        po = sum(p == q for p, q in xs) / len(xs)
        pa, pb = sum(p for p, _ in xs) / len(xs), sum(q for _, q in xs) / len(xs)
        pe = pa * pb + (1 - pa) * (1 - pb)
        return (po - pe) / (1 - pe)
    ks = {f"{a}|{b}": round(kappa(a, b), 2) for a, b in itertools.combinations(m4, 2)}
    out["judges"] = {
        "rounds": len(votes), "kappa": ks, "kappa_mean": round(sum(ks.values()) / len(ks), 2),
        "reject_rate": {v: _pct(sum(x[v] != "approve" for x in votes) / len(votes)) for v in m4},
        "approved_by_quorum": {k: _pct(sum(sum(x[v] == "approve" for v in m4) >= k for x in votes) / len(votes))
                               for k in range(1, len(m4) + 1)},
        "selectivity": {v: {role: _pct(sum(V[v].get(r["key"]) == "approve" for r in judged if r["role"] == role)
                                      / max(1, sum(r["role"] == role for r in judged)))
                            for role in ("attack_effect", "benign")} for v in m4},
        "benign_approved_by_domain": {d: _pct(sum(bool(decide(r["key"], m4, q4, V)) for r in judged
                                                  if r["role"] == "benign" and r["domain"] == d)
                                              / max(1, sum(r["role"] == "benign" and r["domain"] == d for r in judged)))
                                      for d in D4},
    }

    # ---- ASB, rule-evading siblings, lineage
    asb = {}
    for panel in ("Local4", "Div3L", "Lin3", "Single"):
        mem, qq = panel_for(panel, "asb")
        asb[panel] = {"replay405_let_through": sum(bool(decide(r["key"], mem, qq, V)) for r in R["asb_replay405"]),
                      "frozen_executed": sum(bool(decide(r["key"], mem, qq, V)) for r in R["asb_frozen"])}
    out["asb"] = asb
    lin = {}
    for panel in ("Local4", "Div3L", "Lin3", "Single"):
        r = outcomes("full", "q235_div4", "agenticcyops", D4, "", panel, V, R["full"])
        lin[panel] = {"dev": _ci(A(r, ("cyberops",)))[0], "transfer": _ci(A(r, TR))[0]}
    out["lineage"] = lin
    return out


def main() -> None:
    out = build()
    (BASE_DIR / "results" / "replay_tables.json").write_text(json.dumps(out, indent=1))
    lines = ["# Paper numbers under the all-local main panel (Local4)", "",
             "Generated by `python -m analysis.replay_tables` from the logs and `cache/validators/`.", ""]
    for k, v in out.items():
        lines += [f"## {k}", "", "```", json.dumps(v, indent=1), "```", ""]
    (BASE_DIR / "results" / "replay_tables.md").write_text("\n".join(lines))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
