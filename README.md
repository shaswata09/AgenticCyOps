# AgenticCyOps — Empirical Evaluation Testbed

> **Securing Multi-Agentic AI Integration in Enterprise Operations**

This repository contains the evaluation testbed for the AgenticCyOps framework, a domain-agnostic security architecture for LLM-powered multi-agent systems (MAS). The testbed validates the framework across **four enterprise domains** — cybersecurity operations, healthcare, financial fraud detection, and legal case management — with 13-16 MCP-based tool servers per domain, phase-scoped agents, consensus-validated execution, and six adversarial attack scenarios, evaluated across three configurations and seven model families. **Zero framework code changes** are required across domains — only configuration files and tool stubs differ.

---

## Table of Contents

- [Overview](#overview)
- [Key Results](#key-results)
- [Architecture](#architecture)
- [Hardware Requirements](#hardware-requirements)
- [Model Requirements](#model-requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Project Structure](#project-structure)
- [Domain Adapters](#domain-adapters)
- [Configurations](#configurations)
- [Running Experiments](#running-experiments)
- [Analysis & Reproducing Results](#analysis--reproducing-results)
- [Citation](#citation)
- [License](#license)

---

## Overview

AgenticCyOps addresses the security challenges of integrating LLM-powered multi-agent systems into enterprise operations. The framework is built on two observations:

1. **MAS attack vectors converge on two integration surfaces:** tool orchestration and memory management
2. **Five defensive principles** — authorized interfaces, capability scoping, verified execution, memory integrity, and access-controlled isolation — provide domain-agnostic defense-in-depth coverage

The key architectural claim is that these five principles are **not domain-specific** — they are structural constraints on how agents interact with tools and memory, independent of what the tools do or what domain they serve.

This testbed validates that claim through:

| Evaluation | Runs | Domains | What It Tests |
|-----------|------|---------|---------------|
| **A: Attack Path Replay** | ~630 | CyberOps | 6 attack scenarios (AP-1 through AP-6), full depth |
| **B: Trust Boundary Analysis** | Analytical | All 4 | Weighted boundary reduction across domains |
| **C: Memory Poisoning** | ~90 | CyberOps | Write-boundary filtering at 5%, 10%, 20% poisoning |
| **D: TAMAS Benchmark** | ~400 | Generic (5 scenarios) | Independent adversarial benchmark |
| **E: Consensus Overhead** | From A logs | CyberOps | Latency and token cost analysis |
| **F: Multi-Domain Generalizability** | ~315 | Healthcare, Finance, Legal | 3 attack analogues per domain, zero code changes |
| **Ablation Study** | ~300 | CyberOps + Finance | Necessity of each principle, cross-domain spot check |
| **Validator Diversity** | ~90 | CyberOps | Correlated failure across same vs diverse model families |
| **Total** | **~1,925** | **4 domains + TAMAS** | |

---

## Key Results

*(Tables populated after running experiments — see `results/tables/`)*

- **Table R1:** CyberOps attack interception rates per AP per configuration
- **Table R2:** Weighted trust boundary reduction (unweighted + weighted × 3 configs)
- **Table R3:** TAMAS benchmark comparison (flat GPT-4o vs defended Qwen3)
- **Table R4:** Ablation degradation per principle (+ cross-domain spot check)
- **Table R5:** Consensus latency overhead per validation loop
- **Table R6:** Benign workflow completion rates across all 4 domains
- **Table R7:** Validator diversity — consensus failure by model family configuration
- **Table R8:** Memory poisoning propagation resistance
- **Table R9:** Model-independence check (Qwen3 vs GLM-4.7)
- **Table R10:** **Cross-domain attack interception (headline table)** — consistent results with "Code Changes: 0"
- **Table R11:** Cross-domain boundary reduction comparison

---

## Architecture

### Domain-Agnostic Core

The following components are **identical across all domains** — zero code changes required:

| Component | Purpose |
|-----------|---------|
| `host/orchestrator.py` | LangGraph Host with CoT planning and phase routing |
| `host/manifest_enforcer.py` | Validates tool calls against phase manifests |
| `agents/base_agent.py` | LLM-powered agent with switchable model backend |
| `consensus/validator.py` | Multi-model consensus (≥2/3 approval) |
| `memory/mma_gateway.py` | Memory Management Agent with access control |
| `memory/write_filter.py` | Schema validation + cosine similarity check |
| `attacks/harness.py` | Attack execution and logging harness |
| `logging_utils/json_logger.py` | Structured JSON instrumentation |

### Domain-Specific Content (Config Only)

Each domain provides only:

| Content | Location | Example |
|---------|----------|---------|
| Phase manifests | `domains/{domain}/configs/` | Which tools each phase can access |
| Tool stubs | `domains/{domain}/tools/` | FastAPI servers (~20 lines each) |
| Memory seeds | `domains/{domain}/seed_data/` | Initial collection entries |
| System prompts | `domains/{domain}/prompts/` | Agent role descriptions |
| Access policies | `domains/{domain}/configs/access_policy.json` | Memory read/write permissions |
| Attack payloads | `domains/{domain}/payloads/` | Domain-specific injection variants |

### Switching Domains

```bash
# Run CyberOps
python -m attacks.harness --domain cyberops --ap ap1 --config agenticcyops --trials 30

# Run Healthcare — same framework, different config
python -m attacks.harness --domain healthcare --ap ap1 --config agenticcyops --trials 10

# Run Finance
python -m attacks.harness --domain finance --ap ap1 --config agenticcyops --trials 10

# Run Legal
python -m attacks.harness --domain legal --ap ap1 --config agenticcyops --trials 10
```

---

## Hardware Requirements

### Minimum (to reproduce core results)

| Component | Specification |
|-----------|--------------|
| GPUs | 2× NVIDIA A100 80GB or equivalent |
| RAM | 128 GB |
| Storage | 400 GB (models) + 50 GB (experiment data) |
| Network | Internet access for API calls (GPT-4o (consensus + TAMAS)) |

With 2× A100: run Qwen3-235B-A22B only (primary agent), use API providers for validators.

### Recommended (full reproduction as published)

| Component | Specification |
|-----------|--------------|
| GPUs | 6× NVIDIA H200 141GB (4 NVLink + 2 standalone) |
| RAM | 256 GB |
| Storage | 1 TB |
| CUDA | 12.4+ |

### GPU Assignment (6× H200 configuration)

```
GPU 0 ─┐
GPU 1 ─┤ TP=4 ── Qwen3-235B-A22B-Instruct-2507  (Primary, Port 8000)
GPU 4 ─┤          GLM-4.7-FP8                     (Diversity, Port 8001; swap with Primary)
GPU 5 ─┘

GPU 2 ──────────── Qwen3-32B                      (Validator V1, Port 8002)

GPU 3 ──────────── DeepSeek-R1-Distill-Qwen-32B   (Validator V2, Port 8005)
                   Mistral-Small-3.2-24B           (Validator V5 optional, Port 8003; swap with V2)

GPU 4 ─┐ TP=2 ── Llama-4-Scout-17B-16E            (Validator V3, Port 8004)
GPU 5 ─┘
```

---

## Model Requirements

### Open-Source Models (downloaded locally)

| Model | Role | Family | Size | HuggingFace Repo |
|-------|------|--------|------|-------------------|
| Qwen3-235B-A22B-Instruct-2507 | Primary agents + Host | Qwen (Alibaba) | ~438 GB | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| GLM-4.7-FP8 | Diversity agents | GLM (Zhipu) | ~334 GB | `zai-org/GLM-4.7-FP8` |
| Qwen3-32B | Validator V1 | Qwen (Alibaba) | ~61 GB | `Qwen/Qwen3-32B` |
| DeepSeek-R1-Distill-Qwen-32B | Validator V2 | DeepSeek | ~64 GB | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` |
| Llama-4-Scout-17B-16E-Instruct | Validator V3 | Meta | ~202 GB | `meta-llama/Llama-4-Scout-17B-16E-Instruct` |
| Mistral-Small-3.2-24B-Instruct | Validator V5 (optional) | Mistral | ~89 GB | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` |
| Qwen3-Embedding-8B | Embedding (ChromaDB) | Qwen (Alibaba) | ~1.2 GB | `Qwen/Qwen3-Embedding-8B` |
| Qwen3-Embedding-0.6B | Embedding (fast/CPU) | Qwen (Alibaba) | ~1.2 GB | `Qwen/Qwen3-Embedding-0.6B` |

### Proprietary Models (API only)

| Model | Role | Estimated Cost |
|-------|------|---------------|
| Claude Sonnet | Validator V4 (optional) | ~$20 (not required) |
| GPT-4o | Validator V6 + TAMAS baseline | ~$12 (consensus only); ~$50 (with TAMAS) |

**Total API budget: ~$12 (consensus only), ~$70 (with TAMAS + optional Claude)**

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
# ANTHROPIC_API_KEY=sk-ant-xxx  # Optional — not needed for default consensus
# Edit .env with your OPENAI_API_KEY, HF_TOKEN

# 5. Download models (~1.5 TB total, takes several hours)
cd /path/to/model/storage
chmod +x download_models.sh
./download_models.sh

# 6. Start vLLM servers
chmod +x start_servers.sh
./start_servers.sh

# 7. Verify servers
for port in 8000 8002 8003 8004; do
  curl -s http://localhost:$port/v1/models | python -m json.tool | head -3
done

# 8. Run a benign end-to-end test (CyberOps)
python -m attacks.harness --domain cyberops --benign --config agenticcyops --trials 1

# 9. Run CyberOps full evaluation (auto charts + PDF)
bash scripts/run_eval_a.sh

# 10. Run multi-domain evaluation (auto charts + PDF)
bash scripts/run_eval_f.sh
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

# Step 3: vLLM nightly (required for GLM-4.7 and DeepSeek-R1)
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
# From your model storage directory
chmod +x download_models.sh
./download_models.sh
```

Downloads all local models with HuggingFace's Rust-based parallel transfer (`hf_transfer`). Models are stored as actual files (no symlinks to HF cache).

### Step 5: Start vLLM Servers

```bash
chmod +x start_servers.sh
./start_servers.sh
```

Or start individually (see [GPU Assignment](#gpu-assignment-6-h200-configuration) for port/GPU mapping).

**Note:** Primary and GLM-4.7-FP8 diversity share GPU 0,1,4,5 (swap — only one runs at a time). V1 is on GPU 2, V2 is on GPU 3 (run simultaneously). V5 Mistral swaps with V2 on GPU 3.

### Step 6: Initialize Memory Layer

```bash
# Initialize all domains
for domain in cyberops healthcare finance legal; do
  python -m memory.chromadb_setup --domain $domain \
    --embedding-model <PROJECT_ROOT>/models/Qwen/Qwen3-Embedding-0.6B  # 0.6B is the default (CPU)
  python -m memory.seed_data --domain $domain
done
```

### Step 7: Verify End-to-End

```bash
# Verify each domain
for domain in cyberops healthcare finance legal; do
  echo "Testing $domain..."
  python -m attacks.harness --domain $domain --benign --config agenticcyops --trials 1 --verbose
done

# Expected: each domain completes Monitor → Analyze → Admin → Report
# Expected: all 5 principles log activity, no false blocks
# Expected: zero code changes — only --domain flag differs
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
├── start_servers.sh                  # Interactive vLLM server launcher
├── monitor.sh                        # Live system monitor
├── gpu_monitor.sh                    # nvidia-smi loop
├── scripts/                          # Experiment runner scripts
│   ├── run_baseline.sh              # Interactive domain baseline verification
│   ├── run_eval_a.sh               # CyberOps attack evaluation (auto charts + PDF)
│   └── run_eval_f.sh               # Multi-domain evaluation (auto charts + PDF)
├── README.md                         # This file
├── experiment_plan.md                # Full evaluation protocol
├── task_checklist.md                 # 10-day execution checklist
│
├── models/                           # Model weights + utilities
│   ├── download_models.sh
│   ├── utils/                        # Per-model Python utility classes
│   │   ├── qwen3_235b.py
│   │   ├── glm47.py
│   │   ├── qwen3_32b.py
│   │   ├── deepseek_r1.py
│   │   ├── mistral_small.py
│   │   ├── llama4_scout.py
│   │   ├── claude_sonnet.py
│   │   ├── gpt4o.py
│   │   ├── qwen3_embedding.py
│   │   └── qwen3_embedding_small.py    # Lightweight 0.6B embedding (CPU)
│   ├── test_scripts/                 # Per-model test notebooks
│   │   ├── test_qwen3_embedding_small.ipynb
│   └── (model weight directories, gitignored)
│
├── domains/                          # Domain-specific configs
│   ├── cyberops/                     # Full pipeline: 16 tools, 12 memory stores
│   │   ├── configs/
│   │   │   ├── monitor_manifest.json
│   │   │   ├── analyze_manifest.json
│   │   │   ├── admin_manifest.json
│   │   │   ├── report_manifest.json
│   │   │   └── access_policy.json
│   │   ├── tools/                    # 16 MCP tool stubs (T1–T16)
│   │   │   ├── monitor/             # T1–T4
│   │   │   ├── analyze/             # T5–T7
│   │   │   ├── admin/               # T8–T12
│   │   │   └── report/              # T13–T16
│   │   ├── seed_data/               # 12 collection seeds (760 entries total, 50-100 each)
│   │   ├── prompts/                 # 4 agent system prompts
│   │   └── payloads/                # 6 APs × 5 variants + benign
│   │       ├── ap1_variants.json
│   │       ├── ap2_variants.json
│   │       ├── ap3_variants.json
│   │       ├── ap4_variants.json
│   │       ├── ap5_variants.json
│   │       ├── ap6_variants.json
│   │       └── benign_alerts.json
│   │
│   ├── healthcare/                   # Adapter: 13 tools, 8 memory stores
│   │   ├── configs/                  # 4 manifests + access_policy.json
│   │   ├── tools/                    # H1–H13 (EHR, Vitals, Imaging, Rx Writer, etc.)
│   │   ├── seed_data/               # 8 collections (10-20 entries each)
│   │   ├── prompts/                 # Triage, Diagnostic, Treatment, Compliance agents
│   │   └── payloads/                # 3 APs × 5 variants + benign
│   │       ├── ap1_variants.json           # Triage → Prescription Writer
│   │       ├── ap2_variants.json           # Poisoned labs → wrong diagnosis
│   │       ├── ap4_variants.json           # PHI exfil into quality metrics
│   │       └── benign_workflows.json
│   │
│   ├── finance/                      # Adapter: 13 tools, 8 memory stores
│   │   ├── configs/
│   │   ├── tools/                    # F1–F13 (Transaction Stream, Account Freeze, SAR, etc.)
│   │   ├── seed_data/
│   │   ├── prompts/                 # Surveillance, Investigator, Action, Compliance agents
│   │   └── payloads/                # 3 APs × 5 variants + benign
│   │       ├── ap1_variants.json           # Surveillance → Account Freeze
│   │       ├── ap2_variants.json           # Falsified fraud determination
│   │       ├── ap5_variants.json           # Mass account freeze
│   │       └── benign_workflows.json
│   │
│   └── legal/                        # Adapter: 13 tools, 8 memory stores
│       ├── configs/
│       ├── tools/                    # L1–L13 (Docket Search, Court Filing, Billing, etc.)
│       ├── seed_data/
│       ├── prompts/                 # Intake, Research, Filing, Client Reporting agents
│       └── payloads/                # 3 APs × 5 variants + benign
│           ├── ap1_variants.json           # Research → Court Filing
│           ├── ap2_variants.json           # Poisoned case law → wrong analysis
│           ├── ap4_variants.json           # Privileged comms in billing
│           └── benign_workflows.json
│
├── host/                             # SOAR Host orchestrator (DOMAIN-AGNOSTIC)
│   ├── orchestrator.py               # LangGraph CoT + phase routing
│   ├── manifest_enforcer.py          # Reads manifests from domains/{domain}/configs/
│   ├── acl_middleware.py            # HTTP-level ACL for acl_hardened config
│   └── handoff.py
│
├── agents/                           # Phase agents (DOMAIN-AGNOSTIC)
│   ├── base_agent.py                 # Loads prompts from domains/{domain}/prompts/
│   ├── monitor_agent.py
│   ├── analyze_agent.py
│   ├── admin_agent.py
│   └── report_agent.py
│
├── memory/                           # Memory layer (DOMAIN-AGNOSTIC)
│   ├── chromadb_setup.py             # Creates collections from domains/{domain}/seed_data/
│   ├── seed_data.py
│   ├── mma_gateway.py                # Reads access_policy from domains/{domain}/configs/
│   ├── access_control.py
│   └── write_filter.py               # Cosine similarity via Qwen3-Embedding-0.6B (CPU default)
│
├── consensus/                        # Consensus module (DOMAIN-AGNOSTIC)
│   ├── validator.py
│   ├── recovery_loop.py
│   ├── improvement_loop.py
│   └── escalation.py
│
├── mcp_servers/                      # Tool server template (DOMAIN-AGNOSTIC)
│   ├── base_server.py                # Generic FastAPI + MCP template
│   └── server_registry.py            # Dynamic tool discovery + start/stop
│
├── logging_utils/                    # Structured JSON instrumentation (DOMAIN-AGNOSTIC)
│   ├── __init__.py
│   └── json_logger.py                # Includes domain field in every event
│
├── attacks/                          # Attack harness (DOMAIN-AGNOSTIC)
│   ├── harness.py                    # --domain flag loads from domains/{domain}/payloads/
│   └── benign_scenarios.py
│
├── benchmarks/
│   ├── tamas/                        # TAMAS adversarial benchmark
│   │   ├── setup.sh
│   │   ├── run_baseline.py
│   │   ├── run_defended.py
│   │   └── compare.py
│   └── boundary/                     # Trust boundary analysis (all domains)
│       ├── classify_boundaries.py
│       ├── boundary_weights.csv      # CyberOps (200 boundaries)
│       ├── cross_domain_boundaries.csv  # All 4 domains
│       ├── stress_test.py
│       └── sensitivity.py
│
├── ablation/
│   ├── run_ablation.py               # --domain flag for cross-domain spot checks
│   ├── validator_diversity.py
│   └── configs/
│       ├── no_p1.yaml
│       ├── no_p2.yaml
│       ├── no_p3.yaml
│       ├── no_p4.yaml
│       └── no_p5.yaml
│
├── analysis/
│   ├── __init__.py
│   ├── verify_baseline.py        # CLI pass/fail readiness gate
│   ├── baseline_dashboard.py     # Seaborn charts + CSV
│   ├── generate_report.py        # 9-page PDF report
│   ├── visualize_pipeline.py     # Pipeline flow diagram
│   ├── parse_logs.py             # Log parsing utilities
│   ├── compute_metrics.py        # Metrics computation
│   ├── statistical_tests.py      # McNemar's, chi-squared, CIs
│   ├── generate_tables.py        # R1-R11 result tables
│   └── generate_figures.py       # Publication figures
│
├── logs/                             # (gitignored)
│   ├── vllm/
│   ├── cyberops_eval_a/
│   ├── healthcare_eval_f/
│   ├── finance_eval_f/
│   ├── legal_eval_f/
│   ├── eval_b/
│   ├── eval_c/
│   ├── eval_d/
│   ├── ablation/
│   └── validator_diversity/
│
├── results/                          # (gitignored)
│   ├── tables/
│   │   ├── R1_attack_interception.csv
│   │   ├── R2_boundary_reduction.csv
│   │   ├── R3_tamas_benchmark.csv
│   │   ├── R4_ablation.csv
│   │   ├── R5_consensus_latency.csv
│   │   ├── R6_benign_completion.csv    # All 4 domains
│   │   ├── R7_validator_diversity.csv
│   │   ├── R8_memory_poisoning.csv
│   │   ├── R9_glm_diversity.csv
│   │   ├── R10_cross_domain_interception.csv   # HEADLINE
│   │   └── R11_cross_domain_boundaries.csv
│   └── figures/
│       ├── asr_by_ap.png
│       ├── cross_domain_comparison.png         # NEW
│       ├── boundary_reduction.png
│       ├── cross_domain_boundaries.png         # NEW
│       ├── ablation_heatmap.png
│       ├── validator_diversity.png
│       └── poisoning_propagation.png
│
├── docs/
│   ├── engineering_challenges.md
│   └── rebuttal_draft.md
│
└── tests/
    ├── test_manifest_enforcer.py
    ├── test_access_control.py
    ├── test_write_filter.py
    ├── test_consensus.py
    ├── test_harness.py
    ├── test_e2e_benign.py
    └── test_domain_adapters.py         # Verifies all 4 domains load and run
```

---

## Domain Adapters

AgenticCyOps claims its five principles are architectural, not domain-specific. To validate this, the testbed includes four enterprise domains. The framework code is identical across all — only configuration files and tool stubs differ.

### CyberOps (Full Pipeline)

Security Operations Center incident response.

| Phase | Agent | Tools | Memory |
|-------|-------|-------|--------|
| Monitor | SOC Triage | UEBA, IDS/CMDB, EDR/NDR, ITSM | Threat Repo, SIEM Lake, CTI KB, Detection Rules |
| Analyze | Investigation | Sandbox, SIEM Search, Code Analyzer | Threat Repo, Asset Inv, Case Mgmt, CTI KB |
| Admin | Response | IAM/PAM, Firewall, Config Mgr, EPP/AV, Ansible | Asset Inv, Policy, Playbooks, BCP |
| Report | Reporting | Dashboard, ISAC/MISP, Editor/Test, GRC Mapper | Playbooks, Compliance, Rules, AAR |

**16 tools, 12 memory stores, 200 flat boundaries → 56 AgenticCyOps boundaries (72% reduction)**

### Healthcare (Adapter)

Clinical decision support and treatment pipeline.

| Phase | Agent | Tools | Memory |
|-------|-------|-------|--------|
| Monitor | Patient Triage | EHR Query, Vitals Monitor, Lab Results, Triage Scoring | Patient Records, Lab Archive |
| Analyze | Diagnostic | Imaging Viewer, Drug Interaction, Clinical Guidelines | Clinical Protocols, Diagnostic History |
| Admin | Treatment | Prescription Writer, Procedure Scheduler, Insurance Pre-Auth | Formulary, Treatment Plans |
| Report | Compliance | Discharge Summary, Regulatory Filing, Quality Metrics | Audit Trail, Compliance Records |

**Key risk:** Patient safety (misrouted tool call → prescriptions by wrong agent), PHI leakage (HIPAA).

### Finance (Adapter)

Fraud detection and regulatory compliance.

| Phase | Agent | Tools | Memory |
|-------|-------|-------|--------|
| Monitor | Surveillance | Transaction Stream, Rule Engine, Customer Profile, Alert Queue | Transaction Log, Customer DB |
| Analyze | Investigation | Graph Analysis, External Fraud DB, Document Verification | Case History, Fraud Patterns |
| Admin | Account Action | Account Freeze, Chargeback Processor, Wire Recall | Account Registry, Compliance Records |
| Report | SAR/Compliance | SAR Generator, Audit Compiler, Regulatory Submission | SAR Archive, Audit Log |

**Key risk:** Financial irreversibility (mass account freeze), regulatory exposure (SAR filing has legal consequences).

### Legal (Adapter)

Case management and legal research.

| Phase | Agent | Tools | Memory |
|-------|-------|-------|--------|
| Monitor | Case Intake | Docket Search, Deadline Tracker, Conflict Checker, Client Portal | Case Registry, Deadline DB |
| Analyze | Research | Case Law DB, Statute Search, Contract Analyzer | Precedent Library, Research Memos |
| Admin | Filing/Action | Court Filing, Document Signing, Payment Processing | Filing Records, Client Trust Account |
| Report | Client Reporting | Memo Generator, Billing System, Matter Close | Billing Archive, Matter Archive |

**Key risk:** Attorney-client privilege (cross-phase leakage destroys privilege), court filings are irreversible and public.

### Cross-Domain Attack Matrix

| Attack Pattern | CyberOps | Healthcare | Finance | Legal |
|---------------|----------|------------|---------|-------|
| Tool Redirection | Monitor → IAM/PAM | Triage → Prescription Writer | Surveillance → Account Freeze | Research → Court Filing |
| Memory Poisoning | Falsified RCA → Threat Repo | Poisoned labs → Patient Records | Falsified fraud → Case History | Poisoned case law → Research Memos |
| Data Exfiltration | Raw forensics → MISP | PHI → Quality Metrics | — | Privileged comms → Billing |
| Bulk Irreversible | Mass credential revocation | — | Mass account freeze | — |

---

## Configurations

Three system configurations applied identically across all domains:

### Flat MAS (Baseline)

- All agents access all tools and memory stores
- No manifest enforcement, consensus, or MMA
- Peer-to-peer agent communication

### ACL-Hardened MAS

- Same phase-to-tool restrictions as AgenticCyOps
- Enforcement via network-level ACLs (HTTP 403)
- No signed manifests, consensus, write-boundary filtering, or MMA
- Tests whether simple access control suffices (it doesn't — semantic attacks bypass ACLs)

### AgenticCyOps

- **P1 (Authorized Interface):** Signed manifests, admin-approved tool catalog
- **P2 (Capability Scoping):** Phase-to-tool restriction at Host routing layer
- **P3 (Verified Execution):** Multi-model consensus (≥2/3) before irreversible actions
- **P4 (Memory Integrity):** Write-boundary filtering + versioned ledger
- **P5 (Access Control):** MMA-mediated memory with phase-partitioned policies
- Host-mediated sequential handoffs

---

## Running Experiments

### Prerequisites

1. At least Primary vLLM server (port 8000) running
2. ChromaDB initialized for target domain(s)
3. `.env` has valid API keys
4. Benign E2E test passes for target domain

### CyberOps (Full Depth — Eval A)

```bash
# Recommended: use the evaluation script (auto charts + PDF report)
bash scripts/run_eval_a.sh

# Or run manually: all 6 APs × 3 configs × 30 trials
python -m attacks.harness --domain cyberops --eval A --config all --trials 30

# Single AP
python -m attacks.harness --domain cyberops --ap ap1 --config agenticcyops --trials 30

# Benign baseline
python -m attacks.harness --domain cyberops --benign --config all --trials 20
```

### Multi-Domain (Eval F)

```bash
# Recommended: use the evaluation script (auto charts + PDF report)
bash scripts/run_eval_f.sh

# Or run manually: all 3 adapter domains
for domain in healthcare finance legal; do
  python -m attacks.harness --domain $domain --eval F --config all --trials 10
done
```

### Baseline Verification

```bash
# Interactive domain selection menu
bash scripts/run_baseline.sh
```

### TAMAS Benchmark (Eval D)

```bash
cd benchmarks/tamas && bash setup.sh
python run_baseline.py      # Flat + GPT-4o
python run_defended.py      # AgenticCyOps + Qwen3
python compare.py
```

### Ablation + Cross-Domain Spot Check

```bash
# CyberOps ablation
python -m ablation.run_ablation --domain cyberops --all --trials 30

# Finance cross-domain spot check (P2 ablation)
python -m ablation.run_ablation --domain finance --principle P2 --ap ap1 --trials 30
```

### Validator Diversity

```bash
python -m ablation.validator_diversity --trials 30
```

### GLM-4.7 Diversity Check

```bash
# Swap Primary for GLM-4.7, then:
python -m attacks.harness --domain cyberops --ap ap1 --config agenticcyops \
  --trials 30 --model-url http://localhost:8001/v1
```

### Trust Boundary Analysis (All Domains)

```bash
python -m benchmarks.boundary.classify_boundaries --domain cyberops
python -m benchmarks.boundary.classify_boundaries --domain healthcare
python -m benchmarks.boundary.classify_boundaries --domain finance
python -m benchmarks.boundary.classify_boundaries --domain legal
python -m benchmarks.boundary.sensitivity
python -m benchmarks.boundary.stress_test --domain cyberops --config agenticcyops
```

### Full Evaluation Suite

```bash
# Everything (~1,925 runs, several hours)
# CyberOps depth
python -m attacks.harness --domain cyberops --eval A --config all --trials 30
# Multi-domain
for domain in healthcare finance legal; do
  python -m attacks.harness --domain $domain --eval F --config all --trials 10
done
# TAMAS
cd benchmarks/tamas && python run_baseline.py && python run_defended.py && python compare.py && cd ../..
# Ablation
python -m ablation.run_ablation --domain cyberops --all --trials 30
python -m ablation.run_ablation --domain finance --principle P2 --ap ap1 --trials 30
# Validator diversity
python -m ablation.validator_diversity --trials 30
# Memory poisoning
python -m attacks.harness --domain cyberops --eval C --poison-rates 0.05 0.10 0.20 --trials 10
```

---

## Analysis & Reproducing Results

### Generate Result Tables

```bash
# Parse all logs and compute metrics
python -m analysis.compute_metrics --input logs/ --output results/tables/

# Run statistical tests (McNemar's, CIs, chi-squared homogeneity for cross-domain)
python -m analysis.statistical_tests --input results/tables/

# Generate all tables (R1–R11)
python -m analysis.generate_tables --input results/tables/ --output results/tables/
```

### Generate Figures

```bash
python -m analysis.generate_figures --input results/tables/ --output results/figures/

# Or interactive
jupyter notebook analysis/results_explorer.ipynb
```

### Expected Results

| File | Content |
|------|---------|
| `R1_attack_interception.csv` | CyberOps ASR per AP per config (6 APs × 3 configs) |
| `R2_boundary_reduction.csv` | Unweighted + weighted reduction (CyberOps) |
| `R3_tamas_benchmark.csv` | ASR/TSR/ERS (flat GPT-4o vs defended Qwen3) |
| `R4_ablation.csv` | ASR with each principle removed + cross-domain spot check |
| `R5_consensus_latency.csv` | Per-loop latency statistics |
| `R6_benign_completion.csv` | Completion rates across all 4 domains |
| `R7_validator_diversity.csv` | Consensus failure by validator config |
| `R8_memory_poisoning.csv` | Propagation rate by poisoning rate |
| `R9_glm_diversity.csv` | Qwen3 vs GLM-4.7 comparison |
| **`R10_cross_domain_interception.csv`** | **ASR across 4 domains with "Code Changes: 0" column** |
| `R11_cross_domain_boundaries.csv` | Boundary reduction across 4 domains |

---

## Reducing Experiment Scope

| Reduction | Impact | How |
|-----------|--------|-----|
| Fewer trials | Wider CIs | `--trials 10` instead of `--trials 30` |
| Fewer APs | Incomplete coverage | `--ap 1 2 3 4` (skip AP-5, AP-6) |
| Skip adapter domains | No cross-domain proof | Skip `--domain healthcare/finance/legal` |
| Skip GLM-4.7 | No model-independence | Skip diversity runs |
| Skip TAMAS | No independent benchmark | Skip `benchmarks/tamas/` |
| API validators only | No local V1-V3 | Set all to GPT-4o in `validators.yaml` |
| 2-GPU setup | Single model only | Use API providers for everything else |

Minimum viable: CyberOps Eval A (AP-1–4) + Eval B + Ablation = ~500 runs, single model.

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| vLLM OOM | Reduce `--gpu-memory-utilization` or run validators sequentially |
| DeepSeek-R1 load error | Requires vLLM nightly |
| GLM-4.7 FP8 error | Verify vLLM nightly supports FP8; check model path |
| GPT-4o rate limit | Tenacity retry built in; or fallback to local_only consensus config |
| ChromaDB slow | Run embedding on GPU: `CUDA_VISIBLE_DEVICES=3 python -m memory.chromadb_setup` |
| TAMAS conflicts | Run in separate virtualenv |
| Domain adapter fails | Verify manifests load: `python -m host.manifest_enforcer --domain healthcare --test` |
| Benign E2E fails | Check vLLM servers: `curl http://localhost:800X/v1/models` |
| Cross-domain inconsistency | Interesting result — analyze and report domain-specific LLM biases |

---

## Logging & Instrumentation

All inter-component calls logged via `logging_utils/json_logger.py`. One JSON line per event.

### Usage

```python
from logging_utils import ExperimentLogger

logger = ExperimentLogger(
    eval_name="eval_f", 
    domain="healthcare",
    config="agenticcyops", 
    model="Qwen3-235B"
)
logger.set_trial("ap1", variant=3, trial=5)

with logger.track("triage_agent", "H8_prescription_writer", "tool_call") as event:
    result = call_tool(...)
    event.set_auth("deny", "P2_capability_scoping")
```

### Log Format

```json
{
  "timestamp": "2026-04-08T14:30:22.451Z",
  "trial_id": "healthcare_ap1_v3_t5_agenticcyops",
  "domain": "healthcare",
  "eval": "eval_f",
  "config": "agenticcyops",
  "model": "Qwen3-235B-A22B-Instruct-2507",
  "source": "triage_agent",
  "destination": "H8_prescription_writer",
  "action": "tool_call",
  "payload_hash": "b4e2c9d1",
  "auth_decision": "deny",
  "mechanism": "P2_capability_scoping",
  "interception_step": 2,
  "latency_ms": 287,
  "tokens_prompt": 1100,
  "tokens_completion": 520
}
```

---

## Citation

```bibtex
@misc{mitra2025agenticcyops,
  title         = {AgenticCyOps: Securing Multi-Agentic AI Integration 
                   in Enterprise Cyber Operations},
  author        = {Mitra, Shaswata and Patel, Raj and Mittal, Sudip and 
                   Rahman, Md Rayhanur and Rahimi, Shahram},
  year          = {2025},
  eprint        = {2603.09134},
  archiveprefix = {arXiv},
  primaryclass  = {cs.CR},
  url           = {https://arxiv.org/abs/2603.09134}
}
```

---

## License

This testbed is released for research purposes. See [LICENSE](LICENSE) for details.

Model licenses:
- Qwen3, Qwen3-Embedding: Apache 2.0
- GLM-4.7: Apache 2.0
- DeepSeek-R1-Distill-Qwen-32B: MIT License
- Mistral-Small: Apache 2.0
- Llama-4-Scout: Llama Community License

---

## Acknowledgments

This research was carried out in the PATENT Lab, Department of Computer Science, The University of Alabama. The testbed was developed and evaluated on university GPU infrastructure (6× NVIDIA H200).