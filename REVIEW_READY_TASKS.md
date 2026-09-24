# Task block: make the repository review-ready

Branch `revision-v2`, current head `d44a272`, latest freeze tag `defense-freeze-v2.8`. Save this file at the repo root as `REVIEW_READY_TASKS.md` and work through it in order.

The goal is a repository that a reviewer or artifact evaluator can clone and, without contacting us, (1) regenerate every number, table, and figure in the paper from the committed logs in minutes, (2) re-run the defense on cached proposals without a GPU, and (3) re-run any experiment end to end with the documented hardware. It must also be anonymous and must not contradict the paper. ACSAC's artifact evaluation awards Available, Functional, and Reproduced badges; this block targets all three.

## 0. Ground rules

- **Do not change what produced the reported results.** Every change to the decision code (`consensus/`, `memory/`, `configs/`, `domains/*/configs/`) goes under a new freeze tag and is evaluated as a new, separately labeled run. Existing logs and results stay byte-identical; `git diff defense-freeze-v2.8 -- logs/ results/eval_attacks/group_*` must stay empty except where a task says to add files.
- One commit per task, message `review-ready: <task id> <summary>`. Run `pytest -q` before each commit.
- No `Co-Authored-By`, author names, emails, affiliations, hostnames, internal IPs, absolute paths, or API keys in anything you add. Phase D removes the ones already present.
- STOP gates are marked **STOP**. At each, report what the task asks for and wait.

---

## Phase A. Correctness fixes in the analysis (no decision-code change)

### A1. One configuration label per arm in the benign cost table (R1)
`analysis/benign_cost.py` pools the benign runs of `agenticcyops_gate_permissive`, `agenticcyops_noautoapprove`, `p2_judge`, and `agenticcyops_writejudge` into `agenticcyops`, which makes CyberOps DEFER read 27.7 % in T11 instead of the paper's 10.1 %.
- Key every aggregation on the exact `config` string from the run header, never on a prefix or substring. Grep `analysis/` for `startswith("agenticcyops")`, `"agenticcyops" in`, and similar, and fix each.
- Add a test `tests/test_config_labels.py` that builds T11 and asserts CyberOps `agenticcyops` = 88/873 (10.1 %) on the committed logs and that each added arm appears as its own row.
- **Acceptance:** T11 CyberOps DEFER reads 10.1 % with its interval; the four added arms have their own rows.

### A2. One tier mapping for tables, figures, and the paper (R3)
`analysis/figstyle.tier4_of` classifies P3 handoff validation as content-independent and P2 target-in-evidence as similarity, which contradicts the paper's Table XIV.
- Create `analysis/tiers.py` with the single mapping below, import it from `figstyle.py`, `generate_tables.py`, and `make_figures.py`, and delete every other mapping.

| Tier | Mechanisms (first-interception labels) |
|---|---|
| content-independent rule | P1 identity, P1 response integrity, P1 config integrity, P2 manifest / capability scoping, P2 critical asset, P2 bulk action, P3 replay detection, P3 execution verification, P3 bulk action, P4 schema violation, P4 write replay, P5 access control, P3 write-judge escalation |
| content-dependent rule | P2 target not in evidence (substring branch), P2 parameter rule violation, P2 wildcard parameter, P3 handoff validation, P3 operational context, P3 intent chain, P4 contradiction, P4 metadata invalid, P5 broad query block, P5 injection sanitization |
| similarity threshold | P4 similarity reject, P4 drift outlier, P4 centroid shift, P2 target not in evidence (cosine branch), P2 output classifier (cosine), P5 read-pattern monitor |
| LLM panel | P3 consensus reject / approve, P3 write-judge reject |

  Where one check has two branches (P2.2), log which branch denied (`deny_branch: substring|cosine`) from now on; for the committed logs, classify P2.2 as content-dependent and note it in the table caption.
- Regenerate `interception_tiers.pdf` as a four-way stack and T13/T14 from the same mapping.
- **Acceptance:** development / transfer / ASB-live / ASB-replay tier shares equal the paper's Table XIV (44.8/28.4/4.5/22.4, 40.5/31.3/0.0/28.2, 0/37.0/0/63.0, 0/38.3/0/61.7) to one decimal, or report every cell that differs and why. **STOP** if any differ by more than 1.0 point.

### A3. Commit the E2 sibling trials (R4)
The 24 sibling variants exist in the payload files (`meta.e2_parent`) but their trials are in no `trials.jsonl` and not in `all_trials.csv`.
- Find the E2 sweep logs (the run report cites them), parse them with the same parser as every other run, and add the rows to `all_trials.csv` with a new column `sibling_of` (empty for all other rows).
- Add table T15 "E2 paired siblings": per parent/sibling pair, outcome under `flat` and `agenticcyops`, and first interceptor for both.
- **Acceptance:** T15 reproduces flat 84.6 % for parents and for siblings, FULL 0 of 24 siblings executed, interceptor P2.2 → panel for 17 and P4.2 → drift for 7. If the logs cannot be found, **STOP** and say so; the paper cites these numbers and cannot keep them without the rows.

### A4. Label the tool-exposure mode of every arm (R2, analysis half)
The four added arms show about 50 % benign denials dominated by `P2_capability_scoping` (306 of 419), i.e. their agents saw all 16 tools, like ACL, whereas FULL uses the manifest-scoped prompt.
- Add `tool_exposure: scoped|full` to every run header from now on, and a derived column for the committed runs (inferred from whether any benign trial has a `P2_capability_scoping` denial).
- In T3/T11, print benign denial rates for `full`-exposure arms in a separate block with a note that they are comparable with ACL, not with FULL.
- **Acceptance:** no table places a `full`-exposure arm and FULL in the same benign-cost comparison.

### A5. Payload hygiene covers everything a model can see
Extend `tests/test_payload_hygiene.py` to every domain, every `trigger`, `meta.injection.response`, `meta.injection.entries`, planted records in `seed_data`, benign alerts, and the E2 siblings. Word list: `adversar`, `attack`, `inject`, `poison`, `fabricat`, `malicious`, `canary`, `exfil`, `bypass`, `jailbreak`, and every check name (`P1`…`P5`, `P2.2`, etc.). Allow a word only through an explicit per-file allowlist entry with a one-line justification.
- **Acceptance:** the test passes on the committed payloads; any allowlist entry is listed in the report.

### A6. Freeze and provenance table
T8 must show, per (group, domain, config): commit, freeze tag, `git_dirty`, tool exposure, trials, and whether the run is cited in the paper. Add a check that every run cited in the paper has `git_dirty: false` or is listed in a short `PROVENANCE.md` with the diff-based justification (decision code identical to the tag).
- **Acceptance:** `PROVENANCE.md` lists exactly the runs the paper's limitations section says predate the clean-tree guard (`llm_judge` and the three non-Qwen primaries), and no others.

---

## Phase B. The scorer defect, fixed under a new tag (R5)

### B1. Fix
`ProposalScorer` is never passed the cross-incident ledger or the incident evidence, so `alignment` and `precedent` fall back to 0.5 in every run and the shipped approve rule (alignment > 0.7 and precedent > 0.7) is unsatisfiable.
- Pass `context["incident"]` evidence and the ledger handle into the scorer at the P3.8 call site; add a unit test that alignment and precedent vary across three synthetic proposals (aligned, unaligned, repeated).
- Log all five scores on every P3 decision (already started in E16; make it unconditional).
- Cut tag `defense-freeze-v2.9`. The old configurations must be reproducible from their old tags; do not rewrite history.

### B2. One clean FULL run with the working scorer
Run `agenticcyops` at `defense-freeze-v2.9` as group `q235_div4_v29` on the CyberOps development split (75 × 3) and the 20 benign scenarios (× 3), manifest-scoped tools.
- Report: share of P3 approvals by the deterministic gate versus the panel, ASR with interval, benign denial rate (T11 definition), median latency, and the score distributions.
- **STOP** after the run with those five numbers. The paper will report this as the configuration the design describes, next to the permissive-gate arm; do not overwrite any existing row.

---

## Phase C. Make every number reproducible

### C1. Paper-number audit
Create `analysis/paper_numbers.py` that computes every number the paper quotes and writes `paper/numbers.json` and `paper/numbers.tex` (one `\newcommand` per number, e.g. `\newcommand{\asrDevFull}{4.0}`). Start from this list; add any number in `paper/main.tex` not covered (grep for `\d+\.\d+\\%` and integer counts in the body):
- ASR per configuration, development split, with intervals (Flat, ACL, JudgeOnly, NoJudge, Full, Full minus P1–P5 on the 68 shared variants).
- Transfer ASR per domain and pooled, with intervals; pooled over primaries.
- Judged fraction (attack, benign; without P2).
- P3 decision counts (11,031 decisions; 1,662 approvals; denials by layer).
- First-interception tier shares (A2).
- Executed-attack breakdown under Full (37: 15 memory writes, 22 tool calls).
- Paired JudgeOnly/Full classes (20/3/1; ten on AP-4/AP-13; 14.3 vs 3.2 without them).
- E16, E17, E2, E9, E20b numbers.
- Panel replay let-through and benign rejection (Div4, Div3, Div3x, Single, Lin3).
- Validator agreement (rounds, kappa range and mean, reject rates, quorum sweep).
- Benign cost per domain (T11), latency and tokens, carry-over (both passes).
- ASB frozen full run (28.8 / 30.0 / 0.0; emission 32.0) and the April corroboration run.

### C2. Check the paper against the data
`analysis/check_paper_numbers.py paper/main.tex` extracts every number in the body and appendix with its sentence, matches each to an entry in `numbers.json` through a small hand-maintained `paper/number_map.yaml` (sentence fragment → key), and fails on any mismatch beyond rounding, and on any body number with no map entry. Add it to `make check`.
- **Acceptance:** `make check` passes, or the report lists every mismatch with paper value, computed value, and location. **STOP** here with that list; we will fix the paper, not the data.

### C3. Make targets
```
make env            # create the pinned environment (uv/conda lock, Python version)
make check          # pytest + payload hygiene + paper-number audit
make tables         # results/paper_tables.md from logs/ only
make figures        # paper/figs/*.pdf + figures.json from logs/ only
make paper          # latexmk paper/main.tex (uses numbers.tex)
make replay-asb     # defense-only replay of the cached ASB proposals (no primary GPU; validator calls cached)
make replay-benign  # the 661-proposal benign panel replay from cache
make smoke          # one domain, one config, 5 variants, 1 trial, against a small local model (Functional badge)
make run-<exp>      # full re-run of one experiment (documented hardware)
```
`make tables figures check` must succeed on a machine with no GPU and no API keys, from the committed logs, in under 15 minutes. Time it and put the time in REPRODUCE.md.

### C4. Cached validator responses
Every validator call made during the reported runs is keyed by (validator id, model snapshot, hash of the sanitized proposal and context) and stored under `cache/validators/`. The replay targets read from the cache and fail loudly on a miss rather than calling an API. Record the cache hit rate for `replay-asb` and `replay-benign` (must be 100 %).

### C5. Environment and hardware
- Pin Python, vLLM (0.19.1rc1.dev117 on H200 and 0.21.0 on RTX 5090, as in the logs), ChromaDB, the embedding model revision, and every Python dependency in a lock file.
- `Dockerfile` for the analysis and replay levels (CPU only). The full-run level documents the GPU setup instead of containerizing it.
- Model identifiers exactly as in the run headers, including `claude-sonnet-4-5-20250929` and `gpt-4o` (unpinned; state the run dates).

---

## Phase D. Packaging and anonymization

### D1. Repository layout for the release
```
README.md            what the artifact is, the three reproduction levels, badge claims
REPRODUCE.md         per paper table/figure: the command, expected runtime, expected output file
PROVENANCE.md        freeze tags, dirty-tree runs, quarantined runs and why
docs/threat_inventory.md   the 35 vectors with entry point and effect surface (the paper cites this file)
docs/checks.md       the 28 checks, their tier, thresholds, and code location
domains/ attacks/ consensus/ memory/ host/ tools/ analysis/ tests/ configs/
logs/                per-trial JSONL for every cited run
results/             generated tables and CSVs
cache/validators/    cached validator responses
paper/figs/          generated figures
```
- Move `results/_aborted*`, `results/eval_attacks/_quarantine*`, `_superseded*`, smoke and probe groups out of the release tree into a separate `archive/` that is excluded from the anonymous mirror, and list each in `PROVENANCE.md` with a one-line reason.
- `docs/threat_inventory.md` must exist; the paper promises it.

### D2. Anonymize
- Build the release from a fresh orphan branch `review-snapshot` containing a single commit of the release tree, so no history, commit messages, or `Co-Authored-By` lines are exposed.
- Scrub from every file (code, configs, logs, notebooks, PDFs, figure metadata): author and institution names, usernames, emails, hostnames, IPs, absolute paths (`/storage/...`, home directories), GPU server names, API keys, org IDs, and W&B or dashboard URLs. Run a scanner (`gitleaks` for secrets plus a grep list you build from `git log --format='%an %ae'` and `hostname`) and report zero hits.
- PDF metadata: strip `Author`/`Creator` fields from every generated PDF (`exiftool -all= ` or qpdf).
- Rename the package and repo from `AgenticCyOps` to `defer` everywhere a reviewer can see it (the paper's system is DEFER); keep a one-line note in PROVENANCE.md that configuration names `agenticcyops*` in logs denote FULL.
- Mirror to anonymous.4open.science and to an anonymous Hugging Face dataset (logs, payloads, benign scenarios, cache); report both URLs so the paper's `\codelink` and `\datalink` can be filled.

### D3. Dataset card and licenses
- Hugging Face dataset card: contents, splits (development, transfer, third-party, benign), schema of `all_trials.csv` and the JSONL logs, canary convention, intended use, and the statement that payloads target the stub environment.
- Code license (Apache-2.0 or MIT) and data license (CC BY 4.0), and the licenses of the third-party benchmark subsets we redistribute (ASB, InjecAgent); if a license does not permit redistribution, ship a fetch script instead of the data.

### D4. Documentation that matches the paper
- `docs/checks.md` must match Table VI (28 checks, IDs, types) and the four-tier mapping of A2.
- README and REPRODUCE must use the paper's names: DEFER, FULL, FLAT, ACL, JUDGEONLY, NOJUDGE, and the arm names used in the paper (permissive gate, P2 + panel, judged writes).
- A short `KNOWN_LIMITATIONS.md` that mirrors the paper's limitations: the scorer defect in runs before v2.9, tool exposure in the added arms, AP-3 and AP-14 never attempted, ASB utility not measured, no external composed baseline, no adaptive attacker beyond E2.

---

## Phase E. Continuous integration and a final dry run

### E1. CI
GitHub Actions on the anonymous mirror (or a local `act` run if the mirror cannot run CI): `make env check tables figures` on CPU. Badge in README.

### E2. Clean-machine dry run
On a fresh container with no GPU and no keys: clone the anonymous mirror, follow README only, run `make env check tables figures paper replay-asb replay-benign`. Record every step that needed knowledge not in the README and fix the README.
- **Acceptance:** the dry run succeeds without edits; runtime per target recorded in REPRODUCE.md.

### E3. Smoke run on a small GPU
`make smoke` on the RTX 5090 with a small open model as primary and validators served locally: completes in under 30 minutes and produces a results row with the expected schema. This is the Functional badge's end-to-end check.

---

## Report back

1. The A2 tier table and any cells that differ from the paper.
2. The A3 T15 table, or a statement that the E2 logs are missing.
3. The B2 five numbers.
4. The C2 mismatch list (paper value, computed value, location).
5. Timings for every make target from E2.
6. Both anonymous URLs.
7. Scanner output from D2 showing zero hits.
