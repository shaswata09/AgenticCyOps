# Paper tables (scoring v3)

Generated from `/storage/data/AgenticCyOps_Private/results/eval_attacks/all_trials.csv` (9788 trials, groups: llama8b_div4, mistral_div3p, q235_div4, scout_div4). ASR = executed / measurable trials; attempt = executed + blocked; not-measurable and error trials excluded. CIs: Wilson (per-trial) and cluster bootstrap over variants (B = 10,000). Paired differences resample variants shared by both arms; p-values are Holm-corrected within each domain's family of attack paths.

## T1. Headline attack success by group and configuration

| Group | Config | N | ASR % [Wilson 95%] | Cluster bootstrap 95% | Attempt % | Block given attempt % | Δ vs AgenticCyOps |
|---|---|---|---|---|---|---|---|
| llama8b_div4 | Flat | 378 | 37.8 [33.1, 42.8] | [29.9, 45.8] | 37.8 | 0.0 | 35.4 pp [27.5, 43.4], p=0.000 |
| llama8b_div4 | ACL-Hardened | 378 | 37.0 [32.3, 42.0] | [29.1, 45.0] | 37.6 | 1.4 | 34.7 pp [26.7, 42.6], p=0.000 |
| llama8b_div4 | AgenticCyOps | 378 | 2.4 [1.3, 4.5] | [0.3, 5.0] | 40.7 | 94.2 | — |
| mistral_div3p | Flat | 378 | 23.5 [19.6, 28.1] | [16.9, 30.7] | 23.5 | 0.0 | 22.0 pp [15.3, 29.1], p=0.000 |
| mistral_div3p | ACL-Hardened | 378 | 23.0 [19.1, 27.5] | [16.4, 30.2] | 24.3 | 5.4 | 21.4 pp [14.8, 28.6], p=0.000 |
| mistral_div3p | AgenticCyOps | 378 | 1.6 [0.7, 3.4] | [0.0, 4.0] | 24.1 | 93.4 | — |
| q235_div4 | Flat | 756 | 29.8 [26.6, 33.1] | [24.6, 35.2] | 29.8 | 0.0 | 27.1 pp [21.8, 32.4], p=0.000 |
| q235_div4 | ACL-Hardened | 756 | 26.7 [23.7, 30.0] | [21.6, 32.1] | 29.5 | 9.4 | 24.1 pp [19.1, 29.2], p=0.000 |
| q235_div4 | AgenticCyOps | 756 | 2.6 [1.7, 4.0] | [1.1, 4.5] | 34.8 | 92.4 | — |
| scout_div4 | Flat | 364 | 37.9 [33.1, 43.0] | [30.3, 45.7] | 37.9 | 0.0 | 37.1 pp [29.2, 44.9], p=0.000 |
| scout_div4 | ACL-Hardened | 363 | 34.2 [29.5, 39.2] | [26.9, 41.5] | 36.4 | 6.1 | 33.4 pp [26.2, 40.8], p=0.000 |
| scout_div4 | AgenticCyOps | 378 | 0.8 [0.3, 2.3] | [0.0, 2.4] | 38.6 | 98.0 | — |

## T2a. Per attack path, q235_div4, all domains

| Attack path | Flat ASR % | ACL-Hardened ASR % | AgenticCyOps ASR % | Flat − ACO (pp) | ACL − ACO (pp) |
|---|---|---|---|---|---|

## T2b. Per attack path, q235_div4, CyberOps

| Attack path | Flat ASR % | ACL-Hardened ASR % | AgenticCyOps ASR % | Flat − ACO (pp) | ACL − ACO (pp) |
|---|---|---|---|---|---|
| AP-1 Tool redirection | 20.0 [7.0, 45.2] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 20.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-2 Memory poisoning | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-3 Confused deputy | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-5 Irreversible action | 6.7 [1.2, 29.8] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 6.7 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-6 Replay | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 13.3 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-7 Action chain | 20.0 [7.0, 45.2] (n=15) | 6.7 [1.2, 29.8] (n=15) | 13.3 [3.7, 37.9] (n=15) | 6.7 (p_holm=1.000) | -6.7 (p_holm=1.000) |
| AP-8 Parameter manipulation | 33.3 [15.2, 58.3] (n=15) | 46.7 [24.8, 69.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 33.3 (p_holm=1.000) | 46.7 (p_holm=0.190) |
| AP-9 Handoff poisoning | 46.7 [24.8, 69.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 46.7 (p_holm=0.190) | 0.0 (p_holm=1.000) |
| AP-10 Validator manipulation | 100.0 [79.6, 100.0] (n=15) | 100.0 [79.6, 100.0] (n=15) | 13.3 [3.7, 37.9] (n=15) | 86.7 (p_holm=0.000) | 86.7 (p_holm=0.000) |
| AP-11 Operational context | 20.0 [7.0, 45.2] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 20.0 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-12 Concurrent actions | 26.7 [10.9, 51.9] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 26.7 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-13 Adversarial memory | 100.0 [79.6, 100.0] (n=15) | 100.0 [79.6, 100.0] (n=15) | 20.0 [7.0, 45.2] (n=15) | 80.0 (p_holm=0.004) | 80.0 (p_holm=0.004) |
| AP-15 Infrastructure integrity | 77.8 [45.3, 93.7] (n=9) | 77.8 [45.3, 93.7] (n=9) | 22.2 [6.3, 54.7] (n=9) | 55.6 (p_holm=0.000) | 55.6 (p_holm=0.000) |

## T3. Benign utility (E1)

| Group | Config | N | Task completed % [95%] | Any denial % [95%] | Denials / incident | Latency s median / p95 | Tokens primary / validator |
|---|---|---|---|---|---|---|---|
| llama8b_div4 | ACL-Hardened | 75 | 100.0 [95.1, 100.0] | 6.7 [2.9, 14.7] | 0.21 | 8.2 / 22.9 | 17326 / 0 |
| llama8b_div4 | AgenticCyOps | 75 | 98.7 [92.8, 99.8] | 60.0 [48.7, 70.3] | 1.61 | 36.2 / 112.9 | 8360 / 8491 |
| llama8b_div4 | Flat | 75 | 100.0 [95.1, 100.0] | 0.0 [0.0, 4.9] | 0.00 | 8.1 / 58.5 | 17391 / 0 |
| mistral_div3p | ACL-Hardened | 75 | 86.7 [77.2, 92.6] | 24.0 [15.8, 34.8] | 0.71 | 32.8 / 61.2 | 18389 / 0 |
| mistral_div3p | AgenticCyOps | 75 | 78.7 [68.1, 86.4] | 62.7 [51.4, 72.7] | 1.43 | 53.4 / 103.6 | 11821 / 3475 |
| mistral_div3p | Flat | 75 | 80.0 [69.6, 87.5] | 0.0 [0.0, 4.9] | 0.00 | 32.2 / 55.1 | 18758 / 0 |
| q235_div4 | ACL-Hardened | 105 | 58.1 [48.5, 67.1] | 94.3 [88.1, 97.4] | 7.59 | 34.9 / 57.5 | 18376 / 0 |
| q235_div4 | AgenticCyOps | 105 | 97.1 [91.9, 99.0] | 88.6 [81.1, 93.3] | 3.40 | 112.7 / 172.5 | 11928 / 15895 |
| q235_div4 | Flat | 105 | 100.0 [96.5, 100.0] | 0.0 [0.0, 3.5] | 0.00 | 36.2 / 67.5 | 19768 / 0 |
| q235_div4 | LLM-judge only | 60 | 95.0 [86.3, 98.3] | 81.7 [70.1, 89.4] | 1.82 | 167.3 / 194.8 | 11937 / 26321 |
| q235_div4 | Symbolic only (no L6) | 60 | 25.0 [15.8, 37.2] | 96.7 [88.6, 99.1] | 7.42 | 55.1 / 72.3 | 12184 / 0 |
| scout_div4 | ACL-Hardened | 73 | 71.2 [60.0, 80.3] | 50.7 [39.5, 61.8] | 1.78 | 51.7 / 64.5 | 21335 / 0 |
| scout_div4 | AgenticCyOps | 74 | 62.2 [50.8, 72.4] | 94.6 [86.9, 97.9] | 3.41 | 94.5 / 150.0 | 12147 / 8572 |
| scout_div4 | Flat | 72 | 83.3 [73.1, 90.2] | 0.0 [0.0, 5.1] | 0.00 | 52.4 / 64.8 | 21679 / 0 |

## T3b. Persistent-state sequence (E1b), AgenticCyOps, q235_div4

Benign scenarios run after 30 attack incidents with all defense state kept, against the same scenarios under per-trial isolation (first trial of E1).

| Domain | State mode | N | Any denial % [95%] | Denials / incident | Task completed % [95%] | Any denial %: first half / second half of sequence |
|---|---|---|---|---|---|---|
| cyberops | isolated | 20 | 70.0 [48.1, 85.5] | 1.45 | 90.0 [69.9, 97.2] | 70 / 70 |
| cyberops | persistent | 20 | 100.0 [83.9, 100.0] | 7.35 | 5.0 [0.9, 23.6] | 100 / 100 |
| healthcare | isolated | 5 | 100.0 [56.6, 100.0] | 7.60 | 100.0 [56.6, 100.0] | 100 / 100 |
| healthcare | persistent | 5 | 100.0 [56.6, 100.0] | 11.40 | 40.0 [11.8, 76.9] | 100 / 100 |
| finance | isolated | 5 | 100.0 [56.6, 100.0] | 4.20 | 100.0 [56.6, 100.0] | 100 / 100 |
| finance | persistent | 5 | 100.0 [56.6, 100.0] | 8.20 | 40.0 [11.8, 76.9] | 100 / 100 |
| legal | isolated | 5 | 100.0 [56.6, 100.0] | 4.80 | 100.0 [56.6, 100.0] | 100 / 100 |
| legal | persistent | 5 | 100.0 [56.6, 100.0] | 8.20 | 40.0 [11.8, 76.9] | 100 / 100 |

## T4. Ablations (E3), q235_div4

| Ablation config | Attack trials | ASR % [95%] | Benign trials | Benign any-denial % [95%] |
|---|---|---|---|---|
| AgenticCyOps | 756 | 2.6 [1.7, 4.1] | 105 | 88.6 [81.1, 93.3] |
| agenticcyops -P1 | 189 | 5.8 [3.3, 10.1] | 60 | 76.7 [64.6, 85.6] |
| agenticcyops -P2 | 189 | 10.6 [7.0, 15.8] | 60 | 73.3 [61.0, 82.9] |
| agenticcyops -P3 | 189 | 18.0 [13.2, 24.1] | 60 | 65.0 [52.4, 75.8] |
| agenticcyops -P4 | 189 | 10.6 [7.0, 15.8] | 60 | 83.3 [72.0, 90.7] |
| agenticcyops -P5 | 189 | 3.7 [1.8, 7.4] | 60 | 75.0 [62.8, 84.2] |
| LLM-judge only | 189 | 22.2 [16.9, 28.7] | 60 | 81.7 [70.1, 89.4] |
| Symbolic only (no L6) | 189 | 1.6 [0.5, 4.6] | 60 | 96.7 [88.6, 99.1] |

## T5. Which layer blocked the attacks (AgenticCyOps, q235_div4)

| Layer | Blocked trials | Share % |
|---|---|---|
| P2_target_not_in_evidence | 72 | 29.6 |
| P3_llm_consensus_reject | 66 | 27.2 |
| P4_schema_violation | 48 | 19.8 |
| P2_parameter_rule_violation | 20 | 8.2 |
| P2_critical_asset | 5 | 2.1 |
| P3_handoff_validation | 5 | 2.1 |
| P3_operational_context | 5 | 2.1 |
| P1_config_integrity_violation | 4 | 1.6 |
| P4_metadata_invalid | 3 | 1.2 |
| P4_similarity_reject | 3 | 1.2 |
| P4_write_replay | 3 | 1.2 |
| P2_wildcard_parameter | 3 | 1.2 |
| P3_replay_detection | 2 | 0.8 |
| P1_response_integrity | 2 | 0.8 |
| P3_bulk_action | 1 | 0.4 |
| P3_execution_verification | 1 | 0.4 |

## T6. ASB paired panel replay (E6)

| Run (group[_panel]) | Attack subtype | Config | N | LLM ASR % | Defended ASR % |
|---|---|---|---|---|---|
| q235_div4_div3 | context_manipulation | agenticcyops | 150 | 39.33 | 0.0 |
| q235_div4_div3 | escape_characters | agenticcyops | 300 | 13.67 | 0.0 |
| q235_div4_div3 | fake_completion | agenticcyops | 300 | 39.67 | 0.0 |
| q235_div4_div3 | naive | agenticcyops | 450 | 35.33 | 1.56 |
| q235_div4_div3 | trigger_phrase | agenticcyops | 75 | 36.0 | 6.67 |
| q235_div4_div4 | context_manipulation | agenticcyops | 150 | 39.33 | 0.0 |
| q235_div4_div4 | escape_characters | agenticcyops | 300 | 13.67 | 0.0 |
| q235_div4_div4 | fake_completion | agenticcyops | 300 | 39.67 | 0.0 |
| q235_div4_div4 | naive | agenticcyops | 450 | 35.33 | 0.0 |
| q235_div4_div4 | trigger_phrase | agenticcyops | 75 | 36.0 | 0.0 |
| q235_div4_drift | context_manipulation | agenticcyops | 10 | 30.0 | 0.0 |
| q235_div4_drift | context_manipulation | flat | 10 | 30.0 | 30.0 |
| q235_div4_drift | escape_characters | agenticcyops | 10 | 0.0 | 0.0 |
| q235_div4_drift | escape_characters | flat | 10 | 20.0 | 20.0 |
| q235_div4_drift | fake_completion | agenticcyops | 10 | 30.0 | 0.0 |
| q235_div4_drift | fake_completion | flat | 10 | 40.0 | 40.0 |
| q235_div4_drift | naive | agenticcyops | 15 | 26.67 | 6.67 |
| q235_div4_drift | naive | flat | 15 | 26.67 | 26.67 |
| q235_div4_drift | trigger_phrase | agenticcyops | 5 | 20.0 | 0.0 |
| q235_div4_drift | trigger_phrase | flat | 5 | 20.0 | 20.0 |
| q235_div4_lin3 | context_manipulation | agenticcyops | 150 | 39.33 | 0.0 |
| q235_div4_lin3 | escape_characters | agenticcyops | 300 | 13.67 | 7.33 |
| q235_div4_lin3 | fake_completion | agenticcyops | 300 | 39.67 | 8.67 |
| q235_div4_lin3 | naive | agenticcyops | 450 | 35.33 | 11.11 |
| q235_div4_lin3 | trigger_phrase | agenticcyops | 75 | 36.0 | 13.33 |
| q235_div4_single | context_manipulation | agenticcyops | 150 | 39.33 | 0.0 |
| q235_div4_single | escape_characters | agenticcyops | 300 | 13.67 | 1.0 |
| q235_div4_single | fake_completion | agenticcyops | 300 | 39.67 | 2.33 |
| q235_div4_single | naive | agenticcyops | 450 | 35.33 | 5.78 |
| q235_div4_single | trigger_phrase | agenticcyops | 75 | 36.0 | 6.67 |

## T7. Cost

| Group | Config | N | Primary tokens / trial | Validator tokens / trial | Latency s median / p95 |
|---|---|---|---|---|---|
| llama8b_div4 | ACL-Hardened | 378 | 15620 | 0 | 6.8 / 21.5 |
| llama8b_div4 | AgenticCyOps | 378 | 7120 | 8303 | 34.1 / 153.0 |
| llama8b_div4 | Flat | 378 | 15679 | 0 | 6.7 / 24.8 |
| mistral_div3p | ACL-Hardened | 378 | 15533 | 0 | 18.4 / 53.5 |
| mistral_div3p | AgenticCyOps | 378 | 9353 | 2288 | 36.1 / 82.5 |
| mistral_div3p | Flat | 378 | 15685 | 0 | 19.7 / 49.2 |
| q235_div4 | ACL-Hardened | 756 | 14976 | 0 | 36.3 / 76.2 |
| q235_div4 | AgenticCyOps | 756 | 8644 | 9932 | 88.5 / 179.3 |
| q235_div4 | Flat | 756 | 16195 | 0 | 37.3 / 81.4 |
| q235_div4 | LLM-judge only | 189 | 10759 | 29289 | 190.5 / 253.5 |
| q235_div4 | Symbolic only (no L6) | 189 | 11178 | 0 | 51.9 / 73.8 |
| scout_div4 | ACL-Hardened | 363 | 19464 | 0 | 48.2 / 68.4 |
| scout_div4 | AgenticCyOps | 378 | 11328 | 6070 | 77.4 / 135.9 |
| scout_div4 | Flat | 364 | 19691 | 0 | 48.3 / 69.0 |

## T8. Run provenance

| Group | Domain | Config | Suffix | Git | Freeze tag | Primary | Quant | Panel | T | State | vLLM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llama8b_div4 | cyberops | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | cyberops | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 | div4 | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | cyberops | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 | div4 | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| mistral_div3p | cyberops | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | cyberops | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 | mistral_div3p | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | cyberops | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 | mistral_div3p | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | acl_hardened |  | d81550cdb4 | defense-freeze-v2 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops |  | be6b4f1299 | defense-freeze-v2-1-gbe6b4f1 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P1 | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P2 | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P3 | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P4 | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P5 | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | flat |  | d81550cdb4 | defense-freeze-v2 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | llm_judge |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | symbolic_only |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | acl_hardened |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | flat |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | acl_hardened |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | flat |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | acl_hardened |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | flat |  | 8e94f23700 | defense-freeze-v2-4-g8e94f23 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | acl_hardened |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | agenticcyops |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | flat |  | 98dde989a4 | defense-freeze-v2-8-g98dde98 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
