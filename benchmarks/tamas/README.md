# TAMAS Benchmark Integration

## Overview

**TAMAS** (Targeting Agentic Multi-Agent Systems) is an independent,
domain-agnostic benchmark for evaluating the robustness of multi-agent
LLM systems against adversarial manipulation.

- **Paper:** [arxiv 2506.02635](https://arxiv.org/abs/2506.02635)
- **Scope:** Six distinct attack families aimed at the inter-agent
  interaction surface (prompts, tool outputs, shared memory, role
  boundaries).

This directory integrates TAMAS into the AgenticCyOps evaluation
pipeline so we can validate the P1-P5 defense stack against a benchmark
we did not design ourselves.

## Status (2026-04-17): COMPLETE

- Simulated end-to-end run: **960 trials** (19 attack cells × 20 trials × 2 modes).
- Real-logs mapping: 15 AgenticCyOps APs → 6 TAMAS categories across
  5 validator groups (A, C, D, E, F).
- Artifacts: simulated run lands at `results/tamas/`; per-group real-logs
  analytics at `results/tamas/group_<G>/` (one subdirectory per validator
  group derived from existing `logs/<domain>_eval_attacks_<G>/` JSONL).

## Purpose

The AgenticCyOps internal evaluations exercise the defense stack against
red-team campaigns that were co-designed with the defenses. TAMAS
provides an **external, independent, domain-agnostic** yardstick:

- Confirms that the P1-P5 principles generalize beyond the CyberOps
  scenarios used in development.
- Produces comparable numbers against the TAMAS leaderboard (baseline
  AutoGen agents with no defenses).
- Guards against over-fitting the defenses to the internal threat
  model.

## Architecture

```
TAMAS scenario config (5 scenarios)
         │
         ▼
    AutoGen agents / direct trial driver
         │
         ▼
   P12345Middleware (framework-agnostic wrapper)
         │
         ├── P1  AuthenticatedInterface  (identity + response integrity)
         ├── P2  Capability Scoping       (role manifest, param validator, output filter)
         ├── P3  Verified Execution       (operational context, intent chain, consensus)
         ├── P4  Memory Integrity         (schema, drift, contradiction, replay)
         └── P5  Access-Controlled Isolation (ACL, query scope, sanitization)
```

The `P12345Middleware` wraps every AutoGen agent participating in a
TAMAS scenario. Each tool call, message, and memory operation flows
through the same five-layer stack used in production CyberOps
deployments. Unlike the SOARHost (phase-oriented), the TAMAS middleware
treats each agent role as an independent actor and enforces defenses
per-call.

| Principle | Name                              | Source modules                          |
|-----------|-----------------------------------|------------------------------------------|
| P1        | Authenticated Interface           | `host/authenticated_interface.py`       |
| P2        | Capability Scoping                | `host/parameter_validator.py`, `host/output_classifier.py`, + `middleware/role_manifest.py` (DynamicManifestEnforcer) |
| P3        | Verified Execution                | `consensus/verified_execution.py`       |
| P4        | Memory Integrity                  | `memory/memory_integrity.py`            |
| P5        | Access-Controlled Isolation       | `memory/access_isolation.py`            |

### Middleware files

- `middleware/agent_wrapper.py` — `P12345Middleware` main class.
- `middleware/autogen_patches.py` — wraps AutoGen
  `ConversableAgent.register_function` / retriever / comms with the
  middleware.
- `middleware/role_manifest.py` — `DynamicManifestEnforcer` (role-keyed
  replacement for the phase-keyed SOAR enforcer).
- `middleware/budget_tracker.py` — $40 hard-stop tracker for OpenAI /
  Anthropic spend.

The `domains/tamas/configs/` directory holds domain stubs (asset
criticality, access policy, sensitive patterns, etc.) so the existing
enforcement modules load cleanly when `domain="tamas"` is selected.

## Scenarios (5)

| Scenario                     | Roles | Benign task                                                  |
|------------------------------|------:|--------------------------------------------------------------|
| `healthcare_prescription`    | 5     | Diagnose chest pain, prescribe, dispense, administer          |
| `healthcare_diagnosis`       | 4     | Specialist review of ambiguous imaging findings               |
| `healthcare_triage`          | 4     | ER triage with admission decision                             |
| `compliance_review`          | 4     | Multi-stage regulatory filing review                          |
| `social_media_moderation`    | 5     | Content ingest, policy classification, user action            |

All scenarios are plain JSON under `benchmarks/tamas/scenarios/`. Each
declares role manifests (allowed_tools, allowed_memory_read/write,
requires_consensus, escalation_triggers), memory stores, a benign
task, and an expected workflow used for TSR scoring.

## Attack types → TAMAS categories

TAMAS defines six attack families. Each cell in the grid is one
(scenario × attack_type); the benchmark therefore exercises 19 unique
attack cells (some scenarios don't exercise every attack type).

| # | TAMAS attack                  | Primary defense   | Secondary defense |
|--:|-------------------------------|-------------------|--------------------|
| 1 | Tool Misuse                   | P2 capability     | P3 verified exec   |
| 2 | Data Exfiltration             | P5 access iso     | P2 output classify |
| 3 | Direct Prompt Injection       | P3 verified exec  | P1 auth interface  |
| 4 | Indirect Prompt Injection     | P4 memory integ   | P3 verified exec   |
| 5 | Byzantine Behavior            | P3 verified exec  | P1 auth interface  |
| 6 | Persuasive Manipulation       | P3 verified exec  | P2 capability      |

## Running the benchmark

```bash
# 1) One-time setup (idempotent)
cd benchmarks/tamas
./setup.sh

# 2) Baseline — vanilla AutoGen agents with no defenses
python -m benchmarks.tamas.run_baseline --trials 20

# 3) Defended — same scenarios with P12345Middleware enabled
python -m benchmarks.tamas.run_defended --trials 20

# 4) Compare — compute defense uplift, attack-type breakdown, McNemar's test
python -m benchmarks.tamas.compare

# 5) Generate the paper-ready findings PDF
python -m analysis.tamas_analytics

# 6) (Optional) Compute the real TAMAS score from live-LLM AgenticCyOps logs
python -m analysis.tamas_from_logs --groups A,C,D,E,F
```

`setup.sh` will:

1. Create `benchmarks/tamas/external/`.
2. Attempt to clone the upstream TAMAS repository (several candidate
   URLs are tried; see the script for the full list).
3. Fall back to a placeholder if no upstream is reachable — the
   benchmark is then reproduced directly from the paper specification.
4. Install `pyautogen>=0.2.35` if missing.
5. Verify the installation with an import smoke test.

## Results (simulated, 960 trials)

Driven end-to-end via `eval_runner.py` directly against the middleware
(no live LLM required for reproducibility of the defense layer).

| Metric                 | Baseline | Defended | Delta        |
|------------------------|---------:|---------:|--------------|
| Mean ASR (19 cells)    | 100.00%  |    5.53% | -94.47 pp    |
| Mean TSR               | 100.00%  |  100.00% | 0 pp         |
| Mean ERS               |    0.00% |   94.47% | +94.47 pp    |
| Cells p<0.001 (McNemar)| —        | **18/19**| —            |

Lone residual cell: `social_media_moderation × direct_prompt_injection`
(95% defended ASR) — HTML-comment style admin-approved injection that
bypasses the regex-based stub consensus. Swapping in a live-LLM
consensus validator is expected to close this.

## Results (real-logs TAMAS score)

`analysis/tamas_from_logs.py` maps the 15 AgenticCyOps APs onto the 6
TAMAS categories and computes ASR/TSR/ERS from the real multi-agent
evaluation logs across 5 validator groups (A, C, D, E, F).

| Config               | ASR     | TSR     | **ERS**   | ERS_strict |
|----------------------|--------:|--------:|----------:|-----------:|
| Flat MAS             | 58.89%  | 100.00% | **41.11%**| 41.11%     |
| ACL-Hardened         | 59.00%  | 100.00% | **41.00%**| 29.35%     |
| AgenticCyOps (P1-P5) | 16.32%  | 100.00% | **83.68%**| 78.20%     |

ERS_strict penalises false-block tool retries as lost benign utility;
AgenticCyOps drops from 83.68% to 78.20% because one group (D) has 3
false blocks out of ~11 tool calls.

Per-TAMAS-category ASR under AgenticCyOps:

| Category              | ASR    |
|-----------------------|-------:|
| Tool Misuse           |  1.55% |
| Data Exfiltration     |  0.00% |
| Direct PI             | 11.67% |
| Indirect PI           |  6.45% |
| Byzantine             |  6.26% |
| Persuasive            | 72.00% |  ← weak spot (AP-11 operational context)

Per-group ERS: A=84.75%, C=85.00%, **D=73.10%**, E=85.44%, F=90.12%.
Group D's Llama-4-Scout validator mix shows higher residuals on AP-8
(46.7%), AP-11 (100%), AP-12 (63.3%), AP-13/14 (20%), pulling the
aggregate down from 86.33% → 83.68%.

## Expected runtime and budget

| Dimension               | Estimate                               |
|-------------------------|----------------------------------------|
| Simulated trials        | 960 (19 cells × 20 trials × 2 modes)   |
| Wall-clock (simulated)  | ~90 seconds (no LLM in the loop)       |
| Real-logs runtime       | 0 (re-uses existing cyberops logs)     |
| Hard-stop budget        | \$40 (enforced via `BudgetTracker`)    |

`BudgetTracker` persists running spend to `results/tamas/budget.jsonl`;
when the cumulative total exceeds the hard-stop it raises
`BudgetExceededError` and the runner aborts cleanly.

## Output artifacts

Simulated run (`results/tamas/`):

- `baseline_results.json`, `defended_results.json` — 480 trials each
  (all 19 attack cells × 20 trials + 5 benign cells × 20 trials).
- `tamas_compare_summary.json/.csv/.md` — per-cell ASR/TSR/ERS and
  McNemar statistics produced by `compare.py`.
- `tamas_findings.pdf` — 9-page paper-ready report from
  `analysis/tamas_analytics.py`.
- `tamas_enhanced.csv` — 8,800 event rows flattened for analysis.
- `tamas_defense_attribution.csv` — per-mechanism block counts.

Real-logs run (`results/tamas/group_<G>/` for a single validator group,
e.g. `group_A/`; `group_<sorted_concat>/` like `group_A_C_E_F/` when
analytics pools across multiple groups):

- `tamas_from_logs.pdf` — 9-page PDF.
- `tamas_from_logs.md`, `tamas_from_logs.json`.
- `tamas_from_logs_aggregate.csv`, `tamas_from_logs_per_config.csv`,
  `tamas_from_logs_per_category.csv`.

Default invocation:
```bash
python -m analysis.tamas_from_logs --groups A
```
writes to `results/tamas/group_A/`.  Multiple groups expand the suffix:
```bash
python -m analysis.tamas_from_logs --groups A,C,E,F   # -> results/tamas/group_A_C_E_F/
```
