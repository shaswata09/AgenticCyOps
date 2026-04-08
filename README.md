# AgenticCyOps — Empirical Evaluation Testbed

> **Securing Multi-Agentic AI Integration in Enterprise Cyber Operations**

This repository contains the evaluation testbed for the AgenticCyOps framework, a security architecture for LLM-powered multi-agent systems (MAS). The testbed implements a full Security Operations Center (SOC) pipeline with 16 MCP-based tool servers, 12 memory stores, phase-scoped agents, consensus-validated execution, and six adversarial attack scenarios — evaluated across three configurations and five open-source model families.

---

## Table of Contents

- [Overview](#overview)
- [Key Results](#key-results)
- [Hardware Requirements](#hardware-requirements)
- [Model Requirements](#model-requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Project Structure](#project-structure)
- [Configurations](#configurations)
- [Running Experiments](#running-experiments)
- [Analysis & Reproducing Results](#analysis--reproducing-results)
- [Citation](#citation)
- [License](#license)

---

## Overview

AgenticCyOps addresses the security challenges of integrating LLM-powered multi-agent systems into enterprise cyber operations. The framework is built on two observations:

1. **MAS attack vectors converge on two integration surfaces:** tool orchestration and memory management
2. **Five defensive principles** — authorized interfaces, capability scoping, verified execution, memory integrity, and access-controlled isolation — provide defense-in-depth coverage

This testbed empirically validates these claims through:

| Evaluation | Runs | What It Tests |
|-----------|------|---------------|
| **A: Attack Path Replay** | ~630 | 6 attack scenarios (AP-1 through AP-6) across 3 configurations |
| **B: Trust Boundary Analysis** | Analytical | Weighted boundary reduction (200 → 56, ≥72%) |
| **C: Memory Poisoning** | ~90 | Write-boundary filtering efficacy at 5%, 10%, 20% poisoning |
| **D: TAMAS Benchmark** | ~400 | Independent adversarial benchmark comparison |
| **Ablation Study** | ~270 | Necessity of each defensive principle |
| **Validator Diversity** | ~90 | Correlated failure across same-family vs diverse validators |
| **E: Consensus Overhead** | From A logs | Latency and token cost analysis |
| **H: Cross-Domain** | Structural | Generalizability to financial fraud detection |
| **Total** | **~1,570** | |

---

## Key Results

*(Tables populated after running experiments — see `results/tables/`)*

- **Table R1:** Attack interception rates per AP per configuration
- **Table R2:** Weighted trust boundary reduction (unweighted + weighted × 3 configs)
- **Table R3:** TAMAS benchmark comparison (flat GPT-4o vs defended Qwen3)
- **Table R4:** Ablation degradation per principle
- **Table R5:** Consensus latency overhead per validation loop
- **Table R6:** Benign workflow completion rates
- **Table R7:** Validator diversity — consensus failure by model family configuration
- **Table R8:** Memory poisoning propagation resistance
- **Table R9:** Model-independence check (Qwen3 vs GLM-4.7)

---

## Hardware Requirements

### Minimum (to reproduce core results)

| Component | Specification |
|-----------|--------------|
| GPUs | 2× NVIDIA A100 80GB or equivalent |
| RAM | 128 GB |
| Storage | 600 GB (models) + 50 GB (experiment data) |
| Network | Internet access for API calls (Claude Sonnet, GPT-4o) |

With 2× A100: run Qwen3-235B-A22B only (primary agent), use API providers for diversity models and all validators.

### Recommended (full reproduction as published)

| Component | Specification |
|-----------|--------------|
| GPUs | 6× NVIDIA H200 141GB (4 NVLink + 2 standalone) |
| RAM | 256 GB |
| Storage | 1 TB |
| CUDA | 12.4+ |

### GPU Assignment (6× H200 configuration)

```
GPU 0 ─┐ NVLink ── Qwen3-235B-A22B-Instruct  (Primary agents + Host)
GPU 1 ─┘                                       Port 8000

GPU 2 ─┐ NVLink ── GLM-4.7                     (Diversity agents)
GPU 3 ─┘                                       Port 8001

GPU 4 ──────────── Qwen3-32B                   (Validator V1, Port 8002)
                   Mistral-Small-3.2-24B        (Validator V2, Port 8003)

GPU 5 ──────────── Llama-4-Scout-17B-16E        (Validator V3, Port 8004)
```

---

## Model Requirements

### Open-Source Models (downloaded locally)

| Model | Role | Family | Size | HuggingFace Repo |
|-------|------|--------|------|-------------------|
| Qwen3-235B-A22B-Instruct | Primary agents + Host | Qwen (Alibaba) | ~120 GB | `Qwen/Qwen3-235B-A22B-Instruct` |
| GLM-4.7 | Diversity agents | GLM (Zhipu) | ~260 GB | `zai-org/GLM-4.7` |
| Qwen3-32B | Validator V1 | Qwen (Alibaba) | ~64 GB | `Qwen/Qwen3-32B` |
| Mistral-Small-3.2-24B-Instruct | Validator V2 | Mistral | ~48 GB | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` |
| Llama-4-Scout-17B-16E-Instruct | Validator V3 | Meta | ~55 GB | `meta-llama/Llama-4-Scout-17B-16E-Instruct` |
| BGE-EN-ICL | Embedding (ChromaDB) | BAAI | ~2 GB | `BAAI/bge-en-icl` |

### Proprietary Models (API only)

| Model | Role | Estimated Cost |
|-------|------|---------------|
| Claude Sonnet | Validator V4 | ~$12–20 |
| GPT-4o | TAMAS baseline | ~$25–50 |

**Total API budget: ~$40–70**

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_ORG/agenticcyops-experiments.git
cd agenticcyops-experiments

# 2. Create environment
conda create -n agenticcyops python=3.11 -y
conda activate agenticcyops

# 3. Install dependencies
chmod +x install.sh
./install.sh

# 4. Configure API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY, OPENAI_API_KEY, HF_TOKEN

# 5. Download models (~550 GB, takes several hours)
cd /path/to/model/storage
chmod +x download_models.sh
./download_models.sh

# 6. Start vLLM servers (5 terminals or use start_servers.sh)
chmod +x start_servers.sh
./start_servers.sh

# 7. Verify servers
for port in 8000 8001 8002 8003 8004; do
  curl -s http://localhost:$port/v1/models | python -m json.tool | head -3
done

# 8. Run a benign end-to-end test
python -m attacks.benign_scenarios --config agenticcyops --trials 1

# 9. Run full evaluation
python -m attacks.harness --eval all --config all --trials 30
```

---

## Detailed Setup

### Step 1: Environment

```bash
conda create -n agenticcyops python=3.11 -y
conda activate agenticcyops
```

### Step 2: Dependencies

The `install.sh` script handles the three-step install order:

```bash
# Step 1: PyTorch with CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Step 2: All other dependencies
pip install -r requirements.txt

# Step 3: vLLM nightly (required for GLM-4.7)
pip install -U vllm --pre \
  --index-url https://pypi.org/simple \
  --extra-index-url https://wheels.vllm.ai/nightly
```

Verify installation:

```bash
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPUs: {torch.cuda.device_count()}')"
python -c "import vllm; print(f'vLLM {vllm.__version__}')"
```

### Step 3: API Keys

```bash
cp .env.example .env
```

Edit `.env`:

```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

### Step 4: Model Download

```bash
# From your model storage directory (needs ~550 GB)
chmod +x download_models.sh
./download_models.sh
```

This downloads all 6 models with HuggingFace's Rust-based parallel transfer (`hf_transfer`). Models are stored as actual files (no symlinks to HF cache).

Expected directory structure after download:

```
/path/to/models/
├── Qwen/Qwen3-235B-A22B-Instruct/    (~120 GB)
├── zai-org/GLM-4.7/                   (~260 GB)
├── Qwen/Qwen3-32B/                    (~64 GB)
├── mistralai/Mistral-Small-3.2-24B-Instruct-2506/  (~48 GB)
├── meta-llama/Llama-4-Scout-17B-16E-Instruct/      (~55 GB)
└── BAAI/bge-en-icl/                   (~2 GB)
```

### Step 5: Start vLLM Servers

Update the model paths in `start_servers.sh` to match your storage location, then:

```bash
chmod +x start_servers.sh
./start_servers.sh
```

Or start individually in separate terminals:

```bash
# Primary agents + Host (GPU 0-1)
CUDA_VISIBLE_DEVICES=0,1 vllm serve /path/to/models/Qwen/Qwen3-235B-A22B-Instruct \
  --tensor-parallel-size 2 --dtype bfloat16 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --gpu-memory-utilization 0.9 --port 8000

# Diversity agents (GPU 2-3)
CUDA_VISIBLE_DEVICES=2,3 vllm serve /path/to/models/zai-org/GLM-4.7 \
  --tensor-parallel-size 2 --dtype bfloat16 \
  --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm45 \
  --gpu-memory-utilization 0.9 --port 8001

# Validator V1 (GPU 4)
CUDA_VISIBLE_DEVICES=4 vllm serve /path/to/models/Qwen/Qwen3-32B \
  --dtype bfloat16 --gpu-memory-utilization 0.45 --port 8002

# Validator V2 (GPU 4, shared)
CUDA_VISIBLE_DEVICES=4 vllm serve /path/to/models/mistralai/Mistral-Small-3.2-24B-Instruct-2506 \
  --dtype bfloat16 --gpu-memory-utilization 0.45 --port 8003

# Validator V3 (GPU 5)
CUDA_VISIBLE_DEVICES=5 vllm serve /path/to/models/meta-llama/Llama-4-Scout-17B-16E-Instruct \
  --dtype bfloat16 --gpu-memory-utilization 0.85 --port 8004
```

**Note:** V1 and V2 share GPU 4. If OOM occurs, run them sequentially (start V1 for attack/ablation runs, swap to V2 for validator diversity runs).

### Step 6: Initialize Memory Layer

```bash
# Initialize ChromaDB with 12 collections and seed data
python -m memory.chromadb_setup --embedding-model /path/to/models/BAAI/bge-en-icl
python -m memory.seed_data
```

### Step 7: Verify End-to-End

```bash
# Run one benign incident through AgenticCyOps pipeline
python -m attacks.benign_scenarios --config agenticcyops --trials 1 --verbose

# Expected: incident completes Monitor → Analyze → Admin → Report
# Expected: all 5 principles log activity, no false blocks
```

---

## Project Structure

```
agenticcyops-experiments/
│
├── .env                              # API keys (not committed)
├── .gitignore
├── install.sh                        # 3-step dependency installer
├── requirements.txt                  # All Python dependencies
├── start_servers.sh                  # Launch 5 vLLM servers
├── download_models.sh                # Download 6 models from HuggingFace
├── README.md                         # This file
│
├── configs/                          # Phase manifests + system configs
│   ├── monitor_manifest.json
│   ├── analyze_manifest.json
│   ├── admin_manifest.json
│   ├── report_manifest.json
│   ├── flat_config.yaml              # Flat MAS: all access open
│   ├── acl_config.yaml               # ACL-Hardened: network ACLs only
│   ├── agenticcyops_config.yaml      # Full framework
│   └── validators.yaml               # V1–V4 endpoints and models
│
├── mcp_servers/                      # 16 mock tool servers (FastAPI + MCP)
│   ├── base_server.py
│   ├── monitor/                      # T1–T4
│   ├── analyze/                      # T5–T7
│   ├── admin/                        # T8–T12
│   ├── report/                       # T13–T16
│   └── test_servers.py
│
├── agents/                           # LLM-powered phase agents
│   ├── base_agent.py                 # Switchable Qwen3/GLM-4.7 client
│   ├── monitor_agent.py
│   ├── analyze_agent.py
│   ├── admin_agent.py
│   └── report_agent.py
│
├── host/                             # SOAR Host orchestrator
│   ├── orchestrator.py               # LangGraph CoT + phase routing
│   ├── manifest_enforcer.py
│   └── handoff.py
│
├── memory/                           # Organizational memory layer
│   ├── chromadb_setup.py             # 12 collections + bge-en-icl
│   ├── seed_data.py
│   ├── mma_gateway.py                # Memory Management Agent
│   ├── access_control.py             # Phase-partitioned policies
│   └── write_filter.py               # Schema + cosine similarity
│
├── consensus/                        # Consensus validation module
│   ├── validator.py                  # 3-of-4 validators, ≥2/3 approve
│   ├── recovery_loop.py             # Admin phase (irreversible actions)
│   ├── improvement_loop.py          # Report phase (memory writes)
│   └── escalation.py                # Human-in-the-loop handler
│
├── attacks/                          # Attack scenarios + harness
│   ├── harness.py                    # attack × config × trials → logs
│   ├── ap1_tool_redirection.py
│   ├── ap2_memory_poisoning.py
│   ├── ap3_confused_deputy.py
│   ├── ap4_cross_phase_exfil.py
│   ├── ap5_irreversible_action.py
│   ├── ap6_replay_attack.py
│   ├── benign_scenarios.py
│   └── payloads/                     # JSON attack variant definitions
│       ├── ap1_variants.json
│       ├── ap2_variants.json
│       ├── ap3_variants.json
│       ├── ap4_variants.json
│       ├── ap5_variants.json
│       ├── ap6_variants.json
│       └── benign_alerts.json
│
├── benchmarks/                       # External benchmarks
│   ├── tamas/                        # TAMAS adversarial benchmark
│   │   ├── setup.sh
│   │   ├── run_baseline.py           # Flat + GPT-4o
│   │   ├── run_defended.py           # AgenticCyOps + Qwen3
│   │   └── compare.py
│   └── boundary/                     # Trust boundary analysis
│       ├── classify_boundaries.py
│       ├── boundary_weights.csv
│       ├── stress_test.py
│       └── sensitivity.py
│
├── ablation/                         # Ablation + validator diversity
│   ├── run_ablation.py
│   ├── validator_diversity.py
│   └── configs/
│       ├── no_p1.yaml
│       ├── no_p2.yaml
│       ├── no_p3.yaml
│       ├── no_p4.yaml
│       └── no_p5.yaml
│
├── analysis/                         # Results processing
│   ├── parse_logs.py
│   ├── compute_metrics.py
│   ├── statistical_tests.py
│   ├── generate_tables.py
│   ├── generate_figures.py
│   └── results_explorer.ipynb        # Interactive figure tuning
│
├── cross_domain/                     # Generalizability analysis
│   ├── fraud_mapping.md
│   ├── boundary_comparison.md
│   └── generalizability.md
│
├── logs/                             # Structured JSON experiment logs
│   ├── eval_a/
│   ├── eval_b/
│   ├── eval_c/
│   ├── eval_d/
│   ├── ablation/
│   └── validator_diversity/
│
├── results/                          # Output tables and figures
│   ├── tables/
│   │   ├── R1_attack_interception.csv
│   │   ├── R2_boundary_reduction.csv
│   │   ├── R3_tamas_benchmark.csv
│   │   ├── R4_ablation.csv
│   │   ├── R5_consensus_latency.csv
│   │   ├── R6_benign_completion.csv
│   │   ├── R7_validator_diversity.csv
│   │   ├── R8_memory_poisoning.csv
│   │   └── R9_glm_diversity.csv
│   └── figures/
│       ├── asr_by_ap.png
│       ├── boundary_reduction.png
│       ├── ablation_heatmap.png
│       ├── validator_diversity.png
│       └── poisoning_propagation.png
│
├── docs/                             # Documentation
│   ├── AgenticCyOps_Experiment_Plan.md
│   ├── AgenticCyOps_Experiment_Plan.pdf
│   ├── AgenticCyOps_10Day_Checklist.md
│   ├── AgenticCyOps_10Day_Checklist.pdf
│   ├── engineering_challenges.md
│   └── rebuttal_draft.md
│
└── tests/                            # Unit + integration tests
    ├── test_manifest_enforcer.py
    ├── test_access_control.py
    ├── test_write_filter.py
    ├── test_consensus.py
    ├── test_harness.py
    └── test_e2e_benign.py
```

---

## Configurations

The testbed supports three system configurations to isolate the contribution of each defense layer:

### Flat MAS (Baseline)

- All 4 agents access all 16 tools and 12 memory stores
- No manifest enforcement, no consensus, no MMA
- Peer-to-peer agent communication
- **200 trust boundaries, all unverified**

### ACL-Hardened MAS

- Same phase-to-tool and phase-to-memory assignments as AgenticCyOps
- Enforcement via network-level ACLs (HTTP 403 on out-of-scope calls)
- **No** signed manifests, consensus validation, write-boundary filtering, or MMA mediation
- Tests whether simple access control is sufficient (it isn't — semantic attacks bypass ACLs)

### AgenticCyOps

- **P1 (Authorized Interface):** Signed manifests, admin-approved tool catalog
- **P2 (Capability Scoping):** Phase-to-tool restriction at Host routing layer
- **P3 (Verified Execution):** 3-of-4 validator consensus (≥2/3 approval) before irreversible actions
- **P4 (Memory Integrity):** Write-boundary filtering (schema + cosine similarity), versioned ledger
- **P5 (Access Control):** MMA-mediated memory with phase-partitioned read/write policies
- Host-mediated sequential handoffs: Monitor → Analyze → Admin → Report
- **56 trust boundaries, all actively verified**

---

## Running Experiments

### Prerequisites

Before running experiments, ensure:

1. All 5 vLLM servers are running and responding
2. ChromaDB is initialized with seed data
3. `.env` has valid API keys
4. At least one benign E2E test passes

### Individual Evaluations

```bash
# Evaluation A: Attack Path Replay (6 APs × 3 configs × 30 trials)
python -m attacks.harness --eval A --config all --trials 30

# Run single AP against single config
python -m attacks.harness --ap 1 --config agenticcyops --trials 30

# GLM-4.7 diversity check
python -m attacks.harness --ap 1 --config agenticcyops --trials 30 \
  --model-url http://localhost:8001/v1

# Evaluation B: Trust Boundary Analysis
python -m benchmarks.boundary.classify_boundaries
python -m benchmarks.boundary.sensitivity
python -m benchmarks.boundary.stress_test --config agenticcyops

# Evaluation C: Memory Poisoning
python -m attacks.harness --eval C --poison-rates 0.05 0.10 0.20 --trials 10

# Evaluation D: TAMAS Benchmark
cd benchmarks/tamas && bash setup.sh
python run_baseline.py      # Flat + GPT-4o
python run_defended.py      # AgenticCyOps + Qwen3
python compare.py

# Ablation Study
python -m ablation.run_ablation --all --trials 30

# Validator Diversity
python -m ablation.validator_diversity --trials 30
```

### Full Evaluation Suite

```bash
# Runs everything in sequence (~1,570 trials, several hours)
python -m attacks.harness --eval all --config all --trials 30
python -m ablation.run_ablation --all --trials 30
python -m ablation.validator_diversity --trials 30
```

### Monitoring

```bash
# Watch logs in real-time
tail -f logs/eval_a/*.jsonl | python -m analysis.parse_logs --stream

# Check progress
python -m analysis.compute_metrics --summary logs/eval_a/
```

---

## Analysis & Reproducing Results

### Generate Result Tables

```bash
# Parse all logs and compute metrics
python -m analysis.compute_metrics --input logs/ --output results/tables/

# Run statistical tests (McNemar's, CIs)
python -m analysis.statistical_tests --input results/tables/

# Generate all tables (R1–R9)
python -m analysis.generate_tables --input results/tables/ --output results/tables/
```

### Generate Figures

```bash
# Generate all publication-ready figures
python -m analysis.generate_figures --input results/tables/ --output results/figures/

# Or use the interactive notebook for fine-tuning
jupyter notebook analysis/results_explorer.ipynb
```

### Expected Results

After running the full evaluation, the `results/` directory should contain:

| File | Content |
|------|---------|
| `R1_attack_interception.csv` | ASR per AP per config (6 APs × 3 configs) |
| `R2_boundary_reduction.csv` | Unweighted + weighted reduction (3 configs) |
| `R3_tamas_benchmark.csv` | ASR/TSR/ERS per attack type (flat GPT-4o vs defended Qwen3) |
| `R4_ablation.csv` | ASR with each principle removed |
| `R5_consensus_latency.csv` | Per-loop latency statistics |
| `R6_benign_completion.csv` | Completion rate, false block rate |
| `R7_validator_diversity.csv` | Consensus failure by validator configuration |
| `R8_memory_poisoning.csv` | Propagation rate by poisoning rate |
| `R9_glm_diversity.csv` | Qwen3 vs GLM-4.7 interception comparison |

---

## Reducing Experiment Scope

If compute resources or time are limited, experiments can be run at reduced scale:

| Reduction | Impact | How |
|-----------|--------|-----|
| Fewer trials | Wider confidence intervals | `--trials 10` instead of `--trials 30` |
| Fewer APs | Incomplete attack coverage | `--ap 1 2 3 4` (skip AP-5, AP-6) |
| Skip GLM-4.7 | No model-independence check | Don't start port 8001 |
| Skip TAMAS | No independent benchmark | Skip `benchmarks/tamas/` |
| API validators only | No local V1-V3 needed | Set all validators to Claude in `validators.yaml` |
| 2-GPU setup | Run Qwen3-235B only | Use API providers for diversity + validators |

Minimum viable evaluation (2× A100): Eval A (AP-1–4 only) + Eval B + Ablation = ~500 runs on a single model.

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| vLLM OOM on GPU 4 (V1+V2) | Run V1 and V2 sequentially, not simultaneously |
| GLM-4.7 fails to load | Requires vLLM nightly: `pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly` |
| `tokenizer_mode deepseek_v32` error | Update vLLM to latest nightly |
| Claude API rate limit | `tenacity` retry is built in; reduce concurrent calls or fallback to all-local validators |
| ChromaDB embedding slow | Ensure bge-en-icl runs on GPU: `CUDA_VISIBLE_DEVICES=5 python -m memory.chromadb_setup` |
| TAMAS import errors | Run `cd benchmarks/tamas && bash setup.sh` in a separate virtualenv if dependencies conflict |
| Benign E2E test fails | Check all 5 vLLM servers respond: `curl http://localhost:800X/v1/models` |

---

## Log Format

All experiment logs use structured JSON (one entry per line):

```json
{
  "timestamp": "2026-04-08T14:30:22.451Z",
  "trial_id": "ap1_v3_t12_agenticcyops",
  "source": "monitor_agent",
  "destination": "T8_iam_pam",
  "action": "tool_call",
  "payload_hash": "a3f2b8c1",
  "auth_decision": "deny",
  "mechanism": "P2_capability_scoping",
  "interception_step": 2,
  "latency_ms": 342,
  "tokens_used": 1847,
  "config": "agenticcyops",
  "model": "Qwen3-235B-A22B-Instruct"
}
```

---

## Citation

```bibtex
@inproceedings{mitra2026agenticcyops,
  title     = {AgenticCyOps: Securing Multi-Agentic AI Integration 
               in Enterprise Cyber Operations},
  author    = {Mitra, Shaswata and Patel, Raj and Mittal, Sudip and 
               Rahman, Md Rayhanur and Rahimi, Shahram},
  booktitle = {Proceedings of the Conference on AI and Security (CAIS)},
  year      = {2026}
}
```

---

## License

This testbed is released for research purposes. See [LICENSE](LICENSE) for details.

The models used have their own licenses:
- Qwen3: Apache 2.0
- GLM-4.7: Open weight license (see [zai-org/GLM-4.7](https://huggingface.co/zai-org/GLM-4.7))
- Mistral-Small: Apache 2.0
- Llama-4-Scout: Llama Community License
- BGE-EN-ICL: MIT

---

## Acknowledgments

This research was carried out in the PATENT Lab, Department of Computer Science, The University of Alabama. The testbed was developed and evaluated on university GPU infrastructure (6× NVIDIA H200).