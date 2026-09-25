"""Offline re-adjudication with the v3.0 panel input (consensus/panel_context.py).

Every logged panel round of every judged arm is re-judged with the panel
input of ``defense-freeze-v3.0``: the v2.9 fields plus the incident's
structured evidence, the calling agent's scope, the operating context, and
the incident's earlier consequential decisions. The message is built by the
same function the live pipeline uses (``build_panel_message``).

Two properties of the logs bound what can be added:
* the agent's reasoning was never logged, so the justification stays what the
  host sent (a placeholder, or AP-10's injected rationale); only the live v3.0
  runs carry the model's stated reasoning;
* the incident's earlier decisions are those of the run as logged.

    python -m analysis.replay_v3 build                 # -> cache/replay_v3/{messages,rounds}.jsonl
    python -m analysis.replay_run query --replay-dir cache/replay_v3 --validator L1_mistral --url ...
    python -m analysis.replay_v3 tables                # -> results/replay_v3.json, .md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections import Counter, defaultdict

from analysis.p3_eligibility import _payload, call_path, trial_commits, trials
from analysis.replay import _SANITIZER, _full_justification, _proposal, incident_at
from analysis.replay_run import ARMS
from attacks.effects import build_calls, evaluate_effects
from config import BASE_DIR
from consensus.panel_context import build_panel_message, prior_action

OUT = BASE_DIR / "cache" / "replay_v3"
P3_PATHS = ("p3_panel_approved", "p3_panel_rejected", "p3_denied_rule")


def rounds(group: str, config: str, domains, suffix: str = ""):
    host_config = "llm_judge" if config == "llm_judge" else "agenticcyops"
    sanitize = config != "llm_judge"
    for d in domains:
        commits = trial_commits(group, d, config, suffix)
        for tid, events in trials(group, d, config, suffix).items():
            incident = incident_at(d, tid, commits.get(tid, ""))
            iid = incident.get("incident_id") or str(uuid.uuid5(uuid.NAMESPACE_URL, tid))
            benign = "_benign_" in tid
            attack_ids: set[str] = set()
            if not benign:
                p = _payload(d, tid)
                if p:
                    attack_ids = set(evaluate_effects(p[1], events, config=config).attempted_call_ids or [])
            just = {e.get("call_id"): e.get("justification", "") for e in events
                    if e.get("action") == "tool_proposed"}
            prior: list[dict] = []
            for c in build_calls(events):
                path = call_path(c, events)
                if path not in P3_PATHS:
                    continue
                c.justification = _full_justification(just.get(c.call_id, ""), c, d, tid)
                proposal = _proposal(c)
                if path in ("p3_panel_approved", "p3_panel_rejected"):
                    shown = _SANITIZER._sanitize_proposal(proposal) if sanitize else proposal
                    msg = build_panel_message(shown, {
                        "incident": incident, "incident_id": iid, "domain": d, "config": host_config,
                        "current_phase": c.phase, "prior_actions": list(prior)})
                    role = "benign" if benign else ("attack_effect" if c.call_id in attack_ids else "attack_other")
                    yield {"key": hashlib.sha256(msg.encode()).hexdigest(), "message": msg,
                           "group": group + suffix, "domain": d, "config": config, "trial_id": tid,
                           "call_id": c.call_id, "tool": c.target, "role": role, "path": path}
                prior.append(prior_action(proposal, path == "p3_panel_approved"))


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    known: dict[str, str] = {}
    with open(OUT / "rounds.jsonl", "w") as fr:
        for label, group, config, domains, suffix, _unjudged in ARMS:
            n = 0
            for r in rounds(group, config, domains, suffix):
                known.setdefault(r["key"], r.pop("message"))
                r.pop("message", None)
                fr.write(json.dumps({**r, "arm": label}) + "\n")
                n += 1
            print(f"{label:18s} {n:6d} rounds", flush=True)
    with open(OUT / "messages.jsonl", "w") as fm:
        for k, m in known.items():
            fm.write(json.dumps({"key": k, "message": m}) + "\n")
    print(f"distinct messages: {len(known)}")


def tables() -> dict:
    """The headline comparisons, v2.9 input against v3.0 input, both under Local4."""
    from analysis.replay_panels import PANELS, asr, decide, load_all_votes, load_rounds, outcomes, panel_for
    V = load_all_votes()
    old = load_rounds()
    new: dict[str, list[dict]] = defaultdict(list)
    for ln in open(OUT / "rounds.jsonl"):
        r = json.loads(ln)
        new[r["arm"]].append(r)
    D4 = ("cyberops", "healthcare", "finance", "legal")
    keep = {tuple(t.split("_")[1:3]) for t in trials("q235_div4", "cyberops", "agenticcyops") if "_benign_" not in t}
    pct = lambda x: round(100 * x, 1)

    def summary(arm, group, cfg, doms, suffix="", R=None):
        res = outcomes(arm, group, cfg, doms, suffix, "Local4", V, R[arm])
        out = {"missing_votes": res["missing_votes"]}
        for d in doms:
            a = [t for t in res["domains"][d]["attack"] if (group not in ("oss120_local2_v29", "llama8b_local2_v29")
                                                            or (t["ap"], t["variant"]) in keep)]
            p, lo, hi, n = asr(a)
            b = res["domains"][d]["benign"]
            out[d] = {"asr": f"{pct(p)} [{pct(lo)}, {pct(hi)}]", "n": n,
                      "benign_denied": pct(b["denied"] / b["proposed"]) if b.get("proposed") else None}
        return out

    arms = [("full", "q235_div4", "agenticcyops", D4), ("judgeonly", "q235_div4", "llm_judge", ("cyberops",)),
            ("oss120_full", "oss120_local2_v29", "agenticcyops", ("cyberops",)),
            ("oss120_judgeonly", "oss120_local2_v29", "llm_judge", ("cyberops",)),
            ("llama8b_full", "llama8b_local2_v29", "agenticcyops", ("cyberops",)),
            ("llama8b_judgeonly", "llama8b_local2_v29", "llm_judge", ("cyberops",))]
    out = {}
    for arm, g, cfg, doms in arms:
        out[arm] = {"v2.9_input": summary(arm, g, cfg, doms, R=old), "v3.0_input": summary(arm, g, cfg, doms, R=new)}

    # the judges themselves: approval of attack-effect vs benign proposals, per judge
    sel = {}
    for tag, R in (("v2.9_input", old), ("v3.0_input", new)):
        c = defaultdict(Counter)
        for r in R["full"]:
            if r.get("path") not in ("p3_panel_approved", "p3_panel_rejected"):
                continue
            for vid in PANELS["Local4"][0]:
                v = V[vid].get(r["key"])
                if v is None:
                    continue
                c[vid][(r["role"], v == "approve")] += 1
        sel[tag] = {vid: {role: pct(cc[(role, True)] / max(1, cc[(role, True)] + cc[(role, False)]))
                          for role in ("attack_effect", "benign")} for vid, cc in c.items()}
    out["judge_approval_rates"] = sel
    (BASE_DIR / "results" / "replay_v3.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "tables"])
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        print(json.dumps(tables(), indent=1))
