# Ablation Studies

Single-slot ablations on **Group A × cyberops × all 15 APs × 6 trials** —
one row per ablation in the paper's table. All commands assume vLLM
servers are up (`./start_servers.sh`) and `.env` has the API keys for
Group A's validator panel (Claude + GPT-4o).

Outputs land at `results/eval_attacks/group_A<tag>/cyberops/results.csv`
and JSONL audit logs at `logs/cyberops_eval_attacks_A<tag>/`, where
`<tag>` is `_disabled_<set>` for principle-disable runs (e.g.
`_disabled_P3`) or empty for the production run / consensus-sweep runs.

The same CSV schema as the production run, so you can union-load with
[analysis/attack_analytics.py](../analysis/attack_analytics.py) and pivot
on the `Config` column.

---

## A. Single-principle isolation (each principle alone)

Each row = AgenticCyOps with **only one principle enabled**. Disable the
other four via `DISABLE_PRINCIPLES`. Answers: *is any single principle
sufficient on its own?*

```bash
# P1 only  -- identity verification + response integrity
DISABLE_PRINCIPLES=P2,P3,P4,P5 \
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6

# P2 only  -- manifest enforcement + parameter validation + output classifier
DISABLE_PRINCIPLES=P1,P3,P4,P5 \
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6

# P3 only  -- verified-execution stack (consensus, op-context, etc.)
DISABLE_PRINCIPLES=P1,P2,P4,P5 \
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6

# P4 only  -- memory integrity (similarity, drift, schema, replay, contradiction)
DISABLE_PRINCIPLES=P1,P2,P3,P5 \
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6

# P5 only  -- access isolation (memory ACL)
DISABLE_PRINCIPLES=P1,P2,P3,P4 \
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
```

## B. Leave-one-out per principle (full stack minus one)

Each row = AgenticCyOps with **one principle disabled**. Answers: *what
does each principle uniquely catch that nothing else covers?*

```bash
DISABLE_PRINCIPLES=P1 ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
DISABLE_PRINCIPLES=P2 ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
DISABLE_PRINCIPLES=P3 ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
DISABLE_PRINCIPLES=P4 ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
DISABLE_PRINCIPLES=P5 ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6
```

## C. Consensus quorum threshold sweep

Holds the validator panel constant (V1_qwen, V2_deepseek, V6_gpt4o,
V4_claude) and varies the approval threshold. **Reuses the production
agenticcyops config** — only `--consensus-config` changes per run.
Profiles already added to [configs/validators.yaml](../configs/validators.yaml).

To override the per-group default, edit `scripts/run_attack_paths.sh` to
pass `--consensus-config <profile>`, OR call the harness directly:

```bash
for n in 1 2 3 4; do
    ./scripts/run_attack_paths.sh A cyberops all agenticcyops 6 \
        # Edit GP_CONSENSUS[A] to threshold_sweep_${n}of4 first, OR:
    : # see harness-direct command below
done
```

Direct harness invocation (cleanest for a one-shot threshold sweep):

```bash
for n in 1 2 3 4; do
    /home/student/.conda/envs/agenticcyops/bin/python3 -m attacks.harness \
        --domain cyberops --eval A --config agenticcyops \
        --group A --model-url http://localhost:8000/v1 \
        --consensus-config "threshold_sweep_${n}of4" \
        --trials 6
done
```

## D. Consensus panel-size sweep

Same idea, varying the number of validators (1, 2, 3 — the 4-validator
case = `default_consensus` already in the production run).

```bash
for profile in panel_1_qwen panel_2_qwen_claude panel_3_qwen_claude_gpt4o; do
    /home/student/.conda/envs/agenticcyops/bin/python3 -m attacks.harness \
        --domain cyberops --eval A --config agenticcyops \
        --group A --model-url http://localhost:8000/v1 \
        --consensus-config "$profile" \
        --trials 6
done
```

---

## Output layout

| Run | log dir | result dir |
|---|---|---|
| Production agenticcyops | `logs/cyberops_eval_attacks_A/` | `results/eval_attacks/group_A/cyberops/` |
| Disable-P3 ablation | `logs/cyberops_eval_attacks_A_disabled_P3/` | `results/eval_attacks/group_A_disabled_P3/cyberops/` |
| Single-P1 isolation | `logs/cyberops_eval_attacks_A_disabled_P2P3P4P5/` | `results/eval_attacks/group_A_disabled_P2P3P4P5/cyberops/` |
| Threshold sweep | (same as production — overwrites if you don't tag) | (same) |
| Panel-size sweep | (same — tag manually if comparing) | (same) |

For consensus sweeps the eval_name doesn't change automatically — if you
want each threshold/panel combo in its own log dir, pass an explicit
`--eval-name` or rename the output dirs after each run.

## Cost expectations (per ablation slot)

- Single principle / leave-one-out: ~30-60 min wall-clock per slot.
  P3 ablations are the expensive ones (consensus calls); P1/P2 are
  cheap (deterministic checks only).
- Threshold sweep: 4 runs × ~1h each = ~4h total. Each call is
  identical to a production agenticcyops trial; only the threshold
  changes the approval logic.
- Panel-size sweep: 3 runs (1, 2, 3 validators) × ~30-50 min. Smaller
  panels = fewer LLM calls per consensus invocation.

## Mechanism strings to expect

The disable-principles flag does **not** rename existing P-layer
mechanism strings — it just causes the layer's check to be skipped. So
`P1_authenticated_interface`, `P2_capability_scoping`,
`P3_verified_execution`, `P4_*`, `P5_access_control` all still appear
when the corresponding principle is *active*; ablation runs simply have
fewer of them.

New mechanism strings introduced by this work:

- `llm_judge_approved` — the standalone `llm_judge` config when judges
  approve (see [llm_judge config](../host/orchestrator.py)).
- `P3_consensus_reject` / `P3_consensus_approve` /
  `P3_consensus_unavailable` / `P3_consensus_error` — same usage as
  llm_judge above.
- `P4_disabled_accept` — emitted by MMA when `skip_p4=True` and the
  write would have otherwise been integrity-checked. Lets analytics
  separate ablation accepts from genuine P4 approvals.

## What the paper table looks like

| Config | Disabled | ASR | Notes |
|---|---|---:|---|
| Flat MAS | — | (existing) | baseline ceiling |
| ACL-Hardened | — | (existing) | network-layer baseline |
| LLM Judge (P1+consensus) | — | (existing) | reviewer-asked baseline |
| AgenticCyOps | — | (existing) | full stack |
| AgenticCyOps -P1 | P1 | TBD | leave-one-out |
| AgenticCyOps -P2 | P2 | TBD | |
| AgenticCyOps -P3 | P3 | TBD | |
| AgenticCyOps -P4 | P4 | TBD | |
| AgenticCyOps -P5 | P5 | TBD | |
| AgenticCyOps P1-only | P2,P3,P4,P5 | TBD | single-principle |
| ... (5 rows) | | | |
| Quorum 1/4 | — | TBD | threshold sweep |
| Quorum 2/4 | — | TBD | |
| Quorum 3/4 | — | TBD | (= production) |
| Quorum 4/4 | — | TBD | unanimous |
| Panel size 1 | — | TBD | size sweep |
| Panel size 2 | — | TBD | |
| Panel size 3 | — | TBD | |
| Panel size 4 | — | (= production) | |
