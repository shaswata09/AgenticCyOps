# Figure tasks: charts for the DEFER paper

Branch `revision-v2`. Save this file at the repo root. Output goes to `paper/figs/*.pdf` (create `paper/` if the paper is not yet checked in; then the tex file expects `figs/<name>.pdf` relative to `paper/`). One script produces everything: `analysis/make_figures.py`, run by `make figures`. Every figure must be regenerable from `results/` and `logs/` with no manual step.

The paper's argument in one line: deterministic checks decide most of the validation in an agentic pipeline, an LLM judge is needed for a measurable remainder, and both the remainder and the cost can be located. The figures should let a reader who skims only the figures reach that conclusion.

## 0. Ground rules

- Read-only for everything except `analysis/make_figures.py`, `analysis/figstyle.py`, `paper/figs/`, and `Makefile`.
- Every figure: one function `fig_<name>(df, ...) -> Path`, called from `main()`. Each function writes `paper/figs/<name>.pdf` and, for quick review, `paper/figs/preview/<name>.png` at 200 dpi.
- Every number plotted must come from `results/eval_attacks/all_trials.csv`, the JSONL logs, `results/asb/`, `results_legacy_v1/`, or `results/benign_panel_rejection.csv`. Never type a number into the script. If a figure needs a number the analysis code does not compute yet, add the computation to `analysis/` and reuse it in `generate_tables.py` so table and figure cannot drift apart.
- Intervals are 95% cluster-bootstrap intervals over variants, reusing the function in `analysis/statistical_tests.py`. Seed the bootstrap (seed 0) so figures are reproducible.
- Use the same configuration set and variant sets as the tables: main arms on 75 variants; leave-one-out arms on the shared 53-variant subset, with Full recomputed on that subset.
- STOP after task F0 and show me the style sheet rendered on one sample figure before drawing the rest.

## 1. Style guide (`analysis/figstyle.py`)

Write one module that every figure imports. It sets matplotlib rcParams and exposes constants.

**Sizes.** IEEE two-column: single-column width 3.45 in, double-column 7.16 in. Heights 2.0 to 2.6 in for single, 2.6 to 3.2 in for double. Fonts: 8 pt body, 7 pt tick labels and legends, 8 pt bold axis titles. Font family: Helvetica or Arial if available, else DejaVu Sans; embed fonts (`pdf.fonttype = 42`). Line width 1.0, marker size 4, spine width 0.6, no top or right spines, light gray y-grid (`#e6e6e6`, 0.5 pt) behind the data, no x-grid.

**Colors (Okabe--Ito, colorblind safe).** Fix them once and reuse everywhere:

| Meaning | Hex |
|---|---|
| Rule-based tier | `#0072B2` (blue) |
| Similarity-threshold tier | `#56B4E9` (light blue) |
| LLM panel tier | `#E69F00` (orange) |
| Flat (no checks) | `#999999` (gray) |
| ACL (connectivity only) | `#BBBBBB` (light gray) |
| JudgeOnly | `#E69F00` (orange, same as LLM tier) |
| NoJudge | `#0072B2` (blue, same as rule tier) |
| Full / DEFER | `#009E73` (green) |
| Attack executed | `#D55E00` (vermilion) |
| Blocked | `#009E73` |
| Not attempted | `#CCCCCC` |
| Benign / cost | `#CC79A7` (purple) |
| Emphasis or annotation | `#000000` |

The TL;DR figure in the paper uses its own pastel palette; leave it.

**Conventions.** Configuration labels exactly as in the paper: `Flat`, `ACL`, `JudgeOnly`, `NoJudge`, `DEFER` (use `DEFER` for Full in figures). Principle labels `P1` to `P5`. Attack paths `AP-1` to `AP-15` with the short names from the appendix table. Percentages on axes as `0`, `20`, `40` with the axis title carrying the unit ("Attack success (%)"). Intervals as thin black error bars with 2 pt caps. Direct labels on bars for headline values (one decimal). Legends outside the plot area when they would cover data; otherwise upper right. Titles inside the figure only for panels of a multi-panel figure (`(a)`, `(b)`, bold, left-aligned). No figure-level title; the caption carries it. Save with `bbox_inches="tight"`, `pad_inches=0.02`.

**Text.** Every figure gets a one-line "reader takeaway" written as a comment above its function and returned in a `figures.json` manifest (`name`, `file`, `takeaway`, `data_sources`, `n`). I will use the takeaways in the captions.

## 2. Figures

### F0. Style sample (STOP after this)
Draw F1 below with the style sheet, render the PNG, and stop for my approval of fonts, colors, and size.

### F1. The judgment boundary  (main figure; double column)
Two panels sharing the x-axis of five configurations in the order `Flat`, `ACL`, `NoJudge`, `DEFER`, `JudgeOnly` (left to right is "no judgment" to "all judgment", with DEFER between).
- (a) Attack success (%) on the development split with cluster-bootstrap intervals; bars colored by configuration.
- (b) Legitimate tool proposals denied (%) on the 20 benign scenarios; same colors. Add a second thin bar or a marker for "benign tasks completed (%)" on a right axis, or a small annotation above each bar.
- Below or beside each bar, print the judged fraction ("judged: 0 / 0 / 0 / 34 / 100 %").
- A light shaded band spanning NoJudge to JudgeOnly labeled "judgment boundary", with DEFER marked.
Data: `all_trials.csv` (group `q235_div4`, domain `cyberops`, suffix empty), logs for the judged fraction (`consensus_result` events with `votes` over `tool_proposed`).
Takeaway: never judging is the safest and the least usable; judging everything is neither safe nor cheap; DEFER sits near the safety of NoJudge at the usability of JudgeOnly.

### F2. Who stops the attack: first interception by tier  (single column)
Stacked horizontal bars, one per evidence source: `Development`, `Transfer (3 domains)`, `ASB replay (405 actions)`, `ASB live (1,606)`. Segments: rule-based, similarity-threshold, LLM panel, in tier colors, labeled with percentages. n printed at the right end of each bar.
Data: `all_trials.csv` (blocked trials under `agenticcyops`, `blocked_by` mapped to tiers with the same mapping as `generate_tables.py`); `results/asb/e2e_validator_group_q235_div4_div4` and `results_legacy_v1/asb/*` (`defense_mechanism`).
Takeaway: deterministic checks decide three quarters of the interceptions on policy and structure attacks, and about a third on semantic third-party attacks.

### F3. Per-attack-path heatmap  (double column)
Rows: AP-1 to AP-15 with short names, grouped visually into model-mediated and harness-proposed. Columns: `Flat`, `ACL`, `JudgeOnly`, `NoJudge`, `DEFER`. Cell: attack success (%) on the development split, sequential colormap from white (0) to vermilion (100), value printed in each cell, `n` in the row label. Right of the heatmap, a narrow column showing the modal first interceptor under DEFER (tier color chip with the principle label).
Data: `all_trials.csv`, group `q235_div4`, domain `cyberops`.
Takeaway: JudgeOnly leaves whole rows red that DEFER clears; the rows that stay red under DEFER are the harness-proposed ones.

### F4. Paired outcome per variant: JudgeOnly versus DEFER  (single column)
A 75-row dot strip (or a 15 x 5 grid, one row per AP, one cell per variant). Each variant is a small square split diagonally: upper-left color = outcome under JudgeOnly, lower-right = outcome under DEFER (executed at least once = vermilion; always blocked = green; never attempted = gray). Count the three disagreement classes in a legend: "JudgeOnly fails, DEFER holds: 20", "DEFER fails, JudgeOnly holds: 1", "both fail: 3".
Data: `all_trials.csv`, paired on `domain/ap/variant`.
Takeaway: the cascade dominates the judge-only pipeline almost variant by variant.

### F5. Leave-one-out ablation  (single column)
Dumbbell or bar chart on the shared 53-variant subset: x = ASR (%), rows = `DEFER (subset)`, `minus P1` … `minus P5`, with intervals. A second small panel to the right with the benign any-denial (%) for the same arms. Mark the DEFER baseline with a vertical dashed line.
Data: `all_trials.csv`, suffixes `_disabled_P*`, group `q235_div4`, domain `cyberops`; subset = variants present in the `_disabled_P1` arm.
Takeaway: P3, P2, and P4 each stop attacks the others miss; P1 and P5 do not show on this subset (P5 is measured in F6).

### F6. P5 evidence on the read-dependent attack paths  (single column, can share a row with F5)
Grouped bars for AP-4 (and AP-14 if non-zero anywhere): configurations `Flat`, `ACL`, `JudgeOnly`, `DEFER minus P5`, `DEFER`; bar = ASR (%), a hollow marker above each bar = exposure (%).
Data: `all_trials.csv`, group `q235_div4`, domain `cyberops`, `ap in (ap4, ap14)`.
Takeaway: reads are the one place where the judges cannot help and the store policy is what closes the leak.

### F7. Panel composition: security versus benign rejection  (single column)
Scatter: x = benign proposals rejected (%), y = injected actions let through (%), one point per panel (`Single`, `Div3`, `Div4`; `Lin3` plotted at its security value with an open marker and a note "benign n/a"). Label each point; draw a faint line from Single to Div3 to Div4 to show the path as the panel grows. Annotate Lin3 with "same size as Div3, shared lineage".
Data: `results/benign_panel_rejection.csv`, `results/asb/e2e_validator_group_q235_div4_{single,lin3,div3,div4}`.
Takeaway: diversity buys security; size buys the last three points at five points of benign rejection; lineage kills it.

### F8. Validator behavior  (single column, two small panels)
- (a) Pairwise Cohen's kappa heatmap for the four Div4 validators (4 x 4, values printed, sequential colormap), diagonal shows each validator's reject rate (%).
- (b) Quorum sweep: x = quorum (1..4 of 4), y = proposals approved (%), a line with markers; mark the deployed quorum (3).
Data: `consensus_result` events with `votes` and `validators` in `logs/*_eval_attacks_q235_div4/agenticcyops_*.jsonl` (errors count as reject).
Takeaway: the judges agree only moderately, so the quorum is a design knob with large effect.

### F9. Where the cost goes  (double column, three panels)
- (a) Benign tool proposals denied (%) per domain under DEFER, stacked by the principle that denied them (P2 parameter checks, P3 deterministic, P3 LLM panel, P4, P5, redactions as a hatched segment). Domains: CyberOps, Finance, Healthcare, Legal.
- (b) Median incident latency (s) on benign incidents for `Flat`, `NoJudge`, `DEFER`, `JudgeOnly` (development domain), stacked into "primary model", "deterministic checks", "LLM panel" using the per-check latency fields in the logs; p95 as a whisker.
- (c) Tokens per incident: primary versus validator, same four configurations.
Data: benign trials in `all_trials.csv` and the per-trial `deny_mech::*` counts and latency breakdown from the logs.
Takeaway: the judges are three quarters of the added time; outside the development domain, the judges and P4 are most of the blocked work.

### F10. State carry-over  (single column)
Line chart: x = position of the benign incident in the persistent-state sequence (1..20 for CyberOps; the transfer domains as a second panel or lighter lines), y = denials per incident; a horizontal dashed line at the isolated-state mean. Shade the region above the isolated mean.
Data: `logs/*_eval_attacks_q235_div4_persistent/` (order incidents by timestamp), `all_trials.csv` for the isolated baseline.
Takeaway: the pipeline is already saturated at the first benign incident after 30 attacks; state must expire.

### F11. Transfer across domains and primaries  (double column)
Dot-and-interval chart: rows = four domains (Qwen3-235B) and four primaries (CyberOps, plus finance as lighter dots); columns of dots for `Flat`, `ACL`, `DEFER` with intervals for DEFER; a second axis or panel with benign denied (%) under DEFER for each row.
Data: `all_trials.csv`, all groups with suffix empty.
Takeaway: security transfers across domains and models; cost does not.

### F12. Channels  (single column)
Grouped bars per channel (C1 task input, C2 tool response, C3 memory, C4 handoff, C5 rationale): `Flat` versus `DEFER` ASR (%), with a hollow marker for exposure (%). Annotate C2 with "legal AP-2 poisoning" since its DEFER residual is entirely that.
Data: `all_trials.csv`, group `q235_div4`, all domains, `channel` and `exposed` columns.
Takeaway: every channel is exposed and four of five are closed; content-plausible poisoning on the tool-response channel is the open one.

### F13. Third-party benchmarks  (single column)
Grouped bars by ASB attack family (direct PI, indirect PI, memory poisoning, PoT backdoor): `Flat`, `ACL`, `DEFER`, plus an "emitted by the primary" hollow marker. Pooled over the four legacy model configurations; n per family under the labels.
Data: `results_legacy_v1/asb/e2e_validator_group_{A,C,D,E}/general/results.csv`.
Takeaway: ACL does nothing against injected actions on tools the agent already holds; DEFER blocks 94% of what the models emit.

### F14. Cascade pipeline (design figure; TikZ, double column)
Not data. Draw the order of checks as a left-to-right flow with three colored tiers: tool call → P1 registry → P2 manifest and parameters → [P3 context, sequence, ledgers → risk score and auto-gates → LLM panel → pre-execution hash] → execute → P1 response integrity → P2 output classifier; below it the memory write path (P5 policy → six P4 checks) and read path (P5 gates → store → redact → sanitize). Each box carries its check ID (P2.2 etc.) and a small icon for "keeps state". Annotate the LLM panel box with "judged: 34% of attack proposals" and the deterministic block with "76% of interceptions". Use the tier colors. Write it in TikZ in `paper/figs/cascade_pipeline.tex` so the numbers come from a small `\def` block that `make figures` regenerates from the data.
Takeaway: this is what "evaluate what you can, judge what you cannot" looks like as a pipeline.

### F15. Adaptive attacker (pending data)
Write the function now against the expected schema (`results/adaptive/*.csv` with `mode`, `target_set`, `iteration`, `asr`), skip gracefully if the file is missing. Line chart: ASR@k for k = 1..10, black-box and white-box, in-house and ASB-50 targets.

## 3. Wiring

- `Makefile`: `figures: ; python -m analysis.make_figures --out paper/figs` and make `paper-tables` depend on the same computations.
- `paper/figs/figures.json`: manifest with takeaways and n, regenerated on every run.
- A test `tests/test_figures.py` that runs `make_figures` on the committed data and asserts every expected PDF exists, is under 2 MB, and that `figures.json` contains no NaN.
- Report to me: the PNG previews of every figure in one contact sheet (`paper/figs/preview/contact_sheet.png`), and the manifest.

## 4. Definition of done

- `make figures` regenerates all PDFs from the repository data with no manual step and no hard-coded numbers.
- Every figure follows `figstyle.py`; the same configuration or tier has the same color in every figure.
- Each figure has a takeaway in the manifest that a non-specialist can understand without the body text.
