# DEFER: Deterministic-First Enforcement with Residual judgment

Artifact for the paper **"Where Rules End and Judges Begin: Measuring the Judgment
Boundary in Multi-Agent System Defenses"** (under double-blind review).

LLM multi-agent systems (MAS) invoke tools, share memory, and delegate, and each of
those interactions can carry attacker-controlled content. Pipelines that combine
defenses usually leave the final decision to an LLM judge. This artifact measures how
much of that decision deterministic checks can settle, and what is left for the judges.
It contains:

- **DEFER**, a reference pipeline of 27 deterministic checks followed by an LLM panel,
  organized into five principles over the two surfaces where untrusted content enters
  a MAS (tool orchestration and memory);
- **a four-domain testbed** (CyberOps, healthcare, finance, legal) with five injection
  channels, 15 attack paths (300 variants), and 35 benign scenarios;
- **an outcome oracle** that separates model refusal from framework interception, and
  **offline re-adjudication** of every logged judge decision, which re-scores the logged
  proposals under any validator panel without re-running the agents;
- **every per-trial log, cached judge vote, table, and figure** behind the paper, and
  one command per artifact to regenerate it.

![Overview](docs/figures/overview.png)

*Attacker content enters through five channels on two surfaces (left). DEFER settles
what it can with deterministic checks and sends only undecided proposals to a panel of
LLM judges (center). Right: attack success on Agent Security Bench with the frozen
pipeline, and headline numbers from our suite.*

---

## Contents

- [Results at a glance](#results-at-a-glance)
- [Reproducing the results](#reproducing-the-results)
- [Names used in the paper and in the logs](#names-used-in-the-paper-and-in-the-logs)
- [The pipeline](#the-pipeline)
- [Repository layout](#repository-layout)
- [Provenance and known limitations](#provenance-and-known-limitations)
- [Ethics and intended use](#ethics-and-intended-use)
- [License](#license)

---

## Results at a glance

Unless a caption says otherwise, results use the Qwen3-235B-A22B primary, three
trials per variant, isolated state, and the **direct outcome under Local4**: every
logged panel round re-judged by four open-weight judges from four model families
(Mistral-Small-3.2-24B, Gemma-4-31B-it, gpt-oss-120b, Llama-4-Scout; three of four).
Intervals are 95% cluster-bootstrap intervals over variants. The numbers come from
[`results/replay_tables.md`](results/replay_tables.md); the figures come from
`make figures`.

### The judgment boundary (development domain, 75 variants × 3 trials)

| Configuration | Attack success % [95% CI] | Tool proposals judged % | Legitimate proposals denied % |
|---|---|---|---|
| FLAT (no checks) | 36.4 [26.2, 46.7] | 0 | 0.0 |
| ACL (connectivity only) | 24.0 [15.1, 33.3] | 0 | 54.8 |
| JUDGEONLY (judge every proposal) | 33.8 [24.0, 44.0] | 100 | 3.8 |
| NOJUDGE (never judge; escalate instead) | 1.3 [0.0, 4.0] | 0 | 51.7 |
| **FULL (DEFER: rules first, judge last)** | **8.4 [3.1, 15.1]** | **33.4** | **9.5** |
| JUDGEREST (FULL, judge everything the rules let through) | 8.4 [3.1, 15.1] | 78.1 | 11.6 |

![Judgment boundary](docs/figures/judgment_boundary.png)

*(a) Attack success; (b) legitimate tool proposals denied or escalated, with benign
task completion as run (hollow diamonds, not shown for JUDGEONLY, whose benign runs
overlapped the validator outage). The same judges without the rules barely beat no
checks. Judging everything the rules let through changes no attack outcome.*

### Who stops the attack

![First interception by decision tier](docs/figures/interception_tiers.png)

*The check that first intercepted each blocked attack, by decision tier. Rules decide
84% of interceptions in the development domain and 79% in the three transfer domains.
On Agent Security Bench, whose injected actions use in-scope tools with plausible
arguments, they decide at most 40%, and only through rules that read the case's text.*

![Attack success per attack path](docs/figures/ap_heatmap.png)

*Attack success per attack path and configuration (development domain). The upper
block is delivered as content (attacker class T1); the lower block through a
compromised agent's handoff or rationale (T2).*

<table>
<tr>
<td width="50%"><img src="docs/figures/paired_variants.png" alt="Paired outcome per variant"></td>
<td width="50%"><img src="docs/figures/ablation.png" alt="Leave-one-out ablation"></td>
</tr>
<tr>
<td><em>Per variant, FULL rescues 23 variants that JUDGEONLY loses and gives up two;
11 of the 23 are on memory paths JUDGEONLY cannot see.</em></td>
<td><em>Leave-one-out on the 68 variants shared by every arm: removing P3, P2, or P4
lets attacks through that the others do not catch.</em></td>
</tr>
</table>

### The judges

<table>
<tr>
<td width="50%"><img src="docs/figures/validator_behavior.png" alt="Judge agreement and quorum"></td>
<td width="50%"><img src="docs/figures/panel_composition.png" alt="Panel composition and lineage"></td>
</tr>
<tr>
<td><em>(a) Pairwise Cohen's κ between the four Local4 judges (diagonal: reject rate);
mean κ 0.50. (b) Share of proposals approved as a function of the quorum.</em></td>
<td><em>Panels re-adjudicated on the same 405 replayed ASB actions and 661 legitimate
proposals. A same-size panel of one model lineage (Lin3) lets through seven times as
many actions as a mixed one (Div3L).</em></td>
</tr>
</table>

### Transfer, channels, and cost

![Transfer across domains and primaries](docs/figures/transfer.png)

*Security transfers across four domains and four primary models (development-domain
attack success under FULL: 8.4% Qwen3-235B, 5.8% Llama-4-Scout, 8.0% Mistral-Small,
6.2% Llama-3.1-8B; transfer domains 5.3% [2.8, 8.3] against 29.2% for FLAT). Cost does
not: every benign incident outside the development domain loses at least one action.*

<table>
<tr>
<td width="50%"><img src="docs/figures/channels.png" alt="Attack success by channel"></td>
<td width="50%"><img src="docs/figures/state_carryover.png" alt="State carry-over"></td>
</tr>
<tr>
<td><em>Attack success by injection channel (hollow markers: exposure). FULL reduces
four of five channels; the tool-response residual is a plausible fabricated legal
precedent that passes rules and judges alike.</em></td>
<td><em>Persistent state (as run with Div4): legitimate incidents deny each other through
replay and ledger state that never expires. An identity-keyed, one-incident expiry
halves the denials (paper, Table III).</em></td>
</tr>
</table>

![Cost](docs/figures/cost.png)

*Where the cost goes, as run with the original Div4 panel: (a) denials per 100
legitimate proposals by principle and domain, (b) median benign-incident latency,
(c) tokens per incident. JUDGEONLY's benign runs overlapped the validator outage and are
shown for completeness only. With two local judges, median latency is 60 s
(calibration run).*

### Third-party benchmark and calibration

- **Agent Security Bench** (255 cases, frozen pipeline, 2 trials per case): attack
  success 28.8% under FLAT, 30.0% under ACL, **1.8%** under FULL. Access control blocks
  nothing, because the injected action uses a tool the agent holds.
- **Calibration of the re-adjudication:** a live run at `defense-freeze-v2.9` with two
  local judges gives 2.7% [0.0, 6.2] attack success on the 75 development variants,
  against 3.6% [0.0, 8.0] when the original runs are re-judged by the same two judges.
  Legitimate proposals denied: 12.9% live, 12.5% replayed (`results/b2_live.json`).

---

## Reproducing the results

Three levels, from cheapest to most expensive. Levels 1 and 2 call no API and no
primary model.

| Level | Needs | Time | Reproduces |
|---|---|---|---|
| 1. Analysis | CPU, Python 3.13 | minutes | every table, number, and figure, from the committed logs and cached votes |
| 2. Re-adjudication | one GPU per local judge | hours | the cached judge votes in `cache/validators/` |
| 3. Full runs | GPUs for the primary and judges | days | the per-trial logs in `logs/` |

### Setup

```bash
conda create -n defer python=3.13 -y && conda activate defer
pip install -r requirements.txt
make test                      # unit tests, including payload hygiene and the tier mapping
```

`.env` is needed only for level 3 runs that use API validators (the original Div4
panel). The reported panel (Local4) and the calibration panel (local2) are fully local.

### Level 1: analysis (no model calls)

```bash
make paper-tables     # parse logs -> results/eval_attacks/all_trials.csv, statistics, as-run tables
make replay-tables    # every Local4 number -> results/replay_tables.md, all_trials_local4.csv
make figures          # every paper figure -> paper/figs/*.pdf, README figures -> docs/figures/
make b2               # live calibration run vs its replay -> results/b2_live.json
make freeze-check     # the decision code equals defense-freeze-v2.9
```

`make figures` plots the Local4 panel by default; `make figures DEFER_PANEL=` plots the
as-run Div4 values. The offline analyses behind the revision are single modules:

| Module | Question it answers |
|---|---|
| `analysis/replay_panels.py` | direct outcome under any panel (Local4, Div3L, Lin3, Single) |
| `analysis/p3_eligibility.py` | which calls ever reach verification (P3), and how executed attacks got through |
| `analysis/gate_offline.py` | what a deterministic approve gate would have approved |
| `analysis/trusted_evidence.py` | P2.2 with evidence restricted to structured, non-attacker fields |
| `analysis/ledger_expiry.py` | expiry and identity policies for the stateful replay and ledger checks |
| `analysis/b2_live.py` | the live calibration run and its replay |

### Level 2: re-adjudication with local judges

```bash
python -m analysis.replay_run build        # rebuild every logged judge input -> cache/replay/
python -m analysis.replay_run build-asb    # append the ASB panel rounds
# serve a judge with vLLM on a local port, then query it for every input not yet cached:
python -m analysis.replay_run query --validator L1_mistral --url http://127.0.0.1:8101/v1
python -m analysis.replay_run query --validator L3_gptoss  --url http://127.0.0.1:8103/v1 --reasoning-effort low
```

Validator ids and model names are in `configs/validators.yaml` (L1–L4 form Local4,
R1–R3 the lineage panels). The query refuses any URL that is not local, so the replay
cannot call an API. Votes are cached by a hash of the exact input, so an
interrupted query resumes where it stopped.

### Level 3: full runs

```bash
bash scripts/check_freeze.sh                     # decision code must equal the freeze tag
RUN_TAG=mytag REQUIRE_FREEZE=1 \
  scripts/run_attack_paths.sh q235_local2 cyberops all agenticcyops 3   # GROUP DOMAIN APS CONFIGS TRIALS
```

- `GROUP` selects the primary and panel (`scripts/run_attack_paths.sh` lists them;
  `q235_local2` is the fully local calibration setup).
- `APS` is `all`, `benign`, one path, or a comma list (`ap1,ap2`).
- `CONFIGS` is `all` or one of the log names below.
- Environment switches: `STATE_MODE=persistent`, `DISABLE_PRINCIPLES=P3`, `SEED=<int>`.
- `scripts/run_v29_live.sh` is the exact launcher of the calibration run.
- `scripts/vllm_profiles.sh` has the serving commands used for each model.

Every run writes a header with its commit, freeze tag, and whether the tree was clean.
With `RUN_TAG` set, the harness refuses to start from a dirty tree. Do not edit
tracked files while a run is going: each attack path is a separate invocation, and a
later one will refuse to start.

---

## Names used in the paper and in the logs

| Paper | Log `config` | What it is |
|---|---|---|
| FLAT | `flat` | every agent may call every tool and store; no checks |
| ACL | `acl_hardened` | phase-to-tool and phase-to-store restrictions only |
| JUDGEONLY | `llm_judge` | registry plus the LLM panel on every tool proposal |
| NOJUDGE | `symbolic_only` | FULL without the panel; undecided proposals are escalated |
| FULL (DEFER) | `agenticcyops` | all 28 checks in cascade order |
| FULL \ P*i* | `agenticcyops` + suffix `_disabled_Pi` | leave-one-out ablation |
| JUDGEREST | (offline) | FULL with every rule-surviving call judged, from `replay_panels.py` |
| permissive gate | `agenticcyops_gate_permissive` | deterministic approve gate; evaluated offline in the paper |
| judged writes | `agenticcyops_writejudge` | every write to a critical store goes to the panel |

| Run group | Primary | Panel as run | Role |
|---|---|---|---|
| `q235_div4` | Qwen3-235B-A22B | Div4 | main runs, four domains, all configurations |
| `scout_div4`, `mistral_div3p`, `llama8b_div4` | Llama-4-Scout, Mistral-Small, Llama-3.1-8B | Div4 (Mistral: without itself) | other primaries, CyberOps and finance |
| `q235_div4_persistent`, `q235_div4_persistent3` | Qwen3-235B-A22B | Div4 | state carry-over, two passes |
| `q235_div4_e2` | Qwen3-235B-A22B | Div4 | rule-evading siblings (E2) |
| `q235_local2_v29` | Qwen3-235B-A22B | local2 (Mistral-Small, Gemma-4; 2 of 2) | live calibration at `defense-freeze-v2.9` |

Routing of individual log files to groups is declared in
[`analysis/run_groups.yaml`](analysis/run_groups.yaml); load logs only through
`analysis/runlogs.py`.

---

## The pipeline

| Principle | Surface | What DEFER checks |
|---|---|---|
| P1 Authorized Interface | tools | registry membership; response schema, timing, replay, per-tool MAC; configuration hashes |
| P2 Capability Scoping | tools | phase manifests and action caps; parameter rules and target-in-evidence; output classifier |
| P3 Verified Execution | tools | handoff, context, and intent-chain checks; cross-incident ledger; replay detection; consent; risk scoring and auto-gates; LLM panel; pre-execution hash |
| P4 Memory Integrity | memory | schema; similarity to evidence; metadata; drift; write replay; contradiction |
| P5 Access-Controlled Isolation | memory | phase-to-store policy; field filter; query scope; read-pattern monitor; read sanitization |

![The DEFER cascade](docs/figures/cascade.png)

*Order of checks for a tool call, a memory write, and a memory read. Dark blue: rule;
light blue: contains a similarity threshold; orange: the only judgment-based check; dot:
keeps state across incidents.*

Checks run cheapest and most certain first. Only consequential calls (the manifest
requires verification, or the action has negative impact in a static table) enter P3,
and the panel sees only what no deterministic check decided. Every check fails closed,
and a validator error counts as a rejection. Table VIII of the paper lists all 28
checks with their thresholds; the code is in `host/` (orchestrator, parameter
validator), `consensus/` (P3), and `memory/` (P4, P5). The four domains share the
code and differ only in declarative configuration under `domains/<domain>/configs/`.

---

## Repository layout

```
agents/            phase agents (LLM wrappers with phase prompts and tool lists)
host/              orchestrator (reference monitor), manifests, parameter validation
consensus/         P3: context, ledgers, replay, scoring, auto-gates, validator panel
memory/            P4 write filter, P5 access isolation, memory gateway
mcp_servers/       tool stubs (REST servers per domain)
domains/           four domains: configs, payloads (attacks, benign), seed data
attacks/           harness, injection channels, outcome oracle (effects.py), payload schema
benchmarks/        Agent Security Bench and InjecAgent adapters
analysis/          parsing, statistics, tables, figures, re-adjudication, offline analyses
configs/           panels (validators.yaml) and configuration profiles
scripts/           run launchers, vLLM profiles, freeze and path guards
tests/             unit tests (pytest)
logs/              per-trial JSONL logs of every reported run
results/           generated tables and CSVs
cache/             rebuilt judge inputs (replay/) and cached local judge votes (validators/)
docs/              review response, figures for this README
```

---

## Provenance and known limitations

- **Freeze tags.** Reported runs used the decision code of `defense-freeze-v2.2`.
  Later tags changed only logging, the memory reset of baseline configurations, and
  default-off switches for the targeted arms. `defense-freeze-v2.9` fixes the risk
  scorer's wiring and is used only for the labeled calibration run.
  [`REPRODUCE.md`](REPRODUCE.md) lists every tag and diff.
- **Validator outage.** The original panel (Div4) lost both API validators for part
  of the evaluation. Every panel-dependent result is therefore reported as its
  re-adjudication under Local4, and the as-run values are kept for comparison (paper,
  Table XXII). [`docs/review_response.md`](docs/review_response.md) documents each
  analysis.
- **Dirty-tree runs.** About three fifths of the reported trials come from runs
  launched before the clean-tree guard existed. Their headers record the commit, and
  the decision code at each such commit equals `defense-freeze-v2.2`.
- **Not evaluated.** An attacker who adapts to the defense beyond the one-step
  rule-evading siblings; an external composed defense; benign utility on ASB. AP-3
  was never attempted by any primary. The shipped auto-gates decided no proposal in any reported run.
- **Log names.** Configuration names beginning with `agenticcyops` in the logs denote
  FULL; the project's earlier name survives in log fields and some module docstrings.

---

## Ethics and intended use

All experiments ran on a closed testbed with stub tools and synthetic records. The
attack payloads are prompt-injection strings, poisoned records, and forged tool
responses that target this stub environment and carry canary values. They contain no
working exploit against a real product. The artifact is intended for evaluating
defenses of LLM agent systems.

## License

Code under the MIT License (see [`LICENSE`](LICENSE)). The third-party benchmark
subsets under `benchmarks/` keep their original licenses.
