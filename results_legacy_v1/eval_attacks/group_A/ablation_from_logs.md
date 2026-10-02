# Post-hoc principle-disable ablation

Upper-bound counterfactual derived from existing `results.csv` (no re-run).  Each row assumes a Pn-catch becomes a success when Pn is disabled -- a worst-case bound; the true ablation requires a re-run with `attacks.harness --disable-principles Pn`.

### Group A / cyberops

- Trials evaluated: **375**
- Current AgenticCyOps ASR: **1.87%** (7/375)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 15 | 5.87% | +4.00pp |
| -P2 | 116 | 32.80% | +30.93pp |
| -P3 | 170 | 47.20% | +45.33pp |
| -P4 | 25 | 8.53% | +6.66pp |
| -P5 | 10 | 4.53% | +2.66pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 32 trials (8.53%)
- `none`: 7 trials (1.87%)

