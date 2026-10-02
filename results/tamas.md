# TAMAS (Qwen3-235B primary, CrewAI hierarchical, DEFER tool-call mediation)

ASR as run with the live local2 panel; for FULL's tool-based types also re-adjudicated under Local4.

| Attack type | FLAT ASR % | FULL ASR % (as run) | FULL ASR % (Local4) |
|---|---|---|---|
| DPI | 36.9 [25.5, 48.7] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| impersonation | 18.8 [9.4, 29.3] | 2.7 [0.0, 7.3] | 5.3 [0.7, 11.3] |
| colluding | 40.0 [26.7, 52.7] | 2.0 [0.0, 6.1] | 2.0 [0.0, 6.1] |
| byzantine | 91.2 [85.6, 96.0] | 83.9 [77.7, 89.1] | as run |
| contradicting | 18.6 [11.1, 26.4] | 18.6 [11.6, 25.9] | as run |

All attack types: FLAT 41.2 [35.7, 46.8], FULL 21.4 [17.0, 26.1].

Benign (IPI tasks): FULL denies 10.6% of tool calls; FLAT 0.0%.