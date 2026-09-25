# Judgment boundary for gpt-oss-120b and Llama-3.1-8B (live at v2.9, CyberOps)

JUDGEONLY and FULL: direct outcome under Local4 (live local2 value in `live_local2`).

## gpt-oss-120b

| Config | ASR % [95% CI] | Attempt % | Block|att. % | Judged % | Benign denied % |
|---|---|---|---|---|---|
| FLAT | 21.8 [13.3, 31.1] | 21.8 | 0.0 | 0 | 0.0 |
| ACL | 17.8 [9.8, 27.1] | 19.1 | 7.0 | 0 | 0.0 |
| JUDGEONLY | 22.7 [13.8, 32.0] | 24.4 | 7.3 | 100.0 | 0.0 |
| NOJUDGE | 1.3 [0.0, 4.0] | 18.7 | 92.9 | 0 | 33.3 |
| FULL | 6.7 [1.3, 12.0] | 18.7 | 64.3 | 24.6 | 0.0 |

## Llama-3.1-8B

| Config | ASR % [95% CI] | Attempt % | Block|att. % | Judged % | Benign denied % |
|---|---|---|---|---|---|
| FLAT | 34.2 [24.0, 44.4] | 34.2 | 0.0 | 0 | 0.0 |
| ACL | 33.3 [23.1, 43.6] | 34.7 | 3.8 | 0 | 1.1 |
| JUDGEONLY | 28.4 [18.7, 38.2] | 36.0 | 21.0 | 100.0 | 6.6 |
| NOJUDGE | 1.3 [0.0, 4.0] | 37.8 | 96.5 | 0 | 65.5 |
| FULL | 6.7 [1.8, 12.4] | 33.3 | 80.0 | 40.5 | 11.8 |
