# Post-hoc principle-disable ablation

Upper-bound counterfactual derived from existing `results.csv` (no re-run).  Each row assumes a Pn-catch becomes a success when Pn is disabled -- a worst-case bound; the true ablation requires a re-run with `attacks.harness --disable-principles Pn`.

### Group A / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.98%** (3/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.98% | +0.00pp |
| -P2 | 82 | 27.87% | +26.89pp |
| -P3 | 96 | 32.46% | +31.48pp |
| -P4 | 25 | 9.18% | +8.20pp |
| -P5 | 5 | 2.62% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 94 trials (30.82%)
- `none`: 3 trials (0.98%)

### Group A / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.91%** (3/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.91% | +0.00pp |
| -P2 | 28 | 9.39% | +8.48pp |
| -P3 | 54 | 17.27% | +16.36pp |
| -P4 | 25 | 8.48% | +7.57pp |
| -P5 | 5 | 2.42% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 215 trials (65.15%)
- `none`: 3 trials (0.91%)

### Group A / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.33%** (1/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.33% | +0.00pp |
| -P2 | 46 | 15.41% | +15.08pp |
| -P3 | 63 | 20.98% | +20.65pp |
| -P4 | 25 | 8.52% | +8.19pp |
| -P5 | 5 | 1.97% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 165 trials (54.10%)
- `none`: 1 trials (0.33%)

### Group A / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **1.43%** (4/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.43% | +0.00pp |
| -P2 | 35 | 13.93% | +12.50pp |
| -P3 | 132 | 48.57% | +47.14pp |
| -P4 | 25 | 10.36% | +8.93pp |
| -P5 | 5 | 3.21% | +1.78pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 79 trials (28.21%)
- `none`: 4 trials (1.43%)

### Group B / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.00%** (0/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.00% | +0.00pp |
| -P2 | 30 | 9.84% | +9.84pp |
| -P3 | 0 | 0.00% | +0.00pp |
| -P4 | 25 | 8.20% | +8.20pp |
| -P5 | 5 | 1.64% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 245 trials (80.33%)

### Group C / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.98%** (3/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.98% | +0.00pp |
| -P2 | 82 | 27.87% | +26.89pp |
| -P3 | 96 | 32.46% | +31.48pp |
| -P4 | 25 | 9.18% | +8.20pp |
| -P5 | 5 | 2.62% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 94 trials (30.82%)
- `none`: 3 trials (0.98%)

### Group C / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **1.52%** (5/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.52% | +0.00pp |
| -P2 | 28 | 10.00% | +8.48pp |
| -P3 | 41 | 13.94% | +12.42pp |
| -P4 | 25 | 9.09% | +7.57pp |
| -P5 | 5 | 3.03% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 226 trials (68.48%)
- `none`: 5 trials (1.52%)

### Group C / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.66%** (2/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.66% | +0.00pp |
| -P2 | 46 | 15.74% | +15.08pp |
| -P3 | 62 | 20.98% | +20.32pp |
| -P4 | 25 | 8.85% | +8.19pp |
| -P5 | 5 | 2.30% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 165 trials (54.10%)
- `none`: 2 trials (0.66%)

### Group C / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **1.43%** (4/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.43% | +0.00pp |
| -P2 | 35 | 13.93% | +12.50pp |
| -P3 | 133 | 48.93% | +47.50pp |
| -P4 | 25 | 10.36% | +8.93pp |
| -P5 | 5 | 3.21% | +1.78pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 78 trials (27.86%)
- `none`: 4 trials (1.43%)

### Group D / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **2.30%** (7/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 2.30% | +0.00pp |
| -P2 | 63 | 22.95% | +20.65pp |
| -P3 | 88 | 31.15% | +28.85pp |
| -P4 | 25 | 10.49% | +8.19pp |
| -P5 | 5 | 3.93% | +1.63pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 117 trials (38.36%)
- `none`: 7 trials (2.30%)

### Group D / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.61%** (2/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.61% | +0.00pp |
| -P2 | 78 | 24.24% | +23.63pp |
| -P3 | 91 | 28.18% | +27.57pp |
| -P4 | 25 | 8.18% | +7.57pp |
| -P5 | 5 | 2.12% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 129 trials (39.09%)
- `none`: 2 trials (0.61%)

### Group D / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.98%** (3/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.98% | +0.00pp |
| -P2 | 54 | 18.69% | +17.71pp |
| -P3 | 80 | 27.21% | +26.23pp |
| -P4 | 25 | 9.18% | +8.20pp |
| -P5 | 5 | 2.62% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 138 trials (45.25%)
- `none`: 3 trials (0.98%)

### Group D / legal

- Trials evaluated: **271**
- Current AgenticCyOps ASR: **1.48%** (4/271)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.48% | +0.00pp |
| -P2 | 30 | 12.55% | +11.07pp |
| -P3 | 71 | 27.68% | +26.20pp |
| -P4 | 25 | 10.70% | +9.22pp |
| -P5 | 5 | 3.32% | +1.84pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 136 trials (50.18%)
- `none`: 4 trials (1.48%)

### Group E / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.98%** (3/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.98% | +0.00pp |
| -P2 | 82 | 27.87% | +26.89pp |
| -P3 | 96 | 32.46% | +31.48pp |
| -P4 | 25 | 9.18% | +8.20pp |
| -P5 | 5 | 2.62% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 94 trials (30.82%)
- `none`: 3 trials (0.98%)

### Group E / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.91%** (3/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.91% | +0.00pp |
| -P2 | 28 | 9.39% | +8.48pp |
| -P3 | 54 | 17.27% | +16.36pp |
| -P4 | 25 | 8.48% | +7.57pp |
| -P5 | 5 | 2.42% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 215 trials (65.15%)
- `none`: 3 trials (0.91%)

### Group E / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.33%** (1/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.33% | +0.00pp |
| -P2 | 46 | 15.41% | +15.08pp |
| -P3 | 64 | 21.31% | +20.98pp |
| -P4 | 25 | 8.52% | +8.19pp |
| -P5 | 5 | 1.97% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 164 trials (53.77%)
- `none`: 1 trials (0.33%)

### Group E / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **1.07%** (3/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.07% | +0.00pp |
| -P2 | 35 | 13.57% | +12.50pp |
| -P3 | 133 | 48.57% | +47.50pp |
| -P4 | 25 | 10.00% | +8.93pp |
| -P5 | 5 | 2.86% | +1.79pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 79 trials (28.21%)
- `none`: 3 trials (1.07%)

### Group G / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.00%** (0/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.00% | +0.00pp |
| -P2 | 33 | 10.82% | +10.82pp |
| -P3 | 4 | 1.31% | +1.31pp |
| -P4 | 25 | 8.20% | +8.20pp |
| -P5 | 5 | 1.64% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 238 trials (78.03%)

### Group G / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.91%** (3/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.91% | +0.00pp |
| -P2 | 27 | 9.09% | +8.18pp |
| -P3 | 35 | 11.52% | +10.61pp |
| -P4 | 25 | 8.48% | +7.57pp |
| -P5 | 5 | 2.42% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 235 trials (71.21%)
- `none`: 3 trials (0.91%)

### Group G / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.33%** (1/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.33% | +0.00pp |
| -P2 | 26 | 8.85% | +8.52pp |
| -P3 | 11 | 3.93% | +3.60pp |
| -P4 | 25 | 8.52% | +8.19pp |
| -P5 | 5 | 1.97% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 237 trials (77.70%)
- `none`: 1 trials (0.33%)

### Group G / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **0.36%** (1/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.36% | +0.00pp |
| -P2 | 34 | 12.50% | +12.14pp |
| -P3 | 33 | 12.14% | +11.78pp |
| -P4 | 25 | 9.29% | +8.93pp |
| -P5 | 5 | 2.14% | +1.78pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 182 trials (65.00%)
- `none`: 1 trials (0.36%)

### Group H / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.66%** (2/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.66% | +0.00pp |
| -P2 | 47 | 16.07% | +15.41pp |
| -P3 | 24 | 8.52% | +7.86pp |
| -P4 | 25 | 8.85% | +8.19pp |
| -P5 | 5 | 2.30% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 202 trials (66.23%)
- `none`: 2 trials (0.66%)

### Group H / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **1.21%** (4/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.21% | +0.00pp |
| -P2 | 30 | 10.30% | +9.09pp |
| -P3 | 30 | 10.30% | +9.09pp |
| -P4 | 25 | 8.79% | +7.58pp |
| -P5 | 5 | 2.73% | +1.52pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 236 trials (71.52%)
- `none`: 4 trials (1.21%)

### Group H / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.33%** (1/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.33% | +0.00pp |
| -P2 | 51 | 17.05% | +16.72pp |
| -P3 | 116 | 38.36% | +38.03pp |
| -P4 | 25 | 8.52% | +8.19pp |
| -P5 | 5 | 1.97% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 107 trials (35.08%)
- `none`: 1 trials (0.33%)

### Group H / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **0.71%** (2/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.71% | +0.00pp |
| -P2 | 25 | 9.64% | +8.93pp |
| -P3 | 37 | 13.93% | +13.22pp |
| -P4 | 25 | 9.64% | +8.93pp |
| -P5 | 5 | 2.50% | +1.79pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 186 trials (66.43%)
- `none`: 2 trials (0.71%)

### Group I / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **1.31%** (4/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.31% | +0.00pp |
| -P2 | 72 | 24.92% | +23.61pp |
| -P3 | 120 | 40.66% | +39.35pp |
| -P4 | 25 | 9.51% | +8.20pp |
| -P5 | 5 | 2.95% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 79 trials (25.90%)
- `none`: 4 trials (1.31%)

### Group I / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.91%** (3/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.91% | +0.00pp |
| -P2 | 145 | 44.85% | +43.94pp |
| -P3 | 96 | 30.00% | +29.09pp |
| -P4 | 25 | 8.48% | +7.57pp |
| -P5 | 5 | 2.42% | +1.51pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 56 trials (16.97%)
- `none`: 3 trials (0.91%)

### Group I / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.66%** (2/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.66% | +0.00pp |
| -P2 | 60 | 20.33% | +19.67pp |
| -P3 | 175 | 58.03% | +57.37pp |
| -P4 | 25 | 8.85% | +8.19pp |
| -P5 | 5 | 2.30% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 38 trials (12.46%)
- `none`: 2 trials (0.66%)

### Group I / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **0.71%** (2/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.71% | +0.00pp |
| -P2 | 35 | 13.21% | +12.50pp |
| -P3 | 212 | 76.43% | +75.72pp |
| -P4 | 25 | 9.64% | +8.93pp |
| -P5 | 5 | 2.50% | +1.79pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 1 trials (0.36%)
- `none`: 2 trials (0.71%)

### Group J / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.00%** (0/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.00% | +0.00pp |
| -P2 | 30 | 9.84% | +9.84pp |
| -P3 | 0 | 0.00% | +0.00pp |
| -P4 | 25 | 8.20% | +8.20pp |
| -P5 | 5 | 1.64% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 245 trials (80.33%)

### Group J / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.30%** (1/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.30% | +0.00pp |
| -P2 | 25 | 7.88% | +7.58pp |
| -P3 | 1 | 0.61% | +0.31pp |
| -P4 | 25 | 7.88% | +7.58pp |
| -P5 | 5 | 1.82% | +1.52pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 273 trials (82.73%)
- `none`: 1 trials (0.30%)

### Group K / cyberops

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **1.64%** (5/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 1.64% | +0.00pp |
| -P2 | 90 | 31.15% | +29.51pp |
| -P3 | 87 | 30.16% | +28.52pp |
| -P4 | 22 | 8.85% | +7.21pp |
| -P5 | 5 | 3.28% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 96 trials (31.48%)
- `none`: 5 trials (1.64%)

### Group K / healthcare

- Trials evaluated: **330**
- Current AgenticCyOps ASR: **0.30%** (1/330)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.30% | +0.00pp |
| -P2 | 135 | 41.21% | +40.91pp |
| -P3 | 86 | 26.36% | +26.06pp |
| -P4 | 25 | 7.88% | +7.58pp |
| -P5 | 5 | 1.82% | +1.52pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 78 trials (23.64%)
- `none`: 1 trials (0.30%)

### Group K / finance

- Trials evaluated: **305**
- Current AgenticCyOps ASR: **0.33%** (1/305)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.33% | +0.00pp |
| -P2 | 55 | 18.36% | +18.03pp |
| -P3 | 176 | 58.03% | +57.70pp |
| -P4 | 25 | 8.52% | +8.19pp |
| -P5 | 5 | 1.97% | +1.64pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 43 trials (14.10%)
- `none`: 1 trials (0.33%)

### Group K / legal

- Trials evaluated: **280**
- Current AgenticCyOps ASR: **0.71%** (2/280)

**Upper-bound −Pn ASR (worst case if Pn disabled):**

| ablation | Pn caught | upper-bound ASR | Δ vs full |
|---|---:|---:|---:|
| -P1 | 0 | 0.71% | +0.00pp |
| -P2 | 40 | 15.00% | +14.29pp |
| -P3 | 195 | 70.36% | +69.65pp |
| -P4 | 25 | 9.64% | +8.93pp |
| -P5 | 5 | 2.50% | +1.79pp |

**Context (non-P-layer outcomes):**

- `agent_refused`: 13 trials (4.64%)
- `none`: 2 trials (0.71%)

