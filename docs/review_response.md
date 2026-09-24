# Response to the review: evidence per point

Every number here is computed by a committed script from the committed logs
or from the local-panel replay. No Claude or GPT API is used for any new
result. Status: `done`, `running`, `planned`.

## Questions for the authors

### Q1. The 22 executed tool calls: non-consequential or panel-approved? How many proposals never entered P3? `done`
Source: `analysis/p3_eligibility.py` (uses the oracle's own call folding).

- Of the 37 attacks that executed under FULL (four domains, 900 trials):
  - **21 were tool calls, all approved by the panel.** None executed through
    the non-consequential path that bypasses P3.
  - 13 were poisoned content passed on in a handoff (12 legal AP-2, 1 finance AP-14).
  - 3 were memory writes (CyberOps AP-13).
  The paper's "22 tool calls, non-consequential or panel-approved" is corrected
  to this split.
- P3 eligibility of every tool call under FULL:

  | Path | Attack incidents (8,069 calls) | Benign incidents (1,437 calls) |
  |---|---|---|
  | allowed without entering P3 (not consequential) | 43.4% | 48.2% |
  | denied by P1/P2 | 11.2% | 5.8% |
  | denied by a deterministic P3 layer | 4.2% | 0.0% |
  | panel rejected | 31.0% | 11.5% |
  | panel approved | 10.1% | 34.5% |

  The reviewer is right that classification is deterministic approval: 43%
  of attack-incident tool calls and 48% of benign ones were approved by the
  consequentiality table without a judge. "Every approval was judged" holds
  only for consequential proposals, and the paper will say so.

### Q2. Were the gate thresholds tuned on the evaluated runs? `done`
Yes, in part. The thresholds (scope < 0.2, proportionality > 0.9) were set on
114 score vectors from a probe run of the 20 CyberOps **benign** scenarios
(commit 391fba5), the same scenarios the gate's benign arm then used. No attack
trial was used, and the three transfer domains were never seen. We now report
the gate out of sample (Q3).

### Q3. What share of attack proposals reached the gate and fell into its approve region? `done`
Source: `analysis/gate_offline.py`. The gate is deterministic and its inputs are
reproducible from the log (1,311 of 1,315 logged score vectors reproduced exactly).
Every proposal that reached the panel in the main FULL runs is re-scored and the
gate's decision substituted; the oracle then re-scores the trial (direct outcome).

| Domain | Attack proposals approved by the gate | of which the attack itself | Benign approved | ASR as run -> with gate |
|---|---|---|---|---|
| CyberOps (in sample) | 244 of 926 (26%) | 54 of 65 (83%) | 151 of 404 (37%) | 4.0% -> **8.0%** |
| finance, healthcare, legal (out of sample) | 0 of 2,393 | 0 | 0 of 257 | unchanged |

- The gate is **anti-selective**: it approves the attack proposal itself far more
  often than benign proposals, because a typical attack is one reversible action
  on one target, the low-scope, high-proportionality region it approves.
- Replacing the panel with the gate where it decides **doubles development ASR**
  (nine more attacks: AP-8 3, AP-10 3, AP-15 2, AP-6 1).
- Out of sample it **never fires**: the reversibility table only covers CyberOps
  densely, so proportionality stays below 0.9 elsewhere.
- The live gate arm's 0 of 222 is an outage artifact: its panel could not
  approve, so early legitimate proposals were rejected and the phases halted
  before the attack step (85 not-attempted trials with an open round).
- **The paper's claim that the gate "cleared a third of proposals without letting
  an attack through" is withdrawn.**

### B1. The scorer fixed, evaluated offline `done`
Alignment gets the incident evidence (as P2 uses it) and Qwen3-Embedding-0.6B;
precedent gets a ledger of the approvals made earlier in the same trial.

- The shipped default gate **still never decides**, in any domain.
- Why: precedent reaches 0.7 in 8 of 2,233 gate-bound proposals (isolated trials
  start with an empty ledger), and alignment is **higher for attack proposals
  than for benign ones** (mean 0.57 vs 0.39; above 0.7 for 31 of 180 attack
  proposals and 0 of 471 benign), because the attack proposal names the target
  the attacker planted in the incident text. A score computed from
  attacker-influenced evidence rewards the attacker (see Major 4).
- The permissive gate with the fixed scorer behaves exactly as with the shipped
  one (it does not read alignment or precedent): 4.0% -> 8.0%.
