"""E7: one definition of the benign denial rate, shared by table and figure.

The paper quoted a benign denial rate from an ad hoc query, and the figure and
the table computed it two different ways. This module owns the definition so
both import it and cannot drift:

    denied tool proposals / all tool proposals,
    isolated benign runs, one group, per domain

A *tool proposal* is a ``tool_proposed`` event, identified by its ``call_id``.
It counts as *denied* when an event for the same ``call_id`` carries
``auth_decision == "deny"``. Matching on ``call_id`` is what makes the ratio
well defined: the numerator is a subset of the denominator by construction, so
the rate cannot exceed 100% and does not mix tool denials with memory-op
denials (the harness's per-trial ``collateral_denials`` counts both, which is
why the figure used to read higher than the table).

``consensus_vote`` events are individual validator opinions rather than
decisions, so they never count as a denial here.

Resumed runs are deduped the way ``parse_logs`` dedupes trial outcomes: for
each trial, the newest log file that carries it wins.
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict

from config import BASE_DIR

LOGS = BASE_DIR / "logs"
DOMAINS = ("cyberops", "finance", "healthcare", "legal")


def proposal_denials(group: str, domain: str, config: str = "agenticcyops",
                     ap: str = "benign") -> tuple[int, int]:
    """``(denied, proposed)`` tool proposals for one (group, domain, config)."""
    per: dict[tuple[str, str], dict[str, set]] = defaultdict(
        lambda: {"prop": set(), "deny": set()})
    newest: dict[str, str] = {}
    pattern = str(LOGS / f"{domain}_eval_attacks_{group}" / f"{config}_*.jsonl")
    for f in sorted(glob.glob(pattern)):
        with open(f, errors="ignore") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                try:
                    e = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if e.get("ap") != ap:
                    continue
                tid = e.get("trial_id")
                if not tid:
                    continue
                newest[tid] = f
                cid = e.get("call_id")
                if not cid:
                    continue
                rec = per[(tid, f)]
                if e.get("action") == "tool_proposed":
                    rec["prop"].add(cid)
                elif (str(e.get("auth_decision") or "").lower() == "deny"
                        and e.get("action") != "consensus_vote"):
                    rec["deny"].add(cid)
    denied = proposed = 0
    for (tid, f), rec in per.items():
        if newest.get(tid) != f:
            continue
        proposed += len(rec["prop"])
        denied += len(rec["deny"] & rec["prop"])     # subset of the denominator
    return denied, proposed


def proposal_denials_by_variant(group: str, domain: str, config: str = "agenticcyops",
                                ap: str = "benign") -> dict[str, tuple[int, int]]:
    """``{cluster_key: (denied, proposed)}`` for the cluster bootstrap.

    The key is ``domain:ap:variant``, matching
    ``analysis.statistical_tests._CLUSTER`` so intervals resample the same
    clusters the tables do.
    """
    per: dict[tuple[str, str], dict[str, set]] = defaultdict(
        lambda: {"prop": set(), "deny": set()})
    newest: dict[str, str] = {}
    pattern = str(LOGS / f"{domain}_eval_attacks_{group}" / f"{config}_*.jsonl")
    for f in sorted(glob.glob(pattern)):
        with open(f, errors="ignore") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                try:
                    e = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if e.get("ap") != ap:
                    continue
                tid = e.get("trial_id")
                if not tid:
                    continue
                newest[tid] = f
                cid = e.get("call_id")
                if not cid:
                    continue
                rec = per[(tid, f)]
                if e.get("action") == "tool_proposed":
                    rec["prop"].add(cid)
                elif (str(e.get("auth_decision") or "").lower() == "deny"
                        and e.get("action") != "consensus_vote"):
                    rec["deny"].add(cid)
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for (tid, f), rec in per.items():
        if newest.get(tid) != f:
            continue
        # trial_id is "<domain>_<ap>_v<variant>_t<trial>_<config>"
        parts = tid.split("_")
        try:
            v = next(p for p in parts if p.startswith("v") and p[1:].isdigit())[1:]
        except StopIteration:
            continue
        key = f"{domain}:{ap}:{v}"
        out[key][0] += len(rec["deny"] & rec["prop"])
        out[key][1] += len(rec["prop"])
    return {k: (d, p) for k, (d, p) in out.items()}


def benign_denial_rates(group: str, configs, domains=DOMAINS) -> dict:
    """``{(domain, config): (denied, proposed, rate)}`` plus pooled totals."""
    out: dict = {}
    for config in configs:
        tot_d = tot_p = 0
        for domain in domains:
            d, p = proposal_denials(group, domain, config)
            out[(domain, config)] = (d, p, (d / p) if p else float("nan"))
            tot_d += d
            tot_p += p
        out[("all", config)] = (tot_d, tot_p, (tot_d / tot_p) if tot_p else float("nan"))
    return out
