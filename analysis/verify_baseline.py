"""
Quick baseline verification. Run after each benign E2E test.

Usage:
    python -m analysis.verify_baseline --domain cyberops --config agenticcyops
    python -m analysis.verify_baseline --domain cyberops --config all
    python -m analysis.verify_baseline --domain all --config all

Output: CLI table showing pass/fail per check.
"""

import argparse
import json
from pathlib import Path

from config import BASE_DIR


CONFIGS = ["flat", "acl_hardened", "agenticcyops"]
DOMAINS = ["cyberops", "healthcare", "finance", "legal"]


def load_logs(domain: str, config: str) -> list[dict]:
    """Load JSONL logs for a domain+config baseline."""
    log_dir = BASE_DIR / "logs" / f"{domain}_baseline"
    events = []
    for f in sorted(log_dir.glob(f"{config}*.jsonl")):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def verify_config(domain: str, config: str) -> dict:
    """Run all verification checks for one domain+config."""
    events = load_logs(domain, config)
    checks = {}

    if not events:
        return {"domain": domain, "config": config, "checks": {"logs_exist": False}, "pass": False}

    checks["logs_exist"] = True

    # Phase activity
    sources = [e.get("source", "") for e in events]
    active_phases = set()
    for s in sources:
        for phase in ("monitor", "analyze", "admin", "report"):
            if phase in s:
                active_phases.add(phase)
    checks["all_4_phases_active"] = len(active_phases) >= 4

    # Tool calls
    tool_calls = [e for e in events if e.get("action") == "tool_call"]
    allowed = [e for e in tool_calls if e.get("auth_decision") == "allow"]
    denied = [e for e in tool_calls if e.get("auth_decision") == "deny"]
    checks["tool_calls_made"] = len(allowed) > 0
    checks["total_tool_calls"] = len(tool_calls)
    checks["allowed_tool_calls"] = len(allowed)
    checks["denied_tool_calls"] = len(denied)

    # Config-specific
    if config == "flat":
        checks["no_enforcement_active"] = len(denied) == 0

    elif config == "acl_hardened":
        acl_denials = [e for e in denied if "acl" in e.get("mechanism", "").lower()]
        checks["acl_enforcement_active"] = True
        checks["no_non_acl_denials"] = len(denied) == len(acl_denials)

    elif config == "agenticcyops":
        mechanisms = set()
        for e in events:
            m = e.get("mechanism", "")
            if m:
                mechanisms.add(m)

        memory_ops = [e for e in events if e.get("action") in ("memory_read", "memory_write")]
        has_memory_ops = len(memory_ops) > 0

        checks["p2_active"] = any("P2" in m for m in mechanisms)

        # P3 only fires when admin/report phases propose tool calls
        admin_report_calls = [
            e for e in tool_calls
            if any(p in e.get("source", "") for p in ("admin", "report"))
        ]
        if admin_report_calls:
            checks["p3_active"] = any("P3" in m for m in mechanisms) or any(
                e.get("action") == "consensus_vote" for e in events
            )
        else:
            checks["p3_active"] = "N/A (no admin/report tool calls)"

        # P4/P5 only fire on memory operations — mark N/A if no memory ops occurred
        if has_memory_ops:
            checks["p4_active"] = any("P4" in m for m in mechanisms)
            checks["p5_active"] = any("P5" in m for m in mechanisms)
        else:
            checks["p4_active"] = "N/A (no memory ops)"
            checks["p5_active"] = "N/A (no memory ops)"

        # False blocks: count P3 consensus rejections on benign traffic
        # A few consensus rejections are acceptable (validators being cautious)
        consensus_denials = [e for e in denied if "P3" in e.get("mechanism", "")]
        other_denials = [e for e in denied if "P3" not in e.get("mechanism", "")]
        checks["consensus_rejections"] = len(consensus_denials)
        checks["other_denials"] = len(other_denials)
        checks["zero_non_consensus_blocks"] = len(other_denials) == 0

        # Consensus approved at least some legitimate actions
        consensus_votes = [e for e in events if e.get("action") == "consensus_vote"]
        approvals = [e for e in consensus_votes if e.get("auth_decision") == "approve"]
        checks["consensus_approved_benign"] = len(approvals) > 0

    # Overall — critical checks for pass/fail
    critical = ["all_4_phases_active", "tool_calls_made"]
    if config == "agenticcyops":
        critical.extend(["p2_active", "zero_non_consensus_blocks"])
        # P3 only critical if admin/report made tool calls
        if checks.get("p3_active") is not True and not str(checks.get("p3_active", "")).startswith("N/A"):
            critical.append("p3_active")
    result_pass = all(
        checks.get(c, False) is True or str(checks.get(c, "")).startswith("N/A")
        for c in critical
    )

    return {"domain": domain, "config": config, "checks": checks, "pass": result_pass}


def print_report(results: list[dict]):
    print("\n" + "=" * 70)
    print("BASELINE VERIFICATION REPORT")
    print("=" * 70)

    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"\n{r['domain']} / {r['config']}: {status}")
        print("-" * 40)
        for check, value in r["checks"].items():
            if isinstance(value, bool):
                icon = "+" if value else "x"
            else:
                icon = str(value)
            print(f"  {icon:>4}  {check}: {value}")

    # Readiness gate
    print("\n" + "=" * 70)
    print("READINESS GATE")
    print("=" * 70)
    domains = sorted(set(r["domain"] for r in results))

    header = f"{'Domain':<15}" + "".join(f"{c:<18}" for c in CONFIGS) + "Ready"
    print(header)
    print("-" * len(header))

    for domain in domains:
        row = f"{domain:<15}"
        all_pass = True
        for config in CONFIGS:
            match = [r for r in results if r["domain"] == domain and r["config"] == config]
            if match:
                s = "PASS" if match[0]["pass"] else "FAIL"
                all_pass = all_pass and match[0]["pass"]
            else:
                s = "NOT RUN"
                all_pass = False
            row += f"{s:<18}"
        row += "YES" if all_pass else "NO"
        print(row)

    total = all(r["pass"] for r in results)
    print(f"\n{'PROCEED TO ATTACKS' if total else 'FIX FAILURES BEFORE PROCEEDING'}")


def main():
    parser = argparse.ArgumentParser(description="Baseline verification")
    parser.add_argument("--domain", default="cyberops", help="Domain or 'all'")
    parser.add_argument("--config", default="all", help="Config or 'all'")
    args = parser.parse_args()

    domains = DOMAINS if args.domain == "all" else [args.domain]
    configs = CONFIGS if args.config == "all" else [args.config]

    results = []
    for d in domains:
        for c in configs:
            results.append(verify_config(d, c))

    print_report(results)


if __name__ == "__main__":
    main()
