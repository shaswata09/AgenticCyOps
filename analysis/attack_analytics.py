"""
Attack Path Analytics — Paper-Ready PDF Reports and CSV.

Produces:
  1. Multi-page PDF with title, executive summary, charts, cross-group
     comparison, and auto-generated key findings.
  2. enhanced_attack_results.csv — one row per AP per config.
  3. cross_group_summary.csv — one row per AP per group (agenticcyops only).

Usage:
    python -m analysis.attack_analytics --domain cyberops --groups A
    python -m analysis.attack_analytics --domain cyberops --groups A,C,E,F
    python -m analysis.attack_analytics --domain cyberops --groups A --output results/eval_a/group_A/cyberops/
"""

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import seaborn as sns

from config import BASE_DIR

# ---------------------------------------------------------------------------
# Style constants — consistent with generate_report.py / baseline_analytics.py
# ---------------------------------------------------------------------------

sns.set_theme(style="whitegrid", font_scale=1.0, palette="muted")
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
})

CONFIGS = ["flat", "acl_hardened", "agenticcyops"]
CONFIG_LABELS = {"flat": "Flat MAS", "acl_hardened": "ACL-Hardened", "agenticcyops": "AgenticCyOps"}
CONFIG_COLORS = {"flat": "#e74c3c", "acl_hardened": "#f39c12", "agenticcyops": "#2ecc71"}

HEADER_COLOR = "#2c3e50"
ACCENT = "#2980b9"

# ---------------------------------------------------------------------------
# AP metadata
# ---------------------------------------------------------------------------

AP_NAMES = {
    "ap1":  "AP-1 Tool Redirection (TA-1)",
    "ap2":  "AP-2 Memory Poisoning (MA-3)",
    "ap3":  "AP-3 Confused Deputy (TA-2,3)",
    "ap4":  "AP-4 Cross-Phase Exfiltration (MA-1,7)",
    "ap5":  "AP-5 Bulk Irreversible (TA-5)",
    "ap6":  "AP-6 Replay Attack (TA-8)",
    "ap7":  "AP-7 Action Chain (TA-6,10)",
    "ap8":  "AP-8 Parameter Manipulation (TA-4)",
    "ap9":  "AP-9 Handoff Poisoning (TA-11,20)",
    "ap10": "AP-10 Validator Manipulation (TA-12,21)",
    "ap11": "AP-11 Operational Context (TA-15-18)",
    "ap12": "AP-12 Concurrent Bypass (TA-19,22)",
    "ap13": "AP-13 Adversarial Memory (MA-4-6,12)",
    "ap14": "AP-14 Read Injection (MA-9,2)",
    "ap15": "AP-15 Infrastructure Integrity (TA-13-14,MA-10-11,CA-1)",
}

AP_SHORT = {
    "ap1": "AP-1", "ap2": "AP-2", "ap3": "AP-3", "ap4": "AP-4", "ap5": "AP-5",
    "ap6": "AP-6", "ap7": "AP-7", "ap8": "AP-8", "ap9": "AP-9", "ap10": "AP-10",
    "ap11": "AP-11", "ap12": "AP-12", "ap13": "AP-13", "ap14": "AP-14", "ap15": "AP-15",
}

ALL_APS = [f"ap{i}" for i in range(1, 16)]


def _ap_sort_key(ap: str) -> int:
    """Extract numeric part for sorting: ap1 -> 1, ap15 -> 15."""
    m = re.search(r"(\d+)", ap)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Mechanism -> Principle mapping
# ---------------------------------------------------------------------------

def _mechanism_to_principle(mechanism: str) -> str:
    """Map a blocking mechanism string to the principle that caught it."""
    if not mechanism or mechanism == "none":
        return "none"
    m = mechanism.upper()
    if m.startswith("P1") or "IDENTITY" in m or "AUTH" in m:
        return "P1"
    if m.startswith("P2") or "CAPABILITY" in m or "MANIFEST" in m:
        return "P2"
    if m.startswith("P3") or "CONSENSUS" in m or "VERIFIED" in m or "BLOCKED" in m or "REPLAY" in m:
        return "P3"
    if m.startswith("P4") or "SIMILARITY" in m or "EMBEDDING" in m or "WRITE" in m:
        return "P4"
    if m.startswith("P5") or "INJECTION" in m or "SANITIZ" in m or "READ" in m:
        return "P5"
    if "ACL" in m:
        return "ACL"
    return "other"


def _primary_principle(mechanisms: list[str]) -> str:
    """Determine the most common principle across a list of mechanisms."""
    counts: dict[str, int] = defaultdict(int)
    for mech in mechanisms:
        p = _mechanism_to_principle(mech)
        if p not in ("none", "other", "ACL"):
            counts[p] += 1
    if not counts:
        return "N/A"
    return max(counts, key=counts.get)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_results(domain: str, group: str) -> list[dict]:
    """Load results.csv for a given domain and group.

    Expected path: results/eval_a/group_{group}/{domain}/results.csv
    CSV columns: Domain,AP,Variant,Trial,Config,Group,Succeeded,Step,Mechanism
    """
    path = BASE_DIR / "results" / "eval_a" / f"group_{group}" / domain / "results.csv"
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return []
    rows = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["Succeeded"] = row["Succeeded"].strip() == "True"
            try:
                row["Step"] = int(row["Step"])
            except (ValueError, TypeError):
                row["Step"] = 0
            try:
                row["Variant"] = int(row["Variant"])
            except (ValueError, TypeError):
                row["Variant"] = 0
            rows.append(row)
    return rows


def load_multi_group(domain: str, groups: list[str]) -> dict[str, list[dict]]:
    """Load results for multiple groups. Returns {group: [rows]}."""
    data = {}
    for g in groups:
        rows = load_results(domain, g)
        if rows:
            data[g] = rows
    return data


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _compute_ap_config_stats(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Aggregate rows by (AP, Config).

    Returns {(ap, config): {trials, succeeded, blocked, asr, avg_step,
                             primary_mechanism, vectors, mechanisms_list}}
    """
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["AP"].lower(), r["Config"])
        buckets[key].append(r)

    stats = {}
    for (ap, config), trials in buckets.items():
        n = len(trials)
        succ = sum(1 for t in trials if t["Succeeded"])
        blocked = n - succ
        asr = round(succ / n * 100, 1) if n else 0.0
        steps = [t["Step"] for t in trials if not t["Succeeded"] and t["Step"] > 0]
        avg_step = round(sum(steps) / len(steps), 1) if steps else 0.0
        mechanisms = [t["Mechanism"] for t in trials if not t["Succeeded"] and t["Mechanism"] != "none"]
        variants_tested = len(set(t["Variant"] for t in trials))
        primary = _primary_principle(mechanisms)

        # Most common mechanism string
        mech_counts: dict[str, int] = defaultdict(int)
        for m in mechanisms:
            mech_counts[m] += 1
        primary_mech = max(mech_counts, key=mech_counts.get) if mech_counts else "none"

        stats[(ap, config)] = {
            "trials": n,
            "succeeded": succ,
            "blocked": blocked,
            "asr": asr,
            "avg_interception_step": avg_step,
            "primary_mechanism": primary_mech,
            "primary_principle": primary,
            "vectors_tested": variants_tested,
            "mechanisms_list": mechanisms,
        }
    return stats


def _compute_variant_asr(rows: list[dict], config: str = "agenticcyops") -> dict[tuple[str, int], float]:
    """Compute ASR per (AP, variant) for a given config.

    Returns {(ap, variant): asr_pct}
    """
    buckets: dict[tuple[str, int], list[bool]] = defaultdict(list)
    for r in rows:
        if r["Config"] != config:
            continue
        key = (r["AP"].lower(), r["Variant"])
        buckets[key].append(r["Succeeded"])

    result = {}
    for (ap, variant), outcomes in buckets.items():
        n = len(outcomes)
        result[(ap, variant)] = round(sum(outcomes) / n * 100, 1) if n else 0.0
    return result


# ---------------------------------------------------------------------------
# CSV outputs
# ---------------------------------------------------------------------------

def write_enhanced_csv(stats: dict[tuple[str, str], dict], domain: str,
                       group: str, output_dir: Path):
    """Write enhanced_attack_results.csv — one row per AP per config."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "enhanced_attack_results.csv"
    fieldnames = [
        "ap", "ap_name", "config", "group", "domain", "trials", "succeeded",
        "blocked", "asr", "avg_interception_step", "primary_mechanism",
        "primary_principle", "vectors_tested",
    ]
    rows_out = []
    for ap in ALL_APS:
        for config in CONFIGS:
            s = stats.get((ap, config))
            if s is None:
                continue
            rows_out.append({
                "ap": ap,
                "ap_name": AP_NAMES.get(ap, ap),
                "config": config,
                "group": group,
                "domain": domain,
                "trials": s["trials"],
                "succeeded": s["succeeded"],
                "blocked": s["blocked"],
                "asr": s["asr"],
                "avg_interception_step": s["avg_interception_step"],
                "primary_mechanism": s["primary_mechanism"],
                "primary_principle": s["primary_principle"],
                "vectors_tested": s["vectors_tested"],
            })

    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"  CSV written: {path} ({len(rows_out)} rows)")


def write_cross_group_csv(group_data: dict[str, list[dict]], domain: str,
                          output_dir: Path):
    """Write cross_group_summary.csv — one row per AP per group, agenticcyops only."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "cross_group_summary.csv"
    fieldnames = ["ap", "ap_name", "group", "domain", "trials", "succeeded",
                  "blocked", "asr", "primary_mechanism"]
    rows_out = []
    for grp, rows in sorted(group_data.items()):
        stats = _compute_ap_config_stats(rows)
        for ap in ALL_APS:
            s = stats.get((ap, "agenticcyops"))
            if s is None:
                continue
            rows_out.append({
                "ap": ap,
                "ap_name": AP_NAMES.get(ap, ap),
                "group": grp,
                "domain": domain,
                "trials": s["trials"],
                "succeeded": s["succeeded"],
                "blocked": s["blocked"],
                "asr": s["asr"],
                "primary_mechanism": s["primary_mechanism"],
            })

    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"  CSV written: {path} ({len(rows_out)} rows)")


# ---------------------------------------------------------------------------
# PDF Pages
# ---------------------------------------------------------------------------

def _page_title(pdf, domain: str, group_str: str, total_trials: int):
    """Page 1: Title page."""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")

    ax.text(0.5, 0.72, "AgenticCyOps", transform=ax.transAxes,
            ha="center", fontsize=36, fontweight="bold", color=HEADER_COLOR)
    ax.text(0.5, 0.62, "Attack Path Evaluation Report", transform=ax.transAxes,
            ha="center", fontsize=22, color="#7f8c8d")

    ax.plot([0.2, 0.8], [0.56, 0.56], transform=ax.transAxes,
            color=ACCENT, linewidth=2)

    ax.text(0.5, 0.48, f"Domain: {domain.title()}", transform=ax.transAxes,
            ha="center", fontsize=18, color=ACCENT)
    ax.text(0.5, 0.40, f"Group(s): {group_str}", transform=ax.transAxes,
            ha="center", fontsize=14, color="#7f8c8d")
    ax.text(0.5, 0.33, datetime.now().strftime("%B %d, %Y"), transform=ax.transAxes,
            ha="center", fontsize=14, color="#95a5a6")
    ax.text(0.5, 0.26, f"Total trials: {total_trials:,}", transform=ax.transAxes,
            ha="center", fontsize=14, color="#95a5a6")

    ax.text(0.5, 0.12, "Securing Multi-Agentic AI Integration in Enterprise Cyber Operations",
            transform=ax.transAxes, ha="center", fontsize=10, style="italic", color="#bdc3c7")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_executive_summary(pdf, stats: dict[tuple[str, str], dict], domain: str):
    """Page 2: Executive summary table with color-coded ASR."""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.set_title(f"Executive Summary — {domain.title()}", fontsize=18,
                 fontweight="bold", color=HEADER_COLOR, pad=30)

    headers = ["AP", "Name", "Vectors", "Flat ASR", "ACL ASR", "ACyOps ASR",
               "Primary Defense", "Status"]

    cell_data = []
    for ap in ALL_APS:
        short = AP_SHORT.get(ap, ap)
        name = AP_NAMES.get(ap, ap)
        # Trim name: remove the AP-N prefix for table display
        display_name = name.split(" ", 1)[1] if " " in name else name

        flat_s = stats.get((ap, "flat"))
        acl_s = stats.get((ap, "acl_hardened"))
        aco_s = stats.get((ap, "agenticcyops"))

        flat_asr = f"{flat_s['asr']:.0f}%" if flat_s else "--"
        acl_asr = f"{acl_s['asr']:.0f}%" if acl_s else "--"
        aco_asr = f"{aco_s['asr']:.0f}%" if aco_s else "--"
        vectors = str(aco_s["vectors_tested"]) if aco_s else "--"
        defense = aco_s["primary_principle"] if aco_s else "--"

        aco_val = aco_s["asr"] if aco_s else 0
        if aco_val == 0:
            status = "BLOCKED"
        elif aco_val <= 10:
            status = "LOW RISK"
        else:
            status = "VULNERABLE"

        cell_data.append([short, display_name, vectors, flat_asr, acl_asr,
                          aco_asr, defense, status])

    table = ax.table(
        cellText=cell_data, colLabels=headers,
        cellLoc="center", loc="center",
        bbox=[0.01, 0.02, 0.98, 0.88],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    table.scale(1, 1.6)

    # Header styling
    for j in range(len(headers)):
        table[0, j].set_facecolor(HEADER_COLOR)
        table[0, j].set_text_props(color="white", fontweight="bold", fontsize=8)

    # Row styling
    for i in range(1, len(cell_data) + 1):
        table[i, 0].set_text_props(fontweight="bold")
        # Name column left-align
        table[i, 1].set_text_props(ha="left")

        # Color code agenticcyops ASR column (col 5)
        asr_text = cell_data[i - 1][5]
        try:
            asr_val = float(asr_text.replace("%", ""))
        except (ValueError, AttributeError):
            asr_val = -1

        if asr_val == 0:
            table[i, 5].set_facecolor("#d5f5e3")  # green
        elif 0 < asr_val <= 10:
            table[i, 5].set_facecolor("#fef9e7")  # yellow
        elif asr_val > 10:
            table[i, 5].set_facecolor("#fdedec")  # red

        # Status column coloring
        status = cell_data[i - 1][7]
        if status == "BLOCKED":
            table[i, 7].set_facecolor("#d5f5e3")
            table[i, 7].set_text_props(color="#27ae60", fontweight="bold")
        elif status == "LOW RISK":
            table[i, 7].set_facecolor("#fef9e7")
            table[i, 7].set_text_props(color="#f39c12", fontweight="bold")
        else:
            table[i, 7].set_facecolor("#fdedec")
            table[i, 7].set_text_props(color="#e74c3c", fontweight="bold")

        # Alternating row shade
        base = "#f8f9f9" if i % 2 == 0 else "white"
        for j in [0, 1, 2, 3, 4, 6]:
            table[i, j].set_facecolor(base)

    # Column widths
    col_widths = [0.06, 0.28, 0.06, 0.09, 0.09, 0.10, 0.12, 0.10]
    for j, w in enumerate(col_widths):
        for i in range(len(cell_data) + 1):
            table[i, j].set_width(w)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_existing_chart(pdf, chart_path: Path, title: str):
    """Embed an existing PNG chart as a PDF page."""
    if not chart_path.exists():
        print(f"  Chart not found, skipping: {chart_path}")
        return
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    img = plt.imread(str(chart_path))
    ax.imshow(img)
    ax.set_title(title, fontsize=16, fontweight="bold", color=HEADER_COLOR, pad=15)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_defense_effectiveness(pdf, stats: dict[tuple[str, str], dict], domain: str):
    """Page 5: Defense effectiveness by principle — stacked bar chart.

    X-axis = P1..P5, Y-axis = number of APs where that principle was primary blocker.
    """
    principle_ap_map: dict[str, list[str]] = defaultdict(list)
    for ap in ALL_APS:
        s = stats.get((ap, "agenticcyops"))
        if s is None:
            continue
        pp = s["primary_principle"]
        if pp in ("P1", "P2", "P3", "P4", "P5"):
            principle_ap_map[pp].append(AP_SHORT.get(ap, ap))

    principles = ["P1", "P2", "P3", "P4", "P5"]
    principle_labels = [
        "P1\nIdentity &\nResponse",
        "P2\nCapability\nScoping",
        "P3\nConsensus\nVerification",
        "P4\nMemory\nWrite Guard",
        "P5\nMemory\nRead Guard",
    ]
    counts = [len(principle_ap_map.get(p, [])) for p in principles]
    colors = ["#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#1abc9c"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(principle_labels, counts, color=colors, edgecolor="white",
                  linewidth=0.8, width=0.55)

    for bar, count, p in zip(bars, counts, principles):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                str(count), ha="center", va="bottom", fontsize=12, fontweight="bold")
        # Annotate which APs
        ap_list = principle_ap_map.get(p, [])
        if ap_list:
            ap_text = ", ".join(ap_list)
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                    ap_text, ha="center", va="center", fontsize=7,
                    color="white", fontweight="bold", wrap=True)

    ax.set_ylabel("Number of APs Blocked (Primary Defense)", fontsize=12)
    ax.set_title(f"Defense Effectiveness by Principle — {domain.title()}",
                 fontsize=14, fontweight="bold")
    ax.set_ylim(0, max(counts) + 2 if counts else 5)

    total_blocked = sum(counts)
    ax.text(0.98, 0.95, f"{total_blocked} of 15 APs assigned to P1-P5",
            transform=ax.transAxes, ha="right", va="top", fontsize=10,
            color=HEADER_COLOR, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ecf0f1", edgecolor=HEADER_COLOR))

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_variant_analysis(pdf, rows: list[dict], domain: str):
    """Page 6: Per-variant ASR table for agenticcyops."""
    variant_asr = _compute_variant_asr(rows, "agenticcyops")

    # Determine max variants
    all_variants = sorted(set(v for (_, v) in variant_asr.keys()))
    if not all_variants:
        all_variants = [1, 2, 3, 4, 5]

    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.set_title(f"Per-Variant ASR (AgenticCyOps) — {domain.title()}", fontsize=18,
                 fontweight="bold", color=HEADER_COLOR, pad=30)

    headers = ["AP"] + [f"v{v}" for v in all_variants] + ["Avg ASR"]

    cell_data = []
    for ap in ALL_APS:
        row_vals = [AP_SHORT.get(ap, ap)]
        variant_vals = []
        for v in all_variants:
            asr = variant_asr.get((ap, v))
            if asr is not None:
                row_vals.append(f"{asr:.0f}%")
                variant_vals.append(asr)
            else:
                row_vals.append("--")
        avg = round(sum(variant_vals) / len(variant_vals), 1) if variant_vals else 0.0
        row_vals.append(f"{avg:.1f}%")
        cell_data.append(row_vals)

    table = ax.table(
        cellText=cell_data, colLabels=headers,
        cellLoc="center", loc="center",
        bbox=[0.08, 0.05, 0.84, 0.82],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)

    for j in range(len(headers)):
        table[0, j].set_facecolor(HEADER_COLOR)
        table[0, j].set_text_props(color="white", fontweight="bold", fontsize=9)

    for i in range(1, len(cell_data) + 1):
        table[i, 0].set_text_props(fontweight="bold")
        base = "#f8f9f9" if i % 2 == 0 else "white"
        for j in range(len(headers)):
            table[i, j].set_facecolor(base)
        # Color code variant cells
        for j in range(1, len(headers)):
            text = cell_data[i - 1][j]
            try:
                val = float(text.replace("%", ""))
            except (ValueError, AttributeError):
                continue
            if val == 0:
                table[i, j].set_facecolor("#d5f5e3")
            elif val > 0 and val <= 10:
                table[i, j].set_facecolor("#fef9e7")
            elif val > 10:
                table[i, j].set_facecolor("#fdedec")

    # Identify most effective variant
    best_variant = None
    best_avg = -1
    for v in all_variants:
        vals = [variant_asr.get((ap, v), 0) for ap in ALL_APS
                if (ap, v) in variant_asr]
        if vals:
            avg = sum(vals) / len(vals)
            if avg > best_avg:
                best_avg = avg
                best_variant = v

    if best_variant is not None and best_avg > 0:
        ax.text(0.5, 0.92, f"Most effective attack strategy: v{best_variant} "
                f"(avg ASR {best_avg:.1f}%)",
                transform=ax.transAxes, ha="center", fontsize=11,
                color="#e74c3c", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#fdedec",
                          edgecolor="#e74c3c"))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_mechanism_breakdown(pdf, stats: dict[tuple[str, str], dict], domain: str):
    """Page 7: Enhanced horizontal bar chart of blocking mechanisms."""
    mech_counts: dict[str, int] = defaultdict(int)
    for ap in ALL_APS:
        s = stats.get((ap, "agenticcyops"))
        if s is None:
            continue
        for m in s["mechanisms_list"]:
            if m and m != "none":
                mech_counts[m] += 1

    if not mech_counts:
        return

    # Sort by count descending
    sorted_mechs = sorted(mech_counts.items(), key=lambda x: x[1], reverse=True)
    labels = [m for m, _ in sorted_mechs]
    values = [c for _, c in sorted_mechs]

    # Assign colors by principle
    bar_colors = []
    for m in labels:
        p = _mechanism_to_principle(m)
        color_map = {
            "P1": "#3498db", "P2": "#e67e22", "P3": "#2ecc71",
            "P4": "#9b59b6", "P5": "#1abc9c", "ACL": "#95a5a6",
        }
        bar_colors.append(color_map.get(p, "#bdc3c7"))

    fig, ax = plt.subplots(figsize=(11, max(6, len(labels) * 0.4 + 2)))
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=bar_colors, edgecolor="white", height=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Interceptions", fontsize=12)
    ax.set_title(f"Blocking Mechanism Breakdown (AgenticCyOps) — {domain.title()}",
                 fontsize=14, fontweight="bold")

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold")

    # Legend
    import matplotlib.patches as mpatches
    legend_items = []
    for p, color in [("P1", "#3498db"), ("P2", "#e67e22"), ("P3", "#2ecc71"),
                     ("P4", "#9b59b6"), ("P5", "#1abc9c")]:
        legend_items.append(mpatches.Patch(color=color, label=p))
    ax.legend(handles=legend_items, loc="lower right", fontsize=9, frameon=True)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_cross_group(pdf, group_data: dict[str, list[dict]], domain: str):
    """Page 8: Cross-group comparison of ASR per AP (agenticcyops only)."""
    groups = sorted(group_data.keys())
    if len(groups) < 2:
        return

    # Build matrix: rows=APs, cols=groups
    matrix = np.zeros((len(ALL_APS), len(groups)))
    for j, grp in enumerate(groups):
        stats = _compute_ap_config_stats(group_data[grp])
        for i, ap in enumerate(ALL_APS):
            s = stats.get((ap, "agenticcyops"))
            matrix[i, j] = s["asr"] if s else 0.0

    fig, ax = plt.subplots(figsize=(11, 8.5))

    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)

    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f"Group {g}" for g in groups], fontsize=11)
    ax.set_yticks(range(len(ALL_APS)))
    ax.set_yticklabels([AP_SHORT[ap] for ap in ALL_APS], fontsize=10)

    # Annotate cells
    for i in range(len(ALL_APS)):
        for j in range(len(groups)):
            val = matrix[i, j]
            color = "white" if val > 50 else "black"
            ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                    fontsize=9, fontweight="bold", color=color)

    ax.set_title(f"Cross-Group ASR Comparison (AgenticCyOps) — {domain.title()}",
                 fontsize=14, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Attack Success Rate (%)", fontsize=10)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _page_key_findings(pdf, stats: dict[tuple[str, str], dict],
                       group_data: dict[str, list[dict]], domain: str):
    """Page 9: Auto-generated key findings."""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.set_title("Key Findings", fontsize=18, fontweight="bold",
                 color=HEADER_COLOR, pad=30)

    findings = []

    # Gather agenticcyops ASR per AP
    asr_map: dict[str, float] = {}
    for ap in ALL_APS:
        s = stats.get((ap, "agenticcyops"))
        if s:
            asr_map[ap] = s["asr"]

    # 1. Fully blocked count
    fully_blocked = sum(1 for v in asr_map.values() if v == 0)
    findings.append(f"{fully_blocked} of 15 APs fully blocked (0% ASR) under AgenticCyOps")

    # 2. Average ASR
    if asr_map:
        avg_asr = round(sum(asr_map.values()) / len(asr_map), 1)
        findings.append(f"Average ASR across all APs: {avg_asr}%")

    # 3. Most effective defense layer
    principle_block_counts: dict[str, int] = defaultdict(int)
    for ap in ALL_APS:
        s = stats.get((ap, "agenticcyops"))
        if s:
            for m in s["mechanisms_list"]:
                p = _mechanism_to_principle(m)
                if p in ("P1", "P2", "P3", "P4", "P5"):
                    principle_block_counts[p] += 1
    if principle_block_counts:
        best_p = max(principle_block_counts, key=principle_block_counts.get)
        findings.append(
            f"Most effective defense layer: {best_p} "
            f"(blocked {principle_block_counts[best_p]} attack trials)")

    # 4. Weakest AP
    if asr_map:
        weakest_ap = max(asr_map, key=asr_map.get)
        weakest_asr = asr_map[weakest_ap]
        if weakest_asr > 0:
            findings.append(
                f"Weakest AP: {AP_SHORT[weakest_ap]} at {weakest_asr}% ASR")
        else:
            findings.append("All APs fully blocked (0% ASR)")

    # 5. Cross-group observations
    groups = sorted(group_data.keys())
    if len(groups) > 1:
        for grp in groups:
            grp_stats = _compute_ap_config_stats(group_data[grp])
            for ap in ALL_APS:
                s = grp_stats.get((ap, "agenticcyops"))
                if s and s["asr"] > 10:
                    findings.append(
                        f"Group {grp} shows {s['asr']:.0f}% ASR on "
                        f"{AP_SHORT[ap]} ({AP_NAMES[ap].split('(')[0].strip()})")

    # Render findings
    y = 0.82
    for i, finding in enumerate(findings):
        if "fully blocked" in finding.lower() or "0% ASR" in finding.lower():
            color = "#27ae60"
            marker = "+"
        elif "weakest" in finding.lower() or "vulnerable" in finding.lower():
            color = "#e74c3c"
            marker = "!"
        elif "shows" in finding.lower() and "ASR" in finding:
            color = "#e67e22"
            marker = ">"
        else:
            color = HEADER_COLOR
            marker = "-"

        ax.text(0.06, y, f"  {marker}  {finding}", transform=ax.transAxes,
                fontsize=12, color=color, verticalalignment="top",
                fontfamily="sans-serif")
        y -= 0.065

    # Footer
    ax.text(0.5, 0.06, f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            transform=ax.transAxes, ha="center", fontsize=10, color="#bdc3c7")
    ax.text(0.5, 0.02,
            f"Domain: {domain.title()} | Groups: {', '.join(groups)} | APs: 15 | Configs: 3",
            transform=ax.transAxes, ha="center", fontsize=10, color="#bdc3c7")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main PDF assembly
# ---------------------------------------------------------------------------

def generate_report(domain: str, groups: list[str], output_dir: Path):
    """Generate the full attack analytics PDF and CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    group_data = load_multi_group(domain, groups)
    if not group_data:
        print(f"  No data found for {domain} groups {groups}")
        return

    # Use first group as primary for single-group pages
    primary_group = groups[0]
    primary_rows = group_data.get(primary_group, [])
    if not primary_rows:
        primary_group = next(iter(group_data))
        primary_rows = group_data[primary_group]

    stats = _compute_ap_config_stats(primary_rows)
    total_trials = sum(len(rows) for rows in group_data.values())
    group_str = ", ".join(sorted(group_data.keys()))

    print(f"\n{'=' * 60}")
    print(f"  Attack Analytics: {domain.title()} (Groups: {group_str})")
    print(f"{'=' * 60}")

    # --- CSVs ---
    write_enhanced_csv(stats, domain, primary_group, output_dir)
    if len(group_data) > 1:
        write_cross_group_csv(group_data, domain, output_dir)

    # --- Locate existing charts ---
    chart_dir = BASE_DIR / "results" / "eval_a" / f"group_{primary_group}" / domain

    # --- Build PDF ---
    pdf_path = output_dir / "attack_analytics.pdf"
    with PdfPages(str(pdf_path)) as pdf:
        # Page 1: Title
        _page_title(pdf, domain, group_str, total_trials)

        # Page 2: Executive Summary Table
        _page_executive_summary(pdf, stats, domain)

        # Page 3: ASR Bar Chart (existing)
        _page_existing_chart(pdf, chart_dir / "asr_by_ap.png",
                             "Attack Success Rate by Attack Path")

        # Page 4: Interception Heatmap (existing)
        _page_existing_chart(pdf, chart_dir / "interception_heatmap.png",
                             "Interception Step Heatmap")

        # Page 5: Defense Effectiveness by Principle
        _page_defense_effectiveness(pdf, stats, domain)

        # Page 6: Per-Variant Analysis
        _page_variant_analysis(pdf, primary_rows, domain)

        # Page 7: Enhanced Mechanism Breakdown
        _page_mechanism_breakdown(pdf, stats, domain)

        # Page 8: Cross-Group Comparison
        if len(group_data) > 1:
            _page_cross_group(pdf, group_data, domain)

        # Page 9: Key Findings
        _page_key_findings(pdf, stats, group_data, domain)

    page_count = 9 if len(group_data) > 1 else 8
    print(f"  PDF saved: {pdf_path} ({page_count} pages)")

    # --- Summary printout ---
    print(f"\n  --- ASR Summary (AgenticCyOps, Group {primary_group}) ---")
    for ap in ALL_APS:
        s = stats.get((ap, "agenticcyops"))
        if s:
            status = "BLOCKED" if s["asr"] == 0 else f"{s['asr']}%"
            print(f"  {AP_SHORT[ap]:>6}: ASR={status:>8}  "
                  f"({s['succeeded']}/{s['trials']} succeeded)  "
                  f"via {s['primary_mechanism']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Attack Path Analytics — Paper-Ready PDF Reports and CSV"
    )
    parser.add_argument("--domain", default="cyberops",
                        help="Domain to analyze (default: cyberops)")
    parser.add_argument("--groups", default="A",
                        help="Comma-separated group list: A,C,E,F")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: results/eval_a/group_{first}/domain/)")
    args = parser.parse_args()

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = (BASE_DIR / "results" / "eval_a" /
                      f"group_{groups[0]}" / args.domain)

    generate_report(args.domain, groups, output_dir)


if __name__ == "__main__":
    main()
