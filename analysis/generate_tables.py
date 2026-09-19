"""Paper tables from the v3 results (H12).  ``make paper-tables`` runs
parse_logs -> statistical_tests -> this script.

Reads ``results/eval_attacks/all_trials.csv`` and ``stats.csv`` (plus the ASB
``summary.csv`` files when present) and writes ``results/paper_tables.md``
with:

  T1  headline per group x config: ASR [Wilson 95% CI], attempt rate,
      block rate given attempt, paired difference vs AgenticCyOps
  T2  per attack path x config for the main group (all domains pooled and
      CyberOps alone), Holm-corrected paired p-values
  T3  benign utility (E1): task completion, any-denial rate, denials per
      incident, latency, tokens
  T4  ablations (E3): ASR and benign denial rate per ablation config
  T5  what blocked the attacks: blocked_by distribution under AgenticCyOps
  T6  ASB paired panel replay (E6) when the replay outputs exist
  T7  cost: tokens and latency per config
  T8  run provenance (runs.csv)

Usage::

    python -m analysis.generate_tables [--main-group q235_div4]
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from analysis.statistical_tests import MEASURABLE, SYSTEM_CONFIGS, wilson
from config import RESULTS_DIR

CONFIG_LABEL = {"flat": "Flat", "acl_hardened": "ACL-Hardened", "agenticcyops": "AgenticCyOps",
                "llm_judge": "LLM-judge only", "symbolic_only": "Symbolic only (no L6)"}
AP_LABEL = {"ap1": "AP-1 Tool redirection", "ap2": "AP-2 Memory poisoning", "ap3": "AP-3 Confused deputy",
            "ap4": "AP-4 Cross-phase leak", "ap5": "AP-5 Irreversible action", "ap6": "AP-6 Replay",
            "ap7": "AP-7 Action chain", "ap8": "AP-8 Parameter manipulation", "ap9": "AP-9 Handoff poisoning",
            "ap10": "AP-10 Validator manipulation", "ap11": "AP-11 Operational context",
            "ap12": "AP-12 Concurrent actions", "ap13": "AP-13 Adversarial memory",
            "ap14": "AP-14 Read injection", "ap15": "AP-15 Infrastructure integrity"}


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _f(x, digits=1, pct=True):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "–"
    if math.isnan(v):
        return "–"
    return f"{100 * v:.{digits}f}" if pct else f"{v:.{digits}f}"


def _ci(p, lo, hi):
    if _f(p) == "–":
        return "–"
    return f"{_f(p)} [{_f(lo)}, {_f(hi)}]"


def _ap_sort(ap):
    return int(ap.replace("ap", "")) if ap.startswith("ap") and ap[2:].isdigit() else 99


def _md(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# --------------------------------------------------------------------- #


def t1_headline(stats: list[dict]) -> str:
    rows = []
    for r in stats:
        if r["domain"] != "all":
            continue
        for cfg in SYSTEM_CONFIGS:
            cmp_key = {"flat": "flat_minus_aco", "acl_hardened": "acl_minus_aco"}.get(cfg)
            diff = (f"{_f(r.get(cmp_key + '_diff'))} pp [{_f(r.get(cmp_key + '_low'))}, {_f(r.get(cmp_key + '_high'))}], p={_f(r.get(cmp_key + '_p'), 3, False)}"
                    if cmp_key and r.get(cmp_key + "_clusters") not in (None, "", "0") else "—")
            rows.append([r["group"], CONFIG_LABEL[cfg], r.get(f"{cfg}_n", ""),
                         _ci(r.get(f"{cfg}_asr"), r.get(f"{cfg}_wilson_low"), r.get(f"{cfg}_wilson_high")),
                         f"[{_f(r.get(f'{cfg}_boot_low'))}, {_f(r.get(f'{cfg}_boot_high'))}]",
                         _f(r.get(f"{cfg}_attempt_rate")), _f(r.get(f"{cfg}_block_given_attempt")), diff])
    return _md(["Group", "Config", "N", "ASR % [Wilson 95%]", "Cluster bootstrap 95%", "Attempt %",
                "Block | attempt %", "Δ vs AgenticCyOps"], rows)


def t2_per_ap(stats: list[dict], group: str, domain: str) -> str:
    rows = []
    for r in sorted((r for r in stats if r["group"] == group and r["domain"] == domain and r["ap"] != "all"),
                    key=lambda r: _ap_sort(r["ap"])):
        rows.append([AP_LABEL.get(r["ap"], r["ap"])]
                    + [f"{_ci(r.get(f'{c}_asr'), r.get(f'{c}_wilson_low'), r.get(f'{c}_wilson_high'))} (n={r.get(f'{c}_n')})"
                       for c in SYSTEM_CONFIGS]
                    + [f"{_f(r.get('flat_minus_aco_diff'))} (p_holm={_f(r.get('flat_minus_aco_p_holm'), 3, False)})",
                       f"{_f(r.get('acl_minus_aco_diff'))} (p_holm={_f(r.get('acl_minus_aco_p_holm'), 3, False)})"])
    return _md(["Attack path"] + [f"{CONFIG_LABEL[c]} ASR %" for c in SYSTEM_CONFIGS]
               + ["Flat − ACO (pp)", "ACL − ACO (pp)"], rows)


def t3_benign(trials: list[dict]) -> str:
    rows = []
    by = defaultdict(list)
    for t in trials:
        if t["ap"] == "benign" and t["outcome"] == "benign" and not t.get("suffix"):
            by[(t["group"], t["config"])].append(t)
    for (group, cfg), ts in sorted(by.items()):
        n = len(ts)
        task = [t for t in ts if t.get("task_completed") not in ("", None)]
        tc = sum(1 for t in task if str(t["task_completed"]).lower() == "true")
        any_den = sum(1 for t in ts if int(t.get("collateral_denials") or 0) > 0)
        den = sum(int(t.get("collateral_denials") or 0) for t in ts)
        lat = sorted(float(t.get("latency_s") or 0) for t in ts)
        ptok = sum(int(t.get("primary_tokens") or 0) for t in ts) / n
        vtok = sum(int(t.get("validator_tokens") or 0) for t in ts) / n
        p, lo, hi = wilson(tc, len(task))
        q, qlo, qhi = wilson(any_den, n)
        rows.append([group, CONFIG_LABEL.get(cfg, cfg), n, _ci(p, lo, hi), _ci(q, qlo, qhi),
                     f"{den / n:.2f}", f"{lat[n // 2]:.1f} / {lat[int(0.95 * (n - 1))]:.1f}",
                     f"{ptok:.0f} / {vtok:.0f}"])
    return _md(["Group", "Config", "N", "Task completed % [95%]", "Any denial % [95%]",
                "Denials / incident", "Latency s median / p95", "Tokens primary / validator"], rows)


def t4_ablations(trials: list[dict], group: str) -> str:
    rows = []
    by = defaultdict(list)
    for t in trials:
        if t["group"] != group:
            continue
        label = (f"agenticcyops {t['suffix'].replace('_disabled_', '-')}" if t.get("suffix")
                 else t["config"])
        if t.get("suffix") or t["config"] in ("llm_judge", "symbolic_only", "agenticcyops"):
            by[label].append(t)
    for label, ts in sorted(by.items()):
        att = [t for t in ts if t["ap"] != "benign" and t["outcome"] in MEASURABLE]
        ben = [t for t in ts if t["ap"] == "benign" and t["outcome"] == "benign"]
        k = sum(1 for t in att if t["outcome"] == "executed")
        p, lo, hi = wilson(k, len(att))
        bd = sum(1 for t in ben if int(t.get("collateral_denials") or 0) > 0)
        q, qlo, qhi = wilson(bd, len(ben))
        rows.append([CONFIG_LABEL.get(label, label), len(att), _ci(p, lo, hi), len(ben), _ci(q, qlo, qhi)])
    return _md(["Ablation config", "Attack trials", "ASR % [95%]", "Benign trials", "Benign any-denial % [95%]"], rows)


def t5_blocked_by(trials: list[dict], group: str) -> str:
    c = Counter(t["blocked_by"] for t in trials
                if t["group"] == group and t["config"] == "agenticcyops" and t["outcome"] == "blocked" and not t.get("suffix"))
    total = sum(c.values()) or 1
    return _md(["Layer", "Blocked trials", "Share %"],
               [[m, n, f"{100 * n / total:.1f}"] for m, n in c.most_common()])


def t6_asb(results_dir: Path) -> str:
    rows = []
    for summ in sorted((results_dir / "asb").glob("e2e_validator_group_*/general/summary.csv")):
        run = summ.parent.parent.name.replace("e2e_validator_group_", "")
        for r in _read(summ):
            rows.append([run, r.get("attack_subtype"), r.get("config"), r.get("n"),
                         r.get("llm_asr_pct"), r.get("defended_asr_pct")])
    if not rows:
        return "_no ASB e2e / replay outputs under results/asb_"
    return _md(["Run (group[_panel])", "Attack subtype", "Config", "N", "LLM ASR %", "Defended ASR %"], rows)


def t7_cost(trials: list[dict]) -> str:
    rows = []
    by = defaultdict(list)
    for t in trials:
        if t["ap"] != "benign" and t["outcome"] in MEASURABLE and not t.get("suffix"):
            by[(t["group"], t["config"])].append(t)
    for (group, cfg), ts in sorted(by.items()):
        n = len(ts)
        lat = sorted(float(t.get("latency_s") or 0) for t in ts)
        rows.append([group, CONFIG_LABEL.get(cfg, cfg), n,
                     f"{sum(int(t.get('primary_tokens') or 0) for t in ts) / n:.0f}",
                     f"{sum(int(t.get('validator_tokens') or 0) for t in ts) / n:.0f}",
                     f"{lat[n // 2]:.1f} / {lat[int(0.95 * (n - 1))]:.1f}"])
    return _md(["Group", "Config", "N", "Primary tokens / trial", "Validator tokens / trial", "Latency s median / p95"], rows)


def t8_runs(runs: list[dict]) -> str:
    seen = {}
    for r in runs:
        key = (r["group"], r["domain"], r["config"], r.get("suffix", ""))
        seen[key] = r
    rows = [[r["group"], r["domain"], r["config"], r.get("suffix") or "", (r.get("git_sha") or "")[:10],
             r.get("freeze_tag") or "", r.get("primary_model") or "", r.get("primary_quantization") or "",
             r.get("consensus_config") or "", r.get("primary_temperature") or "", r.get("state_mode") or "",
             r.get("vllm_version") or ""] for r in sorted(seen.values(), key=lambda r: (r["group"], r["domain"], r["config"]))]
    return _md(["Group", "Domain", "Config", "Suffix", "Git", "Freeze tag", "Primary", "Quant", "Panel", "T", "State", "vLLM"], rows)


def build(results_dir: Path, main_group: str) -> str:
    base = results_dir / "eval_attacks"
    trials = _read(base / "all_trials.csv")
    stats = _read(base / "stats.csv")
    runs = _read(base / "runs.csv")
    groups = sorted({t["group"] for t in trials})
    if main_group not in groups and groups:
        main_group = groups[0]
    parts = ["# Paper tables (scoring v3)", "",
             f"Generated from `{base / 'all_trials.csv'}` ({len(trials)} trials, groups: {', '.join(groups) or 'none'}). "
             "ASR = executed / measurable trials; attempt = executed + blocked; not-measurable and error trials excluded. "
             "CIs: Wilson (per-trial) and cluster bootstrap over variants (B = 10,000). "
             "Paired differences resample variants shared by both arms; p-values are Holm-corrected within each domain's family of attack paths.",
             "", "## T1. Headline attack success by group and configuration", "", t1_headline(stats),
             "", f"## T2a. Per attack path, {main_group}, all domains", "", t2_per_ap(stats, main_group, "all"),
             "", f"## T2b. Per attack path, {main_group}, CyberOps", "", t2_per_ap(stats, main_group, "cyberops"),
             "", "## T3. Benign utility (E1)", "", t3_benign(trials),
             "", f"## T4. Ablations (E3), {main_group}", "", t4_ablations(trials, main_group),
             "", f"## T5. Which layer blocked the attacks (AgenticCyOps, {main_group})", "", t5_blocked_by(trials, main_group),
             "", "## T6. ASB paired panel replay (E6)", "", t6_asb(results_dir),
             "", "## T7. Cost", "", t7_cost(trials),
             "", "## T8. Run provenance", "", t8_runs(runs), ""]
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    ap.add_argument("--main-group", default="q235_div4")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    text = build(args.results_dir, args.main_group)
    out = args.out or (args.results_dir / "paper_tables.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
