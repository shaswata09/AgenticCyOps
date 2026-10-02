"""The mechanism analyses of the paper, re-run on the reported (v3.1) runs.

Each was first run on the earlier runs; this module repeats it on
``q235_local2_v31`` (and the v3.1 persistent-state runs) with the same code:

    gate          the permissive approve gate (P3.9) offline: what it approves
                  by role, and what substituting it for the panel executes
                  (analysis.gate_offline); the v2.9 calibration run beside it
    siblings      the rule-evading siblings (E2) against their parents
    evidence      P2.2 with structured evidence only (analysis.trusted_evidence)
    expiry        expiry and identity policies for the stateful checks
                  (analysis.ledger_expiry), and whether identity keying keeps
                  every stateful interception of the isolated attack runs
    judges        agreement, per-judge discrimination, and per-domain approval
                  of legitimate proposals over the v3.1 FULL rounds (Local4)
    fidelity      cached votes against the votes logged live in the v3.1 runs

The reported 75 variants per domain exclude the E2 siblings that the v3.1 runs
also carry. Logs and cached votes only; no model is queried.

    python -m analysis.v31_mechanisms     # -> results/v31_mechanisms.{json,md}
"""
from __future__ import annotations

import csv
import itertools
import json
import re
from collections import Counter, defaultdict

from analysis.p3_eligibility import JUDGED_PATHS, _payload, call_path, trials
from analysis.replay_panels import PANELS, decide, load_all_votes, panel_for
from config import BASE_DIR

GROUP = "q235_local2_v31"
CALIBRATION = "q235_local2_v29"
PERSIST = ("q235_local2_v31persist", "q235_local2_v31persist2")
D4 = ("cyberops", "healthcare", "finance", "legal")
ROUNDS = BASE_DIR / "cache" / "replay_v31" / "rounds.jsonl"
TRIALS = BASE_DIR / "results" / "eval_attacks" / "all_trials_local4.csv"


def pct(a, b) -> float:
    return round(100 * a / b, 1) if b else 0.0


def siblings_of() -> dict[tuple[str, str, str], tuple[str, str, str]]:
    """(domain, ap, variant) of each E2 sibling -> its parent (variant_id apN_vKe2)."""
    out = {}
    for f in sorted((BASE_DIR / "domains").glob("*/payloads/ap*_variants.json")):
        dom, ap = f.parts[-3], f.name.split("_")[0]
        for i, v in enumerate(json.loads(f.read_text())):
            m = re.match(r"ap\d+_v(\d+)e2$", v.get("variant_id", ""))
            if m:
                out[(dom, ap, str(i + 1))] = (dom, ap, m.group(1))
    return out


def _is_sibling(tid: str, sib) -> bool:
    m = re.match(r"(\w+?)_(ap\d+)_v(\d+)_t\d+", tid)
    return bool(m) and (m.group(1), m.group(2), m.group(3)) in sib


def gate(sib) -> dict:
    """The permissive gate on the CyberOps rounds that reached the panel."""
    import analysis.gate_offline as go
    from attacks.effects import build_calls, evaluate_effects
    from consensus.auto_gates import AutoGates
    from consensus.scoring import ProposalScorer

    orig_trials = go.trials
    go.trials = lambda g, d, c, suffix="": {t: e for t, e in orig_trials(g, d, c, suffix).items()
                                           if not _is_sibling(t, sib)}
    try:
        out = {}
        for g in (GROUP, CALIBRATION):
            gate_, scorer = AutoGates(mode="permissive"), ProposalScorer(domain="cyberops")
            c = Counter()
            for tid, events in go.trials(g, "cyberops", "agenticcyops").items():
                benign = "_benign_" in tid
                ids = set()
                if not benign and (p := _payload("cyberops", tid)):
                    ids = set(evaluate_effects(p[1], events, config="agenticcyops").attempted_call_ids or [])
                for call in build_calls(events):
                    path = call_path(call, events)
                    if path not in JUDGED_PATHS:
                        continue
                    role = "benign" if benign else ("attack" if call.call_id in ids else "other")
                    dec, _r, det = gate_.evaluate(scorer.score(go.p3_proposal(call, call.phase), {}))
                    c[(role, "n")] += 1
                    c[(role, "gate_approves")] += bool(dec and det.get("approved"))
            sub = go.simulate("permissive", False, g, domains=("cyberops",))["cyberops"]
            out[g] = {f"{r}|{k}": v for (r, k), v in sorted(c.items())} | {
                "attack_incident_approved_pct": pct(c[("attack", "gate_approves")] + c[("other", "gate_approves")],
                                                    c[("attack", "n")] + c[("other", "n")]),
                "attack_approved_pct": pct(c[("attack", "gate_approves")], c[("attack", "n")]),
                "benign_approved_pct": pct(c[("benign", "gate_approves")], c[("benign", "n")]),
                "trials": sub.get("n", 0),
                "executed_as_run": sub.get("executed_as_run", 0),
                "executed_with_gate": sub.get("executed_with_gate", 0)}
        # the other three domains, and whether the gate decides live
        other = go.simulate("permissive", False, GROUP, domains=D4[1:])
        out["other_domains_gate_approvals"] = sum(v.get("attack_gate_approve", 0) + v.get("benign_gate_approve", 0)
                                                  for v in other.values())
    finally:
        go.trials = orig_trials
    live, align = Counter(), defaultdict(list)
    for d in D4:
        for f in (BASE_DIR / "logs" / f"{d}_eval_attacks_{GROUP}").glob("agenticcyops_*.jsonl"):
            for ln in open(f, errors="ignore"):
                if '"P3_L2_scores"' not in ln:
                    continue
                e = json.loads(ln)
                live[str(e.get("auth_decision"))] += 1
                if d == "cyberops":
                    align["benign" if "_benign_" in e["trial_id"] else "attack"].append(float(e.get("alignment", 0.5)))
    out["live_gate_decisions"] = dict(live)
    out["live_alignment_cyberops"] = {k: round(sum(v) / len(v), 3) for k, v in align.items() if v}
    return out


def siblings(sib) -> dict:
    rows = list(csv.DictReader(open(TRIALS)))
    parents = set(sib.values())
    out = {}
    for cfg in ("flat", "acl_hardened", "llm_judge", "symbolic_only", "agenticcyops"):
        for lbl, keys in (("siblings", set(sib)), ("parents", parents)):
            rs = [r for r in rows if r["group"] == GROUP and r["config"] == cfg
                  and (r["domain"], r["ap"], r["variant"]) in keys]
            out[f"{cfg}|{lbl}"] = f"{sum(r['outcome'] == 'executed' for r in rs)}/{len(rs)}"
    by = defaultdict(list)
    for r in rows:
        if r["group"] == GROUP and r["config"] == "agenticcyops" and (r["domain"], r["ap"], r["variant"]) in sib:
            by[(r["domain"], r["ap"], r["variant"])].append((r["outcome"], r["blocked_by"]))
    held = [k for k, v in by.items() if all(o != "executed" for o, _ in v)]
    out["held"] = len(held)
    out["held_with_a_panel_interception"] = sum(any(b == "P3_llm_consensus_reject" for _, b in by[k]) for k in held)
    out["executed"] = sorted(":".join(k) for k, v in by.items() if any(o == "executed" for o, _ in v))
    out["full_blocked_by"] = dict(Counter(b for v in by.values() for o, b in v if o == "blocked"))
    return out


def evidence() -> dict:
    from analysis.trusted_evidence import evaluate
    tot = Counter()
    for v in evaluate(GROUP).values():
        tot.update(v)
    return dict(sorted(tot.items()))


def expiry(sib) -> dict:
    from analysis.ledger_expiry import sequence, simulate
    out = {}
    for g in PERSIST:
        seq = sequence(g, "cyberops")
        pol = {}
        for name, w, ident in (("shipped", None, False), ("skeleton_5", 5, False), ("skeleton_2", 2, False),
                               ("skeleton_1", 1, False), ("identity", None, True), ("identity_1", 1, True)):
            r = simulate(seq, w, ident)
            n = r.get("benign_consequential", 0)
            d = r.get("benign_denied_L4", 0) + r.get("benign_denied_L5", 0)
            pol[name] = {"denied": d, "of": n, "pct": pct(d, n)}
        first = next((items for t, items in seq if "_benign_" in t), [])
        out[g] = pol | {"first_benign_stateful_denials": sum(l != "pass" for _, l, _ in first)}
    seq = [(t, i) for t, i in sequence(GROUP, "cyberops")
           if "_benign_" not in t and not _is_sibling(t, sib)]
    logged = [(t, i) for t, i in seq if any(l != "pass" for _, l, _ in i)]
    kept = 0
    for t, i in logged:
        r = simulate([(t, i)], 1, True)
        kept += r.get("attack_denied_L4", 0) + r.get("attack_denied_L5", 0) > 0
    out["isolated_stateful_interceptions"] = {"trials": len(logged), "kept_by_identity_1": kept}
    return out


def judges() -> dict:
    V = load_all_votes()
    members = PANELS["Local4"][0]
    rounds = [json.loads(ln) for ln in open(ROUNDS)]
    full = [r for r in rounds if r["arm"] == "v31_full" and r["path"] in JUDGED_PATHS
            and all(V[m].get(r["key"]) in ("approve", "reject") for m in members)]
    vec = {m: [V[m][r["key"]] == "approve" for r in full] for m in members}

    def kappa(a, b):
        n = len(a)
        po = sum(x == y for x, y in zip(a, b)) / n
        pa, pb = sum(a) / n, sum(b) / n
        pe = pa * pb + (1 - pa) * (1 - pb)
        return (po - pe) / (1 - pe)
    ks = {f"{a}|{b}": round(kappa(vec[a], vec[b]), 2) for a, b in itertools.combinations(members, 2)}
    cnt = [sum(vec[m][i] for m in members) for i in range(len(full))]
    disc = {role: {m: pct(sum(V[m][r["key"]] == "approve" for r in full if r["role"] == role),
                          sum(r["role"] == role for r in full)) for m in members}
            for role in ("attack_effect", "benign")}
    mem, q = panel_for("Local4", "v31_full")
    legit = {}
    for d in D4:
        dec = [decide(r["key"], mem, q, V) for r in full if r["role"] == "benign" and r["domain"] == d]
        dec = [x for x in dec if x is not None]
        legit[d] = {"approved_pct": pct(sum(dec), len(dec)), "n": len(dec)}
    return {"rounds": len(full), "kappa": ks, "kappa_mean": round(sum(ks.values()) / len(ks), 2),
            "approved_pct_by_quorum": {k: pct(sum(c >= k for c in cnt), len(cnt)) for k in (1, 2, 3, 4)},
            "approve_pct_by_role": disc, "panel_approves_legitimate": legit}


def fidelity() -> dict:
    V = load_all_votes()
    c = Counter()
    for ln in open(ROUNDS):
        r = json.loads(ln)
        for m, lv in (r.get("logged_votes") or {}).items():
            nv, lv = V.get(m, {}).get(r["key"]), str(lv).lower()
            if nv in ("approve", "reject") and lv in ("approve", "reject"):
                c[(m, nv == lv)] += 1
    out = {m: {"reproduced": c[(m, True)], "of": c[(m, True)] + c[(m, False)],
               "pct": pct(c[(m, True)], c[(m, True)] + c[(m, False)])} for m in sorted({m for m, _ in c})}
    tot = sum(v["of"] for v in out.values())
    out["all"] = {"reproduced": sum(v["reproduced"] for v in out.values()), "of": tot,
                  "pct": pct(sum(v["reproduced"] for v in out.values()), tot)}
    return out


def main() -> None:
    sib = siblings_of()
    res = {"gate": gate(sib), "siblings": siblings(sib), "evidence": evidence(),
           "expiry": expiry(sib), "judges": judges(), "fidelity": fidelity()}
    (BASE_DIR / "results" / "v31_mechanisms.json").write_text(json.dumps(res, indent=1))
    L = ["# Mechanism analyses at v3.1", "",
         "Generated by `python -m analysis.v31_mechanisms` (logs and cached votes only). "
         "The 75 reported variants per domain; the E2 siblings only in the sibling section.", ""]
    for k, v in res.items():
        L += [f"## {k}", "", "```", json.dumps(v, indent=1), "```", ""]
    (BASE_DIR / "results" / "v31_mechanisms.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
