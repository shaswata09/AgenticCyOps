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

### Q4. What is "evidence" for P2.2 on ASB, and how often is the target in the task by construction? `done`
Source: `benchmarks/injecagent/harness/trial_driver.py` (`DefensePipeline`), shared by the ASB adapter.

- The ASB adapter does **not** judge the agent's emitted action. It synthesizes a
  proposal from the case: the target is the first 200 characters of the
  **attacker instruction**, and the description and justification are the
  attacker instruction verbatim. P2.2's evidence, and the incident description
  the judges read, is the **user task**.
- By construction, the attacker's target is a substring of the user task in
  **all 90 DPI cases** (the injection sits in the task), so P2.2 cannot fire on
  DPI, and in **none of the 165 IPI, MP and PoT cases**, so there the substring
  branch always fails and the cosine threshold alone decides.
- In the frozen run: DPI 54 emitted, all stopped by the panel; IPI 22 of 49 and
  MP 26 of 53 stopped by P2.2. **P2.2's ASB share measures how topically
  different two ASB texts are, not a property of the agent's action**, and the
  panel reads the attacker's instruction as the proposal's justification. Both
  favor the defense. The paper will state this and stop presenting P2.2's ASB
  share as rule strength.

## Replay with an all-local panel (Majors 2 and 3, minor points on lineage, GPT-4o, egress)

Source: `analysis/replay.py`, `analysis/replay_run.py`, `analysis/replay_panels.py`;
votes cached in `cache/validators/`, prompts in `cache/replay/`.

**Method.** A validator sees a fixed system prompt and one JSON message built
from the proposal (as P3 builds it) and the incident. Both are recoverable from
the logs, so every logged panel round is re-adjudicated offline by local
validators, with no primary model and no API.

**Fidelity.**
- Reconstructed messages match the prompt token count each validator logged in
  **99.6–99.7%** of rounds; the rest differ only by a random incident UUID the
  host drew when a trigger nested its fields (not recoverable, no content).
- **Replay reproduces the original decisions:** Mistral-Small (a Div4 member,
  local, unaffected by the outage) re-asked on the rebuilt prompts gives its
  logged vote in **98.6% of 18,159 rounds** (99.0–99.6% on the main arms).
- Found along the way: for AP-4, AP-5, AP-6, AP-12 and part of AP-10 the
  panel never saw the incident description (the trigger nests its fields, so
  the host's `incident.description` was empty).

**Main panel: Local4** = Mistral-Small-3.2-24B (Mistral), Gemma-4-31B-it
(Google), gpt-oss-120b (OpenAI, open weights), Llama-4-Scout (Meta); quorum 3 of
4, a model never judging its own proposals. Chosen by lineage before any result
was seen. No Qwen-family member (the primary is Qwen), no API, no outage.

| Arm (direct outcome under Local4) | ASR [95% CI] | as run (Div4) |
|---|---|---|
| FULL, development | **9.8% [4.0, 16.9]** | 4.0% |
| FULL, transfer (pooled) | **5.3% [2.8, 8.3]** | 4.1% |
| JUDGEONLY, development | **33.8% [24.0, 44.0]** | 24.4% |
| FULL + judge everything after rules | 9.8% (benign denial 9.5% -> 11.6%) | n/a |
| FULL minus P1 / P2 / P4 / P5 (dev) | 11.3 / 16.2 / 14.7 / 12.4% | 5.4 / 9.8 / 8.9 / 6.2% |
| Scout / Mistral / Llama-8B primaries, dev | 7.1 / 9.3 / 7.6% | 1.8 / 2.7 / 4.0% |
| ASB frozen live run (FLAT 28.8%) | **1.8%** (9 of 101 panel rounds approved) | 0.0% (panel degraded) |
| ASB 405-action replay | 1.4% (18 let through, 4.4%) | n/a |

- **Rules first survives and sharpens.** Under the same judges, JUDGEONLY leaves
  33.8% (FLAT 36.4%): these judges alone barely help. FULL cuts it to 9.8%.
- **Judge-everything-after-rules (Major 3).** Judging every rule-surviving call,
  consequential or not, changes **no** attack outcome (no attack executed through
  a non-consequential call) and adds benign denials. The gap between FULL and
  JUDGEONLY is therefore what the rules add, not what judging less costs.
  Holds in all four domains (executed attacks: CyberOps 22, finance 10, legal
  26, healthcare 0, identical with and without); judged fraction 33.4% -> 78.1%
  (dev), benign denial 9.5% -> 11.6%, incidents with a denial 75% -> 80%.
  Without the memory paths (AP-4, AP-13) JUDGEONLY vs FULL is 23.3% vs 10.1%.
- **Ablation benign cost, recomputed from the logs (minor point).** Legitimate
  proposals denied / benign incidents with a denial, Local4: FULL 9.5 / 75.0,
  -P1 7.1 / 58.3, -P2 2.9 / 33.3, -P3 7.9 / 58.3 (as run, no panel),
  -P4 9.3 / 78.3, -P5 7.2 / 68.3. P2 is both a main defense and the main cost.
- **Panel strictness sets the absolute level.** Per-validator approval of attack
  vs benign proposals: Gemma 31/76%, gpt-oss 43/80%, Mistral 51/91%, Scout 81/94%,
  original Div4 (where all four voted) 26/81%. Scout barely discriminates. We keep
  Local4 as specified and report sensitivity to composition rather than choose
  members after seeing attack outcomes.

**Rule evasion with a working panel (E2).** Of the 24 siblings, **22 were held
by the judges and 2 executed** (CyberOps AP-10, finance AP-5; 6 of 72 trials).
Evading a rule hands the decision to the judges, who then fail on 2 of 24.

## Major 5 and Q6: persistent state and expiry `done`
Source: `analysis/ledger_expiry.py` (drives the shipped `CrossIncidentLedger` and
`VersionedLedger`; reproduces the logged P3.4 denials exactly and P3.6 within 2).

- **Correction to the paper.** The harness runs each attack path in its own
  process and both ledgers are in memory, so the attack incidents' state never
  reached the benign tail. In both passes the **first benign incident has no
  stateful denial**; from the second on, almost every consequential proposal is
  denied. The collapse is **legitimate work denying itself**, not a denial of
  service by the attacks (the CyberOps carry-over figure agrees: 2.0 denials at
  the first benign position against an isolated mean of 1.9, then 4 to 16).
  The paper's "saturated at the first benign incident,
  so the degradation happens during the attack incidents" is withdrawn.
- Cause: replay detection keys on the proposal's **skeleton** (tool, argument
  names, action) and never expires, so one incident's `block_ip` makes every later
  incident's `block_ip` a "replay"; the 24-hour ledger window never expires within
  a 50-incident run.

| Policy (20 benign incidents, 136 consequential proposals) | Denied by stateful checks |
|---|---|
| as shipped (skeleton replay, never expires) | 95.6% |
| skeleton replay, expire after 5 / 2 / 1 incidents | 83.1 / 66.2 / 60.3% |
| identity replay (tool, action, target), never expires | 80.1% |
| **identity replay, expire after 1 incident** | **42.6%** |

- No expiry setting alone restores usability; identity keying plus a
  one-incident window halves the denials and keeps every stateful interception in
  the isolated attack runs (48 of 48 CyberOps trials). Values are upper bounds
  (some remaining denials are retries that only exist because of earlier denials).

## Major 4: rules that trust attacker-controlled evidence `done`
Source: `analysis/trusted_evidence.py` (re-runs the shipped `ParameterValidator`
target-in-evidence check on every logged tool call under FULL, four domains).

- With the full incident as evidence the offline check reproduces the logged
  P2.2 decisions on 99.6-100% of calls.
- Restricting the evidence to structured fields (identifiers, addresses,
  indicators, assets, timestamps, severities; free text and harness-supplied
  proposals removed):

  | | calls | P2.2 denials, full incident | trusted fields only |
  |---|---|---|---|
  | attack proposals | 495 | 108 | 136 |
  | other calls in attack incidents | 7,001 | 220 | 259 |
  | benign calls | 1,376 | 23 | 23 |

- On this suite, trusting only structured evidence **strengthens P2.2 at no
  benign cost**: naming the target in the alert text no longer satisfies it.
  (Per-call overlap between the two sets not yet computed.)

## Adaptive attacker (two-stage) `not done`
Not implemented in this pass. The paper keeps "no adaptive attacker beyond
the rule-evading siblings" as a stated limitation.

## Lineage (minor point: Div4 contains the primary's lineage) `done`
Same replay, size-matched panels (2 of 3), no API:

| Panel | FULL dev | FULL transfer | ASB replay let-through (of 250 panel rounds) | frozen ASB ASR |
|---|---|---|---|---|
| Div3L: Mistral, Gemma, gpt-oss | 9.8% | 5.8% | 18 | 1.8% |
| Lin3: Qwen3-32B, R1-Distill-Qwen-32B, Qwen3-14B | 10.7% | 8.3% | 127 | 9.6% |
| Single: Qwen3-32B (1 of 1) | 10.7% | 8.0% | 36 | 3.3% |
| Local4 (3 of 4, main) | 9.8% | 5.3% | 18 | 1.8% |

At equal size and quorum the same-lineage panel lets 7x more ASB actions through
than the diverse one and 3.5x more than its own single member (original logged
run: Lin3 108, Single 41). The main panel now contains no Qwen-family model.
