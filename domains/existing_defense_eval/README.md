# Eval I — Existing IPI-Defense Bypass Evaluation

This directory contains the evaluation that establishes the **necessary
condition** for the AgenticCyOps contribution: the 15-AP × 4-domain
dataset bypasses every published IPI defense, so the P1-P5 architectural
stack isn't redundant with off-the-shelf solutions.

Without this evaluation a reviewer can fairly object: *"why not just
deploy a fine-tuned detector?"* This eval produces the headline tables
that answer that question.

---

## Methodology

Based on the standard static-filter and prompt-modification evaluation
patterns from:

- **Yi et al., NAACL 2025 Findings** —
  ["Adaptive Attacks Break Defenses Against Indirect Prompt Injection
  Attacks on LLM Agents"](https://aclanthology.org/2025.findings-naacl.395.pdf).
  Defines the 8-defense taxonomy below; the methodology is to test each
  defense independently against a benchmark attack dataset.
- **Yi et al., 2023** — BIPIA benchmark. Established the
  per-attack-family bypass-rate reporting we use.
- **Liu et al., ACL 2024** — InjecAgent. Static-filter eval protocol;
  ASR-valid vs ASR-targeted distinction.
- **Chen et al., 2024** — StruQ. Delimiter (D5) and adversarial-training
  baseline reference.
- **Debenedetti et al., NeurIPS 2024** — AgentDojo. Agent-level
  evaluation pattern for prompt-modification defenses (D4-D6).

### Defenses under test

| ID  | Defense                  | Mode          | Model / mechanism                                                |
|-----|--------------------------|---------------|-------------------------------------------------------------------|
| D1  | Fine-tuned IPI detector  | Static filter | `ProtectAI/deberta-v3-base-prompt-injection-v2` (off-the-shelf)  |
| D2  | LLM-based detector       | Static filter | Qwen3-32B judge with binary Yes/No prompt                         |
| D3  | Perplexity filtering     | Static filter | GPT-2 log-probabilities; threshold tuned on benign baseline       |
| D4  | Instructional prevention | Prompt mod    | Qwen3-32B target with anti-injection system-prompt suffix         |
| D5  | Data-prompt isolation    | Prompt mod    | Qwen3-32B target; untrusted content wrapped in `<untrusted>` tags |
| D6  | Sandwich prevention      | Prompt mod    | Qwen3-32B target; task reminder re-injected after untrusted span  |
| D7  | Paraphrasing             | Static filter | Qwen3-32B paraphraser rewrites untrusted text                     |

D8 (adversarial fine-tuning) is excluded from runs — compute prohibitive
and not deployable per-domain without retraining. Discussed analytically
in the writeup as a comparison point.

### Two evaluation modes

**Static filter (D1, D2, D3, D7):** For every attack payload, extract
untrusted text spans, apply the defense's classifier/filter to each
span, and record whether *any* span was flagged. Bypass = no span
flagged. This mirrors the BIPIA / InjecAgent static evaluation.

**Prompt modification (D4, D5, D6):** Construct the system+user message
that the Monitor agent would receive with the defense's prompt
modification applied. Call a target LLM (Qwen3-32B). Parse the LLM's
completion to determine whether it would have emitted the malicious
tool call. Bypass = LLM complied with the attacker's instruction. This
mirrors the AgentDojo / Yi et al. NAACL 2025 prompt-defense evaluation.

### Attack-path taxonomy (key analytical move)

The 15 APs split into two categories:

- **IPI APs (10):** AP-1, 2, 3, 4, 5, 8, 9, 10, 11, 14 — the ones
  these defenses are *designed* to catch.
- **Structural APs (5):** AP-6 (replay), AP-7 (action chain), AP-12
  (concurrent bypass), AP-13 (adversarial memory write), AP-15
  (infrastructure integrity) — these target system mechanics, not the
  LLM's text-processing surface. Existing IPI defenses cannot help.

The headline finding lives in the contrast: existing defenses cap out
at *partial* coverage of IPI APs and have **0% coverage of structural
APs**. AgenticCyOps' P1-P5 is the only stack that covers both.

### Metrics

- **Bypass rate** — fraction of (variant × trial) cases where the
  defense failed to flag (or failed to deter) the attack. Per-AP,
  per-category, overall.
- **Bootstrap 95% CI** on bypass rates (n=2000 resamples).
- **Per-variant heatmap** — exposes which variants exploit which gaps.
- **McNemar's paired** vs. no-defense baseline for significance.
- *(Future)* False-positive rate on benign workflows.

### Run budget per notebook

- 15 APs × 5 variants × 3 trials = 225 trials per (defense × domain).
- D1, D3: < 1 minute on CPU. D2, D4-D7: ~5-15 minutes on a single GPU
  (Qwen3-32B local). No API spend if all-local.
- Logs land in `<notebook_dir>/logs/<defense>_<domain>_<ts>.jsonl`,
  schema-compatible with `logs/<eval>/` so the existing analysis
  pipeline can ingest.

---

## Directory layout

```
domains/
├── existing_defense_eval/
│   ├── README.md                          # this file
│   └── common/                            # shared utilities (no code outside domains/)
│       ├── attack_loader.py               # loads AP payloads + untrusted spans
│       ├── attack_categories.py           # IPI / Structural taxonomy
│       ├── metrics.py                     # bypass rate, bootstrap CI, McNemar
│       ├── plotting.py                    # 4 standardized charts
│       ├── log_writer.py                  # JSONL writer
│       └── evaluator.py                   # filter / prompt eval loops
├── cyberops/existing_defense_eval/
│   ├── d1_finetuned_detector.ipynb
│   ├── d2_llm_detector.ipynb
│   ├── d3_perplexity_filter.ipynb
│   ├── d4_instructional_prevention.ipynb
│   ├── d5_data_prompt_isolation.ipynb
│   ├── d6_sandwich_prevention.ipynb
│   ├── d7_paraphrasing.ipynb
│   └── logs/                              # produced at runtime
├── healthcare/existing_defense_eval/      (same 7 notebooks + logs/)
├── finance/existing_defense_eval/         (same 7 notebooks + logs/)
└── legal/existing_defense_eval/           (same 7 notebooks + logs/)
```

28 notebooks total: 7 defenses × 4 domains. Each is self-contained — it
downloads the required model, runs the eval, plots results, and writes
its log file into the same directory. All notebook code is thin glue;
the substance lives in `existing_defense_eval/common/`.

## How to run

```bash
cd domains/cyberops/existing_defense_eval
jupyter nbconvert --to notebook --execute d1_finetuned_detector.ipynb
# or open in JupyterLab and run cells interactively
```

To aggregate results across all defenses for one domain, run the
optional aggregation cell at the bottom of any notebook (it scans the
sibling `logs/` directory and produces a comparison chart).
