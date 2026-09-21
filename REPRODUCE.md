# Reproducing the revision-v2 results

Everything below runs from a checkout at the freeze tag named in the run
headers. Runs write `logs/<domain>_eval_attacks_<group>[...]/*.jsonl`; every
table and PDF is rebuilt from those logs with no LLM calls.

## Freeze tags

| Tag | Commit | What it freezes |
|---|---|---|
| `defense-freeze-v2` | see `git show` | the defense stack used for the first full programme |
| `defense-freeze-v2.1` | `a369d18` | v2 plus one agent-output parser fix (`agents/base_agent.py`): a JSON array/scalar answer is free text instead of a crash. Frozen defense directories byte-identical to v2. |
| `defense-freeze-v2.2` | tagged on the T7 commit | v2.1 plus the tool-response / memory-channel measurability work (T1–T7 below). **No defense decision changed.** |

### What changed between `defense-freeze-v2.1` and `defense-freeze-v2.2`

The diff in the decision directories is **empty**:

```
git diff defense-freeze-v2.1 defense-freeze-v2.2 -- consensus memory configs domains/*/configs
```

`mcp_servers/`, `agents/`, and `logging_utils/` are also unchanged. The only
frozen paths that differ are:

| Path | Change | Decision impact |
|---|---|---|
| `host/orchestrator.py` | **logging only** (+25/−4): `injection_served` events where the host applies a tool-response, handoff, or proposal injection; `result_ids` / `sanitized_ids` on the `memory_read` allow event. Every hunk is inside an `if self.logger:` block. | none |
| `attacks/harness.py` | `resolve_tool` before the port lookup; an undeliverable injection is `outcome=error` / `blocked_by=injection_not_delivered` and the incident is not run; seeded memory records carry `doc_id`; `alert_text` served at trial start; memory exposure emitted after the trial; `exposed`/`channel` results columns; `refuse_if_dirty` guard. | none (harness, not defense) |
| `attacks/effects.py` | `exposed` flag on the verdict; new `mem_read` effect kind; `TOOL_ALIASES` imported from the payload schema. | none (oracle) |

Unfrozen paths changed in the same span: `attacks/payload_schema.py`
(`TOOL_ALIASES`, `resolve_tool`, stricter `validate_payload`, `--validate-all`,
`--assert-measurable`), `attacks/build_channel_p5_variants.py` (generator),
`analysis/parse_logs.py`, `scripts/run_revision.sh`, `scripts/run_attack_paths.sh`,
`Makefile`, tests, and the AP-2 / AP-3 / AP-4 / AP-14 payload files
(`domains/*/payloads/`).

Payload changes (all four domains unless noted):

* AP-2 / AP-3: `meta.injection.tool` names the registered tool id (12 variants
  previously used a `_response` suffix or an alias and were never delivered).
* AP-14: a memory-channel attack in every domain — a planted record in an
  analyze-readable store, leading with the read query's phrasing so it ranks
  in the top-3, with an operational next step that names a unique canary.
* AP-4 v1–v5: canary planted in a store the report phase cannot read
  (`p5_target=store_policy`) or, legal v4/v5, in a summary-only store
  (`field_filter`); healthcare keeps `mem_write` and gains a canary.
* AP-4 v6 / v7 (new, every domain): P5 read families — an unauthorised store
  read (`store_policy`) and a broad "dump" query (`query_scope`), scored with
  the `mem_read` effect kind; `channel=alert_text`, no canary.
* AP-2 legal: canary on all five `exfil` variants.

## Environment

* Python env `agenticcyops` (conda). `make test` runs the suite.
* `.env` (git-ignored) holds API keys, `SEED`, and `REMOTE_5090_URL` /
  `REMOTE_5090_API_KEY` for the Llama-3.1-8B node. Never commit it.
* Model weights under `models/` (see `scripts/run_revision.sh preflight`).
* vLLM profiles (`scripts/vllm_profiles.sh start q235|mid`): `q235` serves
  Qwen3-235B (TP=4) plus the V1/V5 validators; `mid` serves Llama-4-Scout,
  Mistral-Small, DeepSeek-R1-Distill-32B, Qwen3-14B plus V1/V5.

## Gates that run before every stage

```
make check-payloads      # --validate-all, --assert-measurable, hygiene test
scripts/check_freeze.sh  # HEAD after the tag, frozen dirs identical and clean
```

The harness itself refuses a non-smoke run when the tree has uncommitted
tracked changes (`git_dirty=true` in the header).

## Stages (scripts/run_revision.sh)

All runs: isolated state, primary temperature 0.7, three trials per variant,
seed recorded per trial, freeze check on.

| Stage | Profile | What | Incidents |
|---|---|---|---|
| `e2b-main` | q235 | `q235_div4`, four domains, flat / acl_hardened / agenticcyops, AP-2/3/4/14 | 792 |
| `e3b` | q235 | `q235_div4` CyberOps, agenticcyops minus P5, minus P4, llm_judge, symbolic_only, AP-2/3/4/14 | 264 |
| `e2b-others` | mid | `scout_div4`, `mistral_div3p`, `llama8b_div4`; CyberOps + finance; three configs; AP-2/3/4/14 | 1,188 |

The other eleven attack paths keep their v2.1 results (no defense decision
changed); the superseded v2.1 rows for AP-2/3/4/14 are archived under
`results/eval_attacks/_superseded_v2.1/` and excluded from `all_trials.csv`.

## Tables and reports

```
make paper-tables    # parse_logs -> statistical_tests -> generate_tables  -> results/paper_tables.md
make paper-reports   # per-run attack_report.pdf, results/revision_report.pdf, ASB asb_analytics.pdf
```

`exposed` in `all_trials.csv` is true when the trial has at least one
`injection_served` event (the model was shown the adversarial content). It
never changes the outcome or the ASR denominator; attempt rates are reported
both plain and *given exposure*.
