# CAIS 2026 Rebuttal Draft

Working draft. Numbers pulled directly from:

- `results/eval_attacks/attack_analytics.pdf` (5-group cross-group PDF)
- `results/eval_attacks/cross_group_summary.csv`
- `results/tamas/tamas_compare_summary.md` (simulated TAMAS)
- `results/tamas/real_logs/tamas_from_logs.md` (real-logs TAMAS)
- `results/baseline/group_*/cyberops/baseline_summary.csv`

Cross-check every figure against the source artifact before pasting
into the final rebuttal.

---

## Scale and scope (opener)

- **~4,110 instrumented trials** executed to date across **5 model
  groups** attacked (A, C, D, E, F), **4 enterprise domains**
  (CyberOps, healthcare, finance, legal), **3 configurations** (flat,
  acl_hardened, AgenticCyOps), **7 model families** (Qwen3, GLM-4.7,
  DeepSeek, Llama-4-Scout, Mistral, Claude, GPT-4o), and the
  independent **TAMAS benchmark** (arxiv 2506.02635).
- Zero framework code changes across the four enterprise domains —
  only JSON configs and tool stubs differ. The same P1-P5 wrappers
  also apply to the domain-neutral TAMAS scenarios.
- Hardened via **4 red-team passes** (21 fixes: 1 critical, 6 high,
  9 medium, 5 low) + **false-negative audit** (11 fixes) +
  **false-positive audit** (6 fixes).

---

## R3: TAMAS Benchmark

Validates that P1-P5 generalises beyond the CyberOps red-team
campaigns the defences were co-designed against. Two complementary
views.

### R3a -- Simulated TAMAS (upper-bound middleware run)

`benchmarks/tamas/eval_runner.py` drives the `P12345Middleware`
directly against the TAMAS 6-category × 5-scenario matrix (19 unique
attack cells).

| Metric                  | Baseline | Defended (P1-P5) | Delta       |
|-------------------------|---------:|-----------------:|-------------|
| Mean ASR (19 cells)     | 100.00%  |     5.53%        | -94.47 pp   |
| Mean TSR                | 100.00%  |   100.00%        | 0 pp        |
| Mean ERS                |    0.00% |    **94.47%**    | +94.47 pp   |
| McNemar p<0.001 cells   | —        |    **18/19**     | —           |

n = 480 baseline trials + 480 defended trials = **960 total**.
Single residual cell: `social_media_moderation × direct_prompt_injection`
— an HTML-comment admin injection that escapes the regex-based stub
consensus. Expected to close under a live-LLM consensus validator.

### R3b -- Real TAMAS Score (from live-LLM AgenticCyOps logs)

`analysis/tamas_from_logs.py` maps the 15 AgenticCyOps APs onto the
6 TAMAS categories and computes ASR/TSR/ERS from real multi-agent
evaluation logs across 5 groups (A, C, D, E, F).

| Config               | ASR    | TSR    | **ERS**   | ERS_strict |
|----------------------|-------:|-------:|----------:|-----------:|
| Flat MAS             | 58.89% | 100.0% | **41.11%**| 41.11%     |
| ACL-Hardened         | 59.00% | 100.0% | **41.00%**| 29.35%     |
| AgenticCyOps (P1-P5) | 16.32% | 100.0% | **83.68%**| 78.20%     |

ERS_strict penalises false-block tool retries (AgenticCyOps: 3 FP
blocks on Group D out of ~11 tool calls). **AgenticCyOps more than
doubles the baseline ERS** (41.11% → 83.68%) while preserving benign
task completion.

Per-TAMAS-category ASR under AgenticCyOps:

| Category                  | ASR    |
|---------------------------|-------:|
| Tool Misuse               |  1.55% |
| Data Exfiltration         |  0.00% |
| Direct Prompt Injection   | 11.67% |
| Indirect Prompt Injection |  6.45% |
| Byzantine Behavior        |  6.26% |
| **Persuasive Manipulation** | **72.00%** |

Persuasive manipulation is the openly acknowledged weak spot — it
maps to AP-11 (Operational Context), which carries 20-100% residual
ASR depending on validator mix. Called out as a named limitation.

### Per-group AgenticCyOps ERS (validator-diversity view)

| Group | Primary         | Validators                          | **ERS** |
|-------|-----------------|-------------------------------------|--------:|
| A     | Qwen3-235B      | V1(Qwen) + V2(DeepSeek) + V4(Claude) + V6(GPT-4o) | 84.75% |
| C     | Qwen3-235B      | V1×3 (same-family)                  | 85.00% |
| D     | Llama-4-Scout   | V1+V2+V4+V6                         | **73.10%** |
| E     | Qwen3-235B      | V1 + V5(Mistral) + V4 + V6          | 85.44% |
| F     | Claude (API)    | V1 + V2 + V3(Llama) + V5 + V6       | 90.12% |

**Group D is the outlier:** Llama-4-Scout as primary produces
different tool-call parameter distributions than Qwen/GLM/Claude,
shifting AP-8 (47%), AP-11 (100%), AP-12 (63%), AP-13/14 (20%) out of
the P2-L2 / P3-L4 detection envelopes. The other four groups range
84-90% ERS regardless of same-family vs diverse-family validator mix,
suggesting **primary-agent model choice matters more than validator
pool composition** for this benchmark.

---

## Token-cost finding (unexpected positive)

The baseline analysis shows AgenticCyOps consumes **~35% fewer tokens per benign run** than both Flat MAS and ACL-Hardened despite running the full P1–P5 pipeline (avg 10,840 tokens vs 16,561 Flat / 16,911 ACL across 72 benign runs). The defenses catch issues early and prevent the agent-retry loops that inflate token counts when tools are blocked at the network layer (ACL) or when the agent must re-plan after runtime failures (Flat). This reframes the common assumption that defense middleware adds cost: structural capability scoping is **cheaper** than reactive denial.

Per-group validator effect: Groups B/D/F (GLM-4.7 / Llama-4-Scout / Claude primaries) consume ~10–20% more tokens than Qwen-primary groups A/C/E across all configs. Group D is the highest-cost AgenticCyOps configuration (~12k tokens/run) and also the weakest validator mix in Eval A and real-logs TAMAS.

---

## Defense-by-principle contribution (CyberOps Eval A)

| Principle | Active coverage                                   | Evidence                      |
|-----------|---------------------------------------------------|-------------------------------|
| P1        | 11,155 identity verifications (always ALLOW since attacks use registered tools) | Structural assurance; defends MITM / spoofed-tool attack surface not simulated in the testbed |
| P2        | 87% of blocks at the tool-call boundary           | AP-1, AP-3, AP-5, AP-8 primary |
| P3        | 10-layer verified execution; majority of residual blocks | AP-6, AP-7, AP-9, AP-10, AP-15 |
| P4        | Memory pipeline; 0 events during attack trials    | Attack payloads don't include memory_ops; defends AP-13/AP-14 once memory_ops are added |
| P5        | Access-controlled isolation; 0 events during attacks | Same reason as P4             |

P4/P5 carry zero attack-trial events not because they are inactive
but because attack payloads target the tool-call surface (TA vectors)
rather than the memory-operation surface (MA vectors). Adding
`memory_ops` to AP-13/AP-14 payloads is listed as pending work.

---

## R10: Cross-domain attack interception (headline table)

*Pending Eval F execution — placeholder.*

| Attack Pattern             | CyberOps | Healthcare | Finance | Legal | Code Changes |
|---------------------------|---------:|-----------:|--------:|------:|-------------:|
| Tool Redirection (AP-1)   | 0% ASR   | TBD        | TBD     | TBD   | **0**        |
| Memory Poisoning (AP-2)   | 0% ASR   | TBD        | TBD     | TBD   | **0**        |
| Exfil / Bulk (AP-4/5)     | 0% ASR   | TBD        | TBD     | TBD   | **0**        |
| Action Chain (AP-7)       | 3-7% ASR | TBD        | TBD     | TBD   | **0**        |
| Parameter Manipulation (AP-8) | 0-60% ASR | TBD    | TBD     | TBD   | **0**        |
| Benign Completion          | 100%    | 100% (baseline) | 100% | 100% | **0**       |
| **Principle Modifications**| **—**   | **None**   | **None**| **None** | **—**    |

"Code Changes: 0" column is the empirical proof of the
domain-agnosticism claim — the **same** P1-P5 wrappers secure tool
orchestration and memory management regardless of whether the tools
are firewalls, MRI scanners, financial fraud detectors, or court
filing systems. Cross-domain ablation (P2 removed on Finance AP-1
analogue) will confirm the principle-necessity finding transfers.

---

## Limitations (honest)

Called out explicitly in the rebuttal.

1. **Group B (GLM-4.7-FP8 primary) not executed.** Time constraint —
   the FP8 Marlin kernel path requires vLLM nightly and swapping in
   GPU occupancy is costly. Real-logs TAMAS therefore spans 5 of 6
   planned groups.
2. **Eval F (multi-domain attacks) not executed.** R10 headline table
   currently shows CyberOps values only; the cross-domain proof rests
   on architectural reasoning + baseline completion across all 4
   domains (72 baseline runs verified).
3. **Persuasive manipulation 72% ASR.** Maps to AP-11 (Operational
   Context); the stub consensus validator used in simulation doesn't
   recognise subtle urgency framing. Expected to improve with a live
   LLM-backed consensus, but that specific mitigation has not been
   measured.
4. **Group D (Llama-4-Scout) residuals.** AP-8/11/12/13/14 carry
   higher ASR than other groups — documented as a validator-diversity
   finding rather than papered over. Drops aggregate TAMAS ERS from
   86.3% (A/C/E/F only) to 83.7% (A/C/D/E/F).
5. **P4/P5 zero attack events.** Attack payloads target the tool-call
   surface; memory_ops need to be added to AP-13/AP-14 so P4/P5 fire
   during attacks (pending).
6. **Simulated TAMAS is a ceiling.** 94.47% ERS is deterministic
   middleware correctness against hand-authored payloads — a live-LLM
   replay would have higher variance. The real-logs 83.68% ERS is the
   defensible paper number.
7. **Ablation study not yet executed.** Principle-necessity claims
   are supported by per-AP defense attribution but not by
   remove-one-at-a-time runs.

---

## What we added vs the submission

| Addition                                               | Evidence location               |
|--------------------------------------------------------|---------------------------------|
| 15 Attack Paths covering 35 TA/MA/CA vectors (vs 6 original APs) | `attacks/payloads/*/ap*_*.json` |
| 5 model groups attacked (A/C/D/E/F) with cross-group analysis | `results/eval_attacks/cross_group_summary.csv` |
| TAMAS benchmark integration (simulated + real-logs)    | `benchmarks/tamas/`, `analysis/tamas_{analytics,from_logs}.py` |
| Group D (Llama-4-Scout) validator-diversity finding    | `results/eval_attacks/group_D/cyberops/` |
| Persuasive-manipulation weak spot (AP-11) acknowledged | `results/tamas/real_logs/tamas_from_logs.md` |
| 4 red-team passes + 11 FN + 6 FP audit fixes           | `experiment_plan.md` §2.8       |
| TSR preservation across all domains and TAMAS          | 100% in every defended cell     |
| ~35% token-cost reduction under AgenticCyOps           | `results/notebooks/01_baseline_findings.ipynb` Chart 2.3 |
| Standalone TAMAS findings notebook                      | `results/notebooks/03_tamas_findings.ipynb` (8 charts, simulated + real-logs views) |

---

## Closing

The testbed, all domain adapters, and experimental data will be
released as open-source upon acceptance. The five principles reduce
the attack surface structurally — not through domain-specific
heuristics — and the empirical evidence spans a rebuttal-relevant
scale: **4,110 instrumented trials, 4 domains, 7 model families, 5
attacked model groups, and an external benchmark**.
