# Paper tables (scoring v3)

Generated from `results/eval_attacks/all_trials.csv` (10373 trials, groups: llama8b_div4, mistral_div3p, q235_div4, scout_div4). ASR = executed / measurable trials; attempt = executed + blocked; not-measurable and error trials excluded. CIs: Wilson (per-trial) and cluster bootstrap over variants (B = 10,000). Paired differences resample variants shared by both arms; p-values are Holm-corrected within each domain's family of attack paths.

## T1. Headline attack success by group and configuration

| Group | Config | N | ASR % [Wilson 95%] | Cluster bootstrap 95% | Attempt % | Attempt given exp. % | Exposed % | Block given attempt % | Δ vs AgenticCyOps |
|---|---|---|---|---|---|---|---|---|---|
| llama8b_div4 | Flat | 450 | 34.9 [30.6, 39.4] | [28.0, 42.0] | 34.9 | 15.7 | 67.4 | 0.0 | 29.8 pp [22.0, 37.6], p=0.000 |
| llama8b_div4 | ACL-Hardened | 450 | 32.7 [28.5, 37.1] | [25.8, 39.8] | 34.4 | 21.0 | 47.0 | 5.2 | 27.6 pp [19.8, 35.3], p=0.000 |
| llama8b_div4 | AgenticCyOps | 450 | 5.1 [3.4, 7.5] | [2.0, 8.7] | 40.0 | 41.9 | 47.0 | 87.2 | — |
| mistral_div3p | Flat | 450 | 23.3 [19.7, 27.5] | [17.3, 29.6] | 23.3 | 17.2 | 70.5 | 0.0 | 22.0 pp [16.0, 28.4], p=0.000 |
| mistral_div3p | ACL-Hardened | 450 | 20.7 [17.2, 24.6] | [14.9, 26.9] | 23.1 | 17.6 | 51.5 | 10.6 | 19.3 pp [13.6, 25.6], p=0.000 |
| mistral_div3p | AgenticCyOps | 450 | 1.3 [0.6, 2.9] | [0.0, 3.3] | 22.9 | 17.6 | 51.5 | 94.2 | — |
| q235_div4 | Flat | 900 | 31.0 [28.1, 34.1] | [26.1, 36.1] | 31.0 | 39.6 | 97.4 | 0.0 | 26.9 pp [22.1, 32.0], p=0.000 |
| q235_div4 | ACL-Hardened | 900 | 25.1 [22.4, 28.1] | [20.4, 29.9] | 28.7 | 37.1 | 87.0 | 12.4 | 21.0 pp [16.4, 25.8], p=0.000 |
| q235_div4 | AgenticCyOps | 900 | 4.1 [3.0, 5.6] | [2.2, 6.2] | 33.2 | 43.3 | 84.1 | 87.6 | — |
| scout_div4 | Flat | 450 | 35.8 [31.5, 40.3] | [28.9, 42.7] | 35.8 | 14.1 | 80.3 | 0.0 | 33.1 pp [26.0, 40.4], p=0.000 |
| scout_div4 | ACL-Hardened | 450 | 30.2 [26.2, 34.6] | [24.0, 36.7] | 33.3 | 18.2 | 58.3 | 9.3 | 27.6 pp [20.7, 34.4], p=0.000 |
| scout_div4 | AgenticCyOps | 450 | 2.7 [1.5, 4.6] | [0.7, 5.1] | 37.1 | 30.4 | 52.3 | 92.8 | — |

## T2a. Per attack path, q235_div4, all domains

| Attack path | Flat ASR % | ACL-Hardened ASR % | AgenticCyOps ASR % | Flat attempt % (all / exposed) | Flat − ACO (pp) | ACL − ACO (pp) |
|---|---|---|---|---|---|---|
| AP-1 Tool redirection | 16.7 [9.3, 28.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 16.7 / – | 16.7 (p_holm=0.059) | 0.0 (p_holm=1.000) |
| AP-2 Memory poisoning | 23.3 [14.4, 35.4] (n=60) | 25.0 [15.8, 37.2] (n=60) | 20.0 [11.8, 31.8] (n=60) | 23.3 / 23.3 | 3.3 (p_holm=1.000) | 5.0 (p_holm=1.000) |
| AP-3 Confused deputy | 0.0 [0.0, 6.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 0.0 / 0.0 | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-4 Cross-phase leak | 51.2 [40.7, 61.6] (n=84) | 14.3 [8.4, 23.3] (n=84) | 0.0 [0.0, 4.4] (n=84) | 51.2 / 53.1 | 51.2 (p_holm=0.000) | 14.3 (p_holm=0.286) |
| AP-5 Irreversible action | 18.3 [10.6, 29.9] (n=60) | 18.3 [10.6, 29.9] (n=60) | 0.0 [0.0, 6.0] (n=60) | 18.3 / – | 18.3 (p_holm=0.059) | 18.3 (p_holm=0.279) |
| AP-6 Replay | 3.3 [0.9, 11.4] (n=60) | 0.0 [0.0, 6.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 3.3 / – | 3.3 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-7 Action chain | 6.7 [2.6, 15.9] (n=60) | 5.0 [1.7, 13.7] (n=60) | 6.7 [2.6, 15.9] (n=60) | 6.7 / – | 0.0 (p_holm=1.000) | -1.7 (p_holm=1.000) |
| AP-8 Parameter manipulation | 18.3 [10.6, 29.9] (n=60) | 23.3 [14.4, 35.4] (n=60) | 5.0 [1.7, 13.7] (n=60) | 18.3 / – | 13.3 (p_holm=0.505) | 18.3 (p_holm=0.084) |
| AP-9 Handoff poisoning | 51.7 [39.3, 63.8] (n=60) | 36.7 [25.6, 49.3] (n=60) | 11.7 [5.8, 22.2] (n=60) | 51.7 / 51.7 | 40.0 (p_holm=0.032) | 25.0 (p_holm=0.409) |
| AP-10 Validator manipulation | 75.0 [62.8, 84.2] (n=60) | 75.0 [62.8, 84.2] (n=60) | 3.3 [0.9, 11.4] (n=60) | 75.0 / – | 71.7 (p_holm=0.000) | 71.7 (p_holm=0.000) |
| AP-11 Operational context | 20.0 [11.8, 31.8] (n=60) | 10.0 [4.7, 20.2] (n=60) | 1.7 [0.3, 8.9] (n=60) | 20.0 / – | 18.3 (p_holm=0.018) | 8.3 (p_holm=0.889) |
| AP-12 Concurrent actions | 13.3 [6.9, 24.2] (n=60) | 16.7 [9.3, 28.0] (n=60) | 3.3 [0.9, 11.4] (n=60) | 13.3 / – | 10.0 (p_holm=1.000) | 13.3 (p_holm=0.650) |
| AP-13 Adversarial memory | 100.0 [94.0, 100.0] (n=60) | 100.0 [94.0, 100.0] (n=60) | 5.0 [1.7, 13.7] (n=60) | 100.0 / 100.0 | 95.0 (p_holm=0.000) | 95.0 (p_holm=0.000) |
| AP-14 Read injection | 0.0 [0.0, 6.0] (n=60) | 0.0 [0.0, 6.0] (n=60) | 1.7 [0.3, 8.9] (n=60) | 0.0 / 0.0 | -1.7 (p_holm=1.000) | -1.7 (p_holm=1.000) |
| AP-15 Infrastructure integrity | 77.8 [61.9, 88.3] (n=36) | 77.8 [61.9, 88.3] (n=36) | 5.6 [1.5, 18.1] (n=36) | 77.8 / – | 72.2 (p_holm=0.000) | 72.2 (p_holm=0.000) |

## T2b. Per attack path, q235_div4, CyberOps

| Attack path | Flat ASR % | ACL-Hardened ASR % | AgenticCyOps ASR % | Flat attempt % (all / exposed) | Flat − ACO (pp) | ACL − ACO (pp) |
|---|---|---|---|---|---|---|
| AP-1 Tool redirection | 20.0 [7.0, 45.2] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 20.0 / – | 20.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-2 Memory poisoning | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 / 0.0 | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-3 Confused deputy | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 / 0.0 | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-4 Cross-phase leak | 76.2 [54.9, 89.4] (n=21) | 14.3 [5.0, 34.6] (n=21) | 0.0 [0.0, 15.5] (n=21) | 76.2 / 76.2 | 76.2 (p_holm=0.000) | 14.3 (p_holm=1.000) |
| AP-5 Irreversible action | 6.7 [1.2, 29.8] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 6.7 / – | 6.7 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-6 Replay | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 13.3 / – | 13.3 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-7 Action chain | 20.0 [7.0, 45.2] (n=15) | 6.7 [1.2, 29.8] (n=15) | 13.3 [3.7, 37.9] (n=15) | 20.0 / – | 6.7 (p_holm=1.000) | -6.7 (p_holm=1.000) |
| AP-8 Parameter manipulation | 33.3 [15.2, 58.3] (n=15) | 46.7 [24.8, 69.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 33.3 / – | 33.3 (p_holm=1.000) | 46.7 (p_holm=0.228) |
| AP-9 Handoff poisoning | 53.3 [30.1, 75.2] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 53.3 / 53.3 | 53.3 (p_holm=0.209) | 0.0 (p_holm=1.000) |
| AP-10 Validator manipulation | 100.0 [79.6, 100.0] (n=15) | 100.0 [79.6, 100.0] (n=15) | 13.3 [3.7, 37.9] (n=15) | 100.0 / – | 86.7 (p_holm=0.000) | 86.7 (p_holm=0.000) |
| AP-11 Operational context | 20.0 [7.0, 45.2] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 20.0 / – | 20.0 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-12 Concurrent actions | 26.7 [10.9, 51.9] (n=15) | 13.3 [3.7, 37.9] (n=15) | 0.0 [0.0, 20.4] (n=15) | 26.7 / – | 26.7 (p_holm=1.000) | 13.3 (p_holm=1.000) |
| AP-13 Adversarial memory | 100.0 [79.6, 100.0] (n=15) | 100.0 [79.6, 100.0] (n=15) | 20.0 [7.0, 45.2] (n=15) | 100.0 / 100.0 | 80.0 (p_holm=0.005) | 80.0 (p_holm=0.005) |
| AP-14 Read injection | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 [0.0, 20.4] (n=15) | 0.0 / 0.0 | 0.0 (p_holm=1.000) | 0.0 (p_holm=1.000) |
| AP-15 Infrastructure integrity | 77.8 [45.3, 93.7] (n=9) | 77.8 [45.3, 93.7] (n=9) | 22.2 [6.3, 54.7] (n=9) | 77.8 / – | 55.6 (p_holm=0.000) | 55.6 (p_holm=0.000) |

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
| scout_div4 | ACL-Hardened | 75 | 70.7 [59.6, 79.8] | 52.0 [40.9, 62.9] | 1.79 | 51.0 / 64.5 | 21316 / 0 |
| scout_div4 | AgenticCyOps | 75 | 62.7 [51.4, 72.7] | 94.7 [87.1, 97.9] | 3.44 | 94.5 / 150.0 | 12162 / 8651 |
| scout_div4 | Flat | 75 | 84.0 [74.1, 90.6] | 0.0 [0.0, 4.9] | 0.00 | 51.9 / 64.8 | 21685 / 0 |

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
| AgenticCyOps | 225 | 4.0 [2.1, 7.4] | 60 | 80.0 [68.2, 88.2] |
| agenticcyops -P1 | 204 | 5.4 [3.0, 9.4] | 60 | 76.7 [64.6, 85.6] |
| agenticcyops -P2 | 204 | 9.8 [6.4, 14.7] | 60 | 73.3 [61.0, 82.9] |
| agenticcyops -P3 | 204 | 19.1 [14.3, 25.1] | 60 | 65.0 [52.4, 75.8] |
| agenticcyops -P4 | 225 | 8.9 [5.8, 13.3] | 60 | 83.3 [72.0, 90.7] |
| agenticcyops -P5 | 225 | 6.2 [3.7, 10.2] | 60 | 75.0 [62.8, 84.2] |
| LLM-judge only | 225 | 24.4 [19.3, 30.5] | 60 | 81.7 [70.1, 89.4] |
| Symbolic only (no L6) | 225 | 1.3 [0.5, 3.8] | 60 | 96.7 [88.6, 99.1] |

## T5. Which layer blocked the attacks (AgenticCyOps, q235_div4)

| Layer | Blocked trials | Share % |
|---|---|---|
| P3_llm_consensus_reject | 70 | 26.7 |
| P2_target_not_in_evidence | 60 | 22.9 |
| P4_schema_violation | 48 | 18.3 |
| P2_parameter_rule_violation | 20 | 7.6 |
| P5_access_control | 12 | 4.6 |
| P5_broad_query_block | 12 | 4.6 |
| P3_handoff_validation | 8 | 3.1 |
| P2_critical_asset | 5 | 1.9 |
| P3_operational_context | 5 | 1.9 |
| P1_config_integrity_violation | 4 | 1.5 |
| P4_metadata_invalid | 3 | 1.1 |
| P4_similarity_reject | 3 | 1.1 |
| P4_write_replay | 3 | 1.1 |
| P2_wildcard_parameter | 3 | 1.1 |
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
| q235_div4_frozen_full | context_manipulation | acl_hardened | 60 | 43.33 | 43.33 |
| q235_div4_frozen_full | context_manipulation | agenticcyops | 60 | 41.67 | 0.0 |
| q235_div4_frozen_full | context_manipulation | flat | 60 | 38.33 | 38.33 |
| q235_div4_frozen_full | escape_characters | acl_hardened | 120 | 11.67 | 11.67 |
| q235_div4_frozen_full | escape_characters | agenticcyops | 120 | 10.83 | 0.0 |
| q235_div4_frozen_full | escape_characters | flat | 120 | 10.83 | 10.83 |
| q235_div4_frozen_full | fake_completion | acl_hardened | 120 | 37.5 | 37.5 |
| q235_div4_frozen_full | fake_completion | agenticcyops | 120 | 40.0 | 0.0 |
| q235_div4_frozen_full | fake_completion | flat | 120 | 35.0 | 35.0 |
| q235_div4_frozen_full | naive | acl_hardened | 180 | 34.44 | 34.44 |
| q235_div4_frozen_full | naive | agenticcyops | 180 | 38.89 | 0.0 |
| q235_div4_frozen_full | naive | flat | 180 | 33.89 | 33.89 |
| q235_div4_frozen_full | trigger_phrase | acl_hardened | 30 | 20.0 | 20.0 |
| q235_div4_frozen_full | trigger_phrase | agenticcyops | 30 | 23.33 | 0.0 |
| q235_div4_frozen_full | trigger_phrase | flat | 30 | 26.67 | 26.67 |
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
| llama8b_div4 | ACL-Hardened | 450 | 15532 | 0 | 6.8 / 19.3 |
| llama8b_div4 | AgenticCyOps | 450 | 7094 | 7542 | 32.4 / 132.4 |
| llama8b_div4 | Flat | 450 | 15599 | 0 | 6.7 / 22.8 |
| mistral_div3p | ACL-Hardened | 450 | 15429 | 0 | 18.9 / 55.0 |
| mistral_div3p | AgenticCyOps | 450 | 9327 | 2150 | 35.3 / 81.6 |
| mistral_div3p | Flat | 450 | 15629 | 0 | 19.7 / 53.7 |
| q235_div4 | ACL-Hardened | 900 | 15184 | 0 | 36.1 / 76.7 |
| q235_div4 | AgenticCyOps | 900 | 8647 | 8694 | 79.4 / 165.2 |
| q235_div4 | Flat | 900 | 16419 | 0 | 37.3 / 81.5 |
| q235_div4 | LLM-judge only | 226 | 10728 | 27857 | 181.2 / 251.1 |
| q235_div4 | Symbolic only (no L6) | 450 | 9529 | 0 | 41.1 / 80.0 |
| scout_div4 | ACL-Hardened | 450 | 19471 | 0 | 48.0 / 66.7 |
| scout_div4 | AgenticCyOps | 450 | 11279 | 6104 | 76.2 / 134.4 |
| scout_div4 | Flat | 450 | 19738 | 0 | 48.3 / 65.7 |

## T8. Run provenance

| Group | Domain | Config | Suffix | Git | Freeze tag | Primary | Quant | Panel | T | State | vLLM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llama8b_div4 | cyberops | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | cyberops | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-3.1-8B-Instruct | bf16 | div4 | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | cyberops | flat |  | 03daccdacb | defense-freeze-v2.4-1-g03daccd | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-3.1-8B-Instruct | bf16 | div4 | 0.7 | isolated | 0.21.0 |
| llama8b_div4 | finance | flat |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-3.1-8B-Instruct | bf16 |  | 0.7 | isolated | 0.21.0 |
| mistral_div3p | cyberops | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | cyberops | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 | mistral_div3p | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | cyberops | flat |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 | mistral_div3p | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| mistral_div3p | finance | flat |  | 5435e156e1 | defense-freeze-v2.2 | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | acl_hardened |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P1 | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P2 | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P3 | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P4 | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | agenticcyops | _disabled_P5 | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | flat |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | llm_judge |  | 5435e156e1 | defense-freeze-v2.2 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | cyberops | symbolic_only |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | acl_hardened |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | agenticcyops |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | flat |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | llm_judge |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | finance | symbolic_only |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | acl_hardened |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | agenticcyops |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | flat |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | llm_judge |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | healthcare | symbolic_only |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | acl_hardened |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | agenticcyops |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | flat |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | llm_judge |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4 | legal | symbolic_only |  | 6c299d9c71 | defense-freeze-v2.4-4-g6c299d9 | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4_persistent | cyberops | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4_persistent | finance | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4_persistent | healthcare | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| q235_div4_persistent | legal | agenticcyops |  | c66c04b66a | defense-freeze-v2-5-gc66c04b | Qwen/Qwen3-235B-A22B-Instruct-2507 | bf16 | div4 | 0.7 | persistent | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | cyberops | flat |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | acl_hardened |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | agenticcyops |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 | div4 | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |
| scout_div4 | finance | flat |  | 5435e156e1 | defense-freeze-v2.2 | meta-llama/Llama-4-Scout-17B-16E-Instruct | bf16 |  | 0.7 | isolated | 0.19.1rc1.dev117+g3352bf8b0 |

## T9. Injection channels (pooled over primaries)

Exposed % = share of scored trials with an injection_served event; attempt | exposed % is the attempt rate among exposed trials.

| Channel | Config | Variants | N | Exposed % | Attempt % | Attempt given exp. % | ASR % [95%] |
|---|---|---|---|---|---|---|---|
| Alert text | ACL-Hardened | 170 | 1176 | 100.0 | 28.3 | 80.8 | 23.8 [21.5, 26.3] |
| Alert text | AgenticCyOps | 170 | 1176 | 100.0 | 34.3 | 80.8 | 2.2 [1.5, 3.2] |
| Alert text | Flat | 170 | 1176 | 100.0 | 28.9 | 80.1 | 28.9 [26.4, 31.6] |
| Handoff | ACL-Hardened | 30 | 270 | 100.0 | 43.3 | 41.7 | 38.9 [33.3, 44.8] |
| Handoff | AgenticCyOps | 30 | 270 | 100.0 | 43.0 | 66.7 | 2.6 [1.3, 5.3] |
| Handoff | Flat | 30 | 270 | 100.0 | 44.4 | 51.7 | 44.4 [38.6, 50.4] |
| Memory | ACL-Hardened | 35 | 285 | 45.3 | 1.1 | 2.3 | 1.1 [0.4, 3.0] |
| Memory | AgenticCyOps | 35 | 285 | 54.7 | 8.4 | 15.4 | 8.4 [5.7, 12.2] |
| Memory | Flat | 35 | 285 | 86.3 | 9.8 | 11.4 | 9.8 [6.9, 13.8] |
| Proposal justification | ACL-Hardened | 32 | 240 | – | 85.4 | – | 85.4 [80.4, 89.3] |
| Proposal justification | AgenticCyOps | 32 | 240 | – | 82.1 | – | 5.0 [2.9, 8.5] |
| Proposal justification | Flat | 32 | 240 | – | 85.4 | – | 85.4 [80.4, 89.3] |
| Tool response | ACL-Hardened | 33 | 279 | 70.3 | 3.2 | 4.6 | 3.2 [1.7, 6.0] |
| Tool response | AgenticCyOps | 33 | 279 | 53.8 | 3.2 | 6.0 | 3.2 [1.7, 6.0] |
| Tool response | Flat | 33 | 279 | 71.7 | 3.2 | 4.5 | 3.2 [1.7, 6.0] |

## T9b. Injection channels, q235_div4

| Channel | Config | Variants | N | Exposed % | Attempt % | Attempt given exp. % | ASR % [95%] |
|---|---|---|---|---|---|---|---|
| Alert text | ACL-Hardened | 170 | 510 | 100.0 | 27.5 | 75.0 | 21.8 [18.4, 25.5] |
| Alert text | AgenticCyOps | 170 | 510 | 100.0 | 32.4 | 75.0 | 3.1 [1.9, 5.0] |
| Alert text | Flat | 170 | 510 | 100.0 | 26.7 | 74.2 | 26.7 [23.0, 30.7] |
| Handoff | ACL-Hardened | 30 | 90 | 100.0 | 40.0 | 41.7 | 36.7 [27.4, 47.0] |
| Handoff | AgenticCyOps | 30 | 90 | 100.0 | 60.0 | 66.7 | 7.8 [3.8, 15.2] |
| Handoff | Flat | 30 | 90 | 100.0 | 46.7 | 51.7 | 46.7 [36.7, 56.9] |
| Memory | ACL-Hardened | 35 | 105 | 62.9 | 0.0 | 0.0 | 0.0 [0.0, 3.5] |
| Memory | AgenticCyOps | 35 | 105 | 62.9 | 1.0 | 1.5 | 1.0 [0.2, 5.2] |
| Memory | Flat | 35 | 105 | 97.1 | 18.1 | 18.6 | 18.1 [11.9, 26.5] |
| Proposal justification | ACL-Hardened | 32 | 96 | – | 76.0 | – | 76.0 [66.6, 83.5] |
| Proposal justification | AgenticCyOps | 32 | 96 | – | 72.9 | – | 4.2 [1.6, 10.2] |
| Proposal justification | Flat | 32 | 96 | – | 76.0 | – | 76.0 [66.6, 83.5] |
| Tool response | ACL-Hardened | 33 | 99 | 88.9 | 9.1 | 10.2 | 9.1 [4.9, 16.4] |
| Tool response | AgenticCyOps | 33 | 99 | 77.8 | 9.1 | 11.7 | 9.1 [4.9, 16.4] |
| Tool response | Flat | 33 | 99 | 92.9 | 9.1 | 9.8 | 9.1 [4.9, 16.4] |

## T10. P5 evidence (AP-4 + AP-14, q235_div4, CyberOps)

| Arm (AP-4 + AP-14, CyberOps) | N | ASR % [95%] | Block given attempt % |
|---|---|---|---|
| Flat | 36 | 44.4 [29.5, 60.4] | 0.0 |
| ACL-Hardened | 36 | 8.3 [2.9, 21.8] | 50.0 |
| Full (AgenticCyOps) | 36 | 0.0 [0.0, 9.6] | 100.0 |
| Full minus P5 | 36 | 19.4 [9.8, 35.0] | 58.8 |

First interception under Full (AP-4 + AP-14, CyberOps):
- P5_access_control: 3
- P5_broad_query_block: 3

P5 benign cost (AgenticCyOps benign incidents):

| Domain | Benign incidents | Incidents w/ a P5 read denial | Incidents w/ a P5 redaction |
|---|---|---|---|
| cyberops | 60 | 0 | 0 |
| finance | 15 | 3 | 0 |
| healthcare | 15 | 0 | 0 |
| legal | 15 | 0 | 0 |

## T11. Benign tool-proposal denial rate (q235_div4)

One definition, shared with Fig. 3(b) via `analysis/benign_cost.py`: denied tool proposals / all tool proposals, matched on `call_id`, isolated benign runs. The numerator is a subset of the denominator by construction, so this does not mix tool denials with memory-op denials the way a per-trial `collateral_denials` count does.

| Domain | Flat denied % | ACL-Hardened denied % | AgenticCyOps denied % |
|---|---|---|---|
| cyberops | 0.0 (0/1163) | 54.8 (640/1168) | 10.1 (88/873) |
| finance | 0.0 (0/245) | 18.0 (41/228) | 15.9 (28/176) |
| healthcare | 0.0 (0/228) | 40.7 (94/231) | 27.1 (56/207) |
| legal | 0.0 (0/190) | 11.8 (22/186) | 23.2 (42/181) |
| **all domains** | 0.0 (0/1826) | 44.0 (797/1813) | 14.9 (214/1437) |

## T12. Benign denials by principle and check (q235_div4, AgenticCyOps)

E14: every benign denial attributed to the check that made it, with the tools or stores it denied most. The LLM panel is separated from the deterministic P3 layers; the gate event that merely surfaces a panel rejection is not counted twice.

| Domain | Principle | Check | Denials | Top denied targets |
|---|---|---|---|---|
| cyberops | P2 | P2 capability scoping | 64 | T8_iam_pam (42), T9_firewall (11), T11_epp_av (6) |
| cyberops | P3 (panel) | P3 llm consensus reject | 24 | P3_L6 (24) |
| cyberops | P4 | P4 metadata invalid | 6 | M1 (6) |
| cyberops | P4 | P4 schema violation | 3 | M6 (3) |
| finance | P3 (panel) | P3 llm consensus reject | 17 | P3_L6 (17) |
| finance | P4 | P4 schema violation | 15 | FM4 (15) |
| finance | P2 | P2 capability scoping | 11 | F10_wire_recall (6), F5_graph_analysis (3), F8_account_freeze (2) |
| finance | P5 | P5 broad query block | 3 | FM1 (3) |
| healthcare | P3 (panel) | P3 llm consensus reject | 53 | P3_L6 (53) |
| healthcare | P4 | P4 similarity reject | 36 | HM5 (12), HM7 (12), HM6 (6) |
| healthcare | P4 | P4 schema violation | 15 | HM1 (15) |
| healthcare | P2 | P2 capability scoping | 3 | H3_lab_results (3) |
| legal | P3 (panel) | P3 llm consensus reject | 36 | P3_L6 (36) |
| legal | P4 | P4 schema violation | 15 | LM1 (15) |
| legal | P4 | P4 similarity reject | 15 | LM8 (9), LM6 (3), LM3 (3) |
| legal | P2 | P2 capability scoping | 6 | L10_payment_processing (6) |
