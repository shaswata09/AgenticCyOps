# AgenticCyOps — 10-Day Experiment Execution Checklist

> **Goal:** Empirical results across 4 enterprise domains + TAMAS for CAIS 2026 rebuttal.  
> **Team:** 3 researchers (A, B, C) working in parallel.  
> **Priority:** Eval A (CyberOps depth) > Eval F (multi-domain) > Eval D (TAMAS) > B > Ablation + Validator Diversity > E > C  
> **Hardware:** 6× H200, all BF16 (GLM-4.7 uses FP8 quantization)  
> **API Budget:** ~$70 (GPT-4o ~$50, Claude Sonnet ~$20)  
> **Target:** ~1,900 instrumented runs, 4 domains, 6 attack paths, 3 configs, 7 model families, zero framework code changes across domains

---

## Model Reference

| Role | Model | Family | GPU | Port |
|------|-------|--------|-----|------|
| Primary agents + Host | Qwen3-235B-A22B-Instruct-2507 | Qwen | 0,1,4,5 TP=4 | 8000 |
| Diversity agents | GLM-4.7 | GLM (Zhipu) | 0,1,4,5 TP=4 FP8 (swap with Primary) | 8001 |
| Validator V1 | Qwen3-32B | Qwen | 2 | 8002 |
| Validator V2 | DeepSeek-R1-Distill-Qwen-32B | DeepSeek | 2 (swap with V1) | 8005 |
| Validator V3 | Llama-4-Scout-17B-16E | Meta | 4,5 TP=2 | 8004 |
| Validator V4 | Claude Sonnet | Anthropic | API | — |
| Validator V5 (optional) | Mistral-Small-3.2-24B | Mistral | 3 | 8003 |
| Embedding | Qwen3-Embedding-0.6B | Qwen | CPU | — |
| TAMAS baseline | GPT-4o | OpenAI | API | — |

---

## Phase 0: Environment Setup (Day 1)

### 0.1 Environment
- [ ] GitHub repo created
- [ ] Conda env `agenticcyops` active, `./install.sh` complete
- [ ] `.env` configured (ANTHROPIC_API_KEY, OPENAI_API_KEY, HF_TOKEN)
- [ ] All local models verified in `/storage/data/models/`
- [x] Structured JSON logger ready (`logging_utils/json_logger.py`)
  - Includes `domain` field in every event (cyberops, healthcare, finance, legal)

### 0.2 vLLM Servers (start as needed)
- [ ] Primary (GPU 0,1,4,5 TP=4, port 8000):
  ```bash
  CUDA_VISIBLE_DEVICES=0,1,4,5 vllm serve /storage/data/models/Qwen/Qwen3-235B-A22B-Instruct-2507 \
    --tensor-parallel-size 4 --dtype bfloat16 \
    --enable-auto-tool-choice --tool-call-parser hermes \
    --gpu-memory-utilization 0.9 --port 8000
  ```
- [ ] Diversity — GLM-4.7 (swap with Primary):
  ```bash
  CUDA_VISIBLE_DEVICES=0,1,4,5 vllm serve /storage/data/models/THUDM/GLM-4.7 \
    --tensor-parallel-size 4 --dtype float16 --quantization fp8 \
    --enable-auto-tool-choice --tool-call-parser hermes \
    --gpu-memory-utilization 0.9 --port 8001
  ```
- [ ] V1 Qwen3-32B (GPU 2, port 8002)
- [ ] V2 DeepSeek-R1 (GPU 2 swap, port 8005)
- [ ] V3 Llama-4-Scout (GPU 4,5 TP=2, port 8004)
- [ ] V5 Mistral-Small (GPU 3, port 8003)
- [ ] V4 Claude Sonnet — API, always available
- [ ] Verify + create `start_servers.sh`

### 0.3 Project Structure
- [ ] Core (domain-agnostic): host/, agents/, memory/, consensus/, attacks/, analysis/
- [ ] Domain configs:
  ```
  domains/
  ├── cyberops/
  │   ├── configs/        # 4 manifests
  │   ├── tools/          # 16 MCP stubs
  │   ├── seed_data/      # 12 collection seeds
  │   ├── prompts/        # 4 agent system prompts
  │   └── payloads/       # 6 APs × 5 variants + benign
  ├── healthcare/
  │   ├── configs/        # 4 manifests
  │   ├── tools/          # 13 tool stubs (~20 lines each)
  │   ├── seed_data/      # 8 collection seeds (10-20 entries each)
  │   ├── prompts/        # 4 agent system prompts
  │   └── payloads/       # 3 APs × 5 variants + benign
  ├── finance/
  │   └── (same structure as healthcare)
  └── legal/
      └── (same structure as healthcare)
  ```

---

## Phase 1: Core Framework (Days 1–2)

**Everything here is domain-agnostic. Domain content goes in `domains/`.**

### 1.1 Tool Server Template + CyberOps Tools — **A**
- [ ] `mcp_servers/base_server.py`: generic FastAPI + MCP template
  - Takes: tool name, description, input schema, response function
  - Auto-provides: `/state`, `/reset`, `/health` endpoints
  - Logs all calls via structured JSON logger
- [ ] Build CyberOps tools (T1–T16) using template → `domains/cyberops/tools/`
- [ ] Verify: all 16 respond to MCP calls

### 1.2 Memory Layer — **B**
- [ ] `memory/chromadb_setup.py`: takes domain config → creates collections + seeds
  - Domain-agnostic: reads collection names and seed files from `domains/{domain}/`
- [ ] `memory/mma_gateway.py`: reads access policy from `domains/{domain}/configs/access_policy.json`
- [ ] `memory/write_filter.py`: cosine similarity via Qwen3-Embedding-0.6B
- [ ] Seed CyberOps collections (M1–M12, 30–50 entries each)
- [ ] Verified: access control + write rejection working

### 1.3 Manifests + Enforcer — **C**
- [ ] CyberOps manifests → `domains/cyberops/configs/`
- [ ] `host/manifest_enforcer.py`: reads manifests from any `domains/{domain}/configs/`
- [ ] `validate_action(agent_phase, tool_id) → bool`

### 1.4 Host Orchestrator — **A** (after 1.1)
- [ ] `host/orchestrator.py`: domain-agnostic LangGraph Host
  - Takes `--domain cyberops` to load correct configs/tools/prompts
  - CoT → phase routing → manifest enforcement → handoffs
  - **Zero code changes** when domain switches — only config path changes

### 1.5 Phase Agents — **B** (after 1.2)
- [ ] `agents/base_agent.py`: domain-agnostic agent class
  - System prompt loaded from `domains/{domain}/prompts/{phase}.txt`
  - Tool schemas loaded from domain manifest
  - LLM client switchable (Qwen3 primary, GLM-4.7 diversity)
- [ ] CyberOps system prompts → `domains/cyberops/prompts/`

### 1.6 Consensus Module — **C** (after 1.3)
- [ ] `consensus/validator.py`: domain-agnostic ConsensusValidator
  - Default: V1 (Qwen3-32B) + V2 (DeepSeek-R1) + V4 (Claude)
  - Configurable for diversity experiments
- [ ] Wired into Admin Recovery Loop + Report Improvement Loop
- [ ] Instrumented: per-validator decision, latency, tokens

---

## Phase 2: CyberOps Pipeline + Configs (Day 3)

### 2.1 Flat MAS — **A**
- [ ] All agents → all tools, all stores, peer-to-peer
- [ ] Verified: Monitor calls T8 ✓, any agent writes any store ✓

### 2.2 ACL-Hardened — **B**
- [ ] Phase restrictions, no consensus/manifests/MMA/filtering
- [ ] Verified: Monitor → T8 returns 403 ✓

### 2.3 AgenticCyOps — **C**
- [ ] Full: Host + manifests + consensus + MMA
- [ ] Verified: benign E2E ✓, all 5 principles logging ✓

---

## Phase 3: Attack Scripts + Domain Adapters (Days 3–4)

### 3.1 Attack Harness — **B**
- [ ] `attacks/harness.py`: domain-agnostic
  - Takes: `--domain cyberops --ap ap1 --config agenticcyops --trials 30`
  - Loads payloads from `domains/{domain}/payloads/`
  - Logs to `logs/{domain}_{eval}/`

### 3.2–3.8 CyberOps Attack Scripts — **A + B**
- [ ] AP-1: Tool Redirection (5 variants) — **B**
- [ ] AP-2: Memory Poisoning (5 variants) — **C**
- [ ] AP-3: Confused Deputy (5 variants) — **A**
- [ ] AP-4: Cross-Phase Exfiltration (5 variants) — **B**
- [ ] AP-5: Unauthorized Irreversible Action (5 variants) — **A**
- [ ] AP-6: Replay Attack (5 variants) — **C**
- [ ] Benign: 20 scenarios — **C**
- [ ] All payloads → `domains/cyberops/payloads/`

### 3.9 Healthcare Adapter — **C** (Day 4)
- [ ] 4 manifests → `domains/healthcare/configs/`
  - Monitor: H1-H4 (EHR, Vitals, Lab Results, Triage Scoring)
  - Analyze: H5-H7 (Imaging, Drug Interaction, Clinical Guidelines)
  - Admin: H8-H10 (Prescription Writer, Procedure Scheduler, Insurance Pre-Auth)
  - Report: H11-H13 (Discharge Summary, Regulatory Filing, Quality Metrics)
- [ ] 13 tool stubs → `domains/healthcare/tools/` (~20 lines each from base template)
- [ ] 8 memory collections (HM1–HM8), 10–20 seed entries each
- [ ] 4 system prompts → `domains/healthcare/prompts/`
- [ ] Access policy JSON → `domains/healthcare/configs/access_policy.json`
- [ ] Attack payloads (3 APs × 5 variants):
  - [ ] AP-1 analogue: Triage agent tricked into writing prescriptions (H8)
  - [ ] AP-2 analogue: Poisoned lab results → wrong diagnosis in patient records
  - [ ] AP-4 analogue: Compliance agent exfiltrates PHI into quality metrics
- [ ] 5 benign clinical workflows
- [ ] **Verify:** run one benign E2E through healthcare AgenticCyOps config

### 3.10 Finance Adapter — **C** (Day 4)
- [ ] 4 manifests → `domains/finance/configs/`
  - Monitor: F1-F4 (Transaction Stream, Rule Engine, Customer Profile, Alert Queue)
  - Analyze: F5-F7 (Graph Analysis, External Fraud DB, Document Verification)
  - Admin: F8-F10 (Account Freeze, Chargeback Processor, Wire Recall)
  - Report: F11-F13 (SAR Generator, Audit Compiler, Regulatory Submission)
- [ ] 13 tool stubs, 8 memory collections, 4 system prompts, access policy
- [ ] Attack payloads:
  - [ ] AP-1 analogue: Surveillance agent tricked into freezing accounts (F8)
  - [ ] AP-2 analogue: Falsified fraud determination poisons case history
  - [ ] AP-5 analogue: Account action agent proposes mass account freezes
- [ ] 5 benign fraud investigation workflows
- [ ] **Verify:** one benign E2E

### 3.11 Legal Adapter — **C** (Day 4)
- [ ] 4 manifests → `domains/legal/configs/`
  - Monitor: L1-L4 (Docket Search, Deadline Tracker, Conflict Checker, Client Portal)
  - Analyze: L5-L7 (Case Law DB, Statute Search, Contract Analyzer)
  - Admin: L8-L10 (Court Filing, Document Signing, Payment Processing)
  - Report: L11-L13 (Client Memo Generator, Billing System, Matter Close)
- [ ] 13 tool stubs, 8 memory collections, 4 system prompts, access policy
- [ ] Attack payloads:
  - [ ] AP-1 analogue: Research agent tricked into filing court documents (L8)
  - [ ] AP-2 analogue: Poisoned case law → wrong legal analysis in research memos
  - [ ] AP-4 analogue: Client reporting agent exfiltrates privileged comms into billing
- [ ] 5 benign case management workflows
- [ ] **Verify:** one benign E2E

**Adapter build time estimate:** ~4 hours per domain. Person C builds all 3 on Day 4 while A+B finish CyberOps attack scripts.

---

## Phase 4: Run Eval A — CyberOps Attack Paths (Days 5–6)

### 4.1 Execution — **A + B**
- [ ] AP-1: 90 runs ✓
- [ ] AP-2: 90 runs ✓
- [ ] AP-3: 90 runs ✓
- [ ] AP-4: 90 runs ✓
- [ ] AP-5: 90 runs ✓
- [ ] AP-6: 90 runs ✓
- [ ] Benign: 60 runs ✓
- [ ] **Total CyberOps: 600 runs** (Qwen3-235B, temp 0.0)

### 4.2 Run Eval F — Multi-Domain (Day 6) — **C**

Same framework code, swap domain config:

```bash
# Healthcare
python -m attacks.harness --domain healthcare --ap ap1_health --config all --trials 10
python -m attacks.harness --domain healthcare --ap ap2_health --config all --trials 10
python -m attacks.harness --domain healthcare --ap ap4_health --config all --trials 10
python -m attacks.harness --domain healthcare --benign --config all --trials 5

# Finance
python -m attacks.harness --domain finance --ap ap1_finance --config all --trials 10
python -m attacks.harness --domain finance --ap ap2_finance --config all --trials 10
python -m attacks.harness --domain finance --ap ap5_finance --config all --trials 10
python -m attacks.harness --domain finance --benign --config all --trials 5

# Legal
python -m attacks.harness --domain legal --ap ap1_legal --config all --trials 10
python -m attacks.harness --domain legal --ap ap2_legal --config all --trials 10
python -m attacks.harness --domain legal --ap ap4_legal --config all --trials 10
python -m attacks.harness --domain legal --benign --config all --trials 5
```

- [ ] Healthcare: 3 APs × 10 trials × 3 configs + 15 benign = **105 runs** ✓
- [ ] Finance: 3 APs × 10 trials × 3 configs + 15 benign = **105 runs** ✓
- [ ] Legal: 3 APs × 10 trials × 3 configs + 15 benign = **105 runs** ✓
- [ ] **Total Eval F: 315 runs**
- [ ] **Key verification:** confirm zero code changes — only `--domain` flag differs

### 4.3 GLM-4.7 Diversity Check — **A** (Day 7)
- [ ] Shut down Primary, start GLM-4.7 on same GPUs
- [ ] AP-1 CyberOps: 30 trials, AgenticCyOps
- [ ] Compare interception: Qwen3 vs GLM-4.7

### 4.4 Extract Latency (Eval E) — **C**
- [ ] From logs: E2E latency, per-loop latency, tokens, cost
- [ ] mean, median, p95, p99 per loop per config

### 4.5 Preliminary Check — **All**
- [ ] ASR per AP per config (CyberOps)
- [ ] ASR per AP analogue per config (Healthcare, Finance, Legal)
- [ ] **Cross-domain consistency check:** are interception rates similar across domains?
- [ ] If interception < 80% in any domain: diagnose
- [ ] Document engineering challenges

---

## Phase 5: Eval B — Weighted Trust Boundaries (Day 5, parallel)

### 5.1 Classification — **C** (CyberOps)
- [ ] 200 boundaries: privilege × criticality → `boundary_weights.csv`

### 5.2 Cross-Domain Boundary Computation — **C**
- [ ] Enumerate boundaries per adapter domain:
  | Domain | Tools | Memory | Flat Boundaries | AgenticCyOps | Reduction |
  |--------|-------|--------|----------------|-------------|-----------|
  | CyberOps | 16 | 12 | 200 | 56 | 72% |
  | Healthcare | 13 | 8 | ~120 | ~34 | ~72% |
  | Finance | 13 | 8 | ~120 | ~34 | ~72% |
  | Legal | 13 | 8 | ~120 | ~34 | ~72% |
- [ ] Confirm: reduction ratio is consistent across domains

### 5.3 Weighted Reduction (CyberOps) — **C**
- [ ] Compute Flat, ACL-Hardened, AgenticCyOps
- [ ] Sensitivity: Execute weight = 3, 5, 10
- [ ] Table + bar chart

### 5.4 Stress Test — **C**
- [ ] 56 retained CyberOps boundaries × 1 malformed payload
- [ ] Active verification coverage

---

## Phase 6: Eval D — TAMAS (Days 5–7, parallel)

### 6.1 Setup — **A**
- [ ] Clone TAMAS, install, verify default run
- [ ] Map TAMAS attack types → P1–P5 defenses

### 6.2 GPT-4o Baseline — **A**
- [ ] Flat AutoGen + GPT-4o → ASR, TSR, ERS

### 6.3 AgenticCyOps Defended — **A**
- [ ] Wrap TAMAS agents with P1–P5:
  - [ ] P1: tool identity validation before invocation
  - [ ] P2: restrict each agent to assigned tools
  - [ ] P3: consensus vote before tool execution
  - [ ] P4: filter agent outputs before passing downstream
  - [ ] P5: partition shared context per agent scope
- [ ] Run with Qwen3-235B → ASR, TSR, ERS
- [ ] **Day 6 decision point:** if >50% incomplete, run as-is with caveat

### 6.4 Results — **A**
- [ ] Comparison table + McNemar's
- [ ] Narrative: "same P1–P5 wrappers applied to generic TAMAS agents — zero domain-specific modification"

---

## Phase 7: Ablation + Validator Diversity (Days 7–8)

### 7.1 Ablation (CyberOps) — **B**
- [ ] Remove P1 → AP-3 (30 trials)
- [ ] Remove P2 → AP-1 + AP-5 (60 trials)
- [ ] Remove P3 → AP-3 + AP-5 + AP-6 (90 trials)
- [ ] Remove P4 → AP-2 + AP-6 (60 trials)
- [ ] Remove P5 → AP-4 (30 trials)
- [ ] **Total: 270 runs**

### 7.2 Cross-Domain Ablation Spot Check — **B**
- [ ] Remove P2 on Finance AP-1 analogue: 30 trials
- [ ] Compare with CyberOps P2 ablation result
- [ ] **Purpose:** confirm ablation results transfer across domains
- [ ] **Total: 30 runs**

### 7.3 Validator Diversity — **B**
- [ ] Same-family: 3× Qwen3-32B → AP-1, 30 trials
- [ ] Default diverse: V1 + V2 + V4 (Qwen, DeepSeek, Anthropic) → AP-1, 30 trials
- [ ] All-local diverse: V1 + V2 + V3 (Qwen, DeepSeek, Meta) → AP-1, 30 trials
- [ ] **Total: 90 runs**

### 7.4 Results — **B**
- [ ] Ablation table: principle × AP × ASR (full vs ablated)
- [ ] Cross-domain ablation: CyberOps P2 result vs Finance P2 result (should match)
- [ ] Validator table: config × consensus failure rate × families

---

## Phase 8: Eval C (Day 8)

### 8.1 Memory Poisoning (CyberOps) — **C**
- [ ] 3 rates × 3 configs × 10 workflows = 90 runs
- [ ] Propagation + write rejection table

---

## Phase 9: Analysis & Rebuttal (Days 9–10)

### 9.1 Results Tables — **A**

- [ ] **R1: CyberOps Attack Interception**
  | AP | Flat | ACL-Hard | AgenticCyOps | Step | Mechanism |
  (6 rows: AP-1 through AP-6)

- [ ] **R2: Weighted Boundary Reduction**
  | Config | Boundaries | Unweighted | Weighted |
  (CyberOps, 3 rows)

- [ ] **R3: TAMAS Benchmark**
  | Attack Type | Flat ASR (GPT-4o) | Defended ASR (Qwen3) | ERS Flat | ERS Ours |

- [ ] **R4: Ablation**
  | Principle | AP(s) | Full ASR | Ablated ASR | Δ |
  (5 rows + 1 cross-domain spot check)

- [ ] **R5: Consensus Latency**
  | Loop | Mean ms | Median | P95 | Tokens |

- [ ] **R6: Benign Completion (All Domains)**
  | Config | CyberOps | Healthcare | Finance | Legal |

- [ ] **R7: Validator Diversity**
  | Config | Consensus Failure % | Families |

- [ ] **R8: Memory Poisoning**
  | Rate | Flat | ACL-Hard | AgenticCyOps | Write Rejection % |

- [ ] **R9: GLM-4.7 Diversity**
  | AP-1 | Qwen3 Interception | GLM-4.7 Interception |

- [ ] **R10: Cross-Domain Attack Interception (HEADLINE TABLE)**
  | Attack Pattern | CyberOps | Healthcare | Finance | Legal | Code Changes |
  |---------------|----------|------------|---------|-------|-------------|
  | Tool Redirection (AP-1) | ?/30 | ?/10 | ?/10 | ?/10 | 0 |
  | Memory Poisoning (AP-2) | ?/30 | ?/10 | ?/10 | ?/10 | 0 |
  | Exfil / Bulk Action | ?/30 | ?/10 | ?/10 | ?/10 | 0 |
  | Benign Completion | ?% | ?% | ?% | ?% | 0 |
  | **Principle Modifications** | **—** | **None** | **None** | **None** | **—** |

- [ ] **R11: Cross-Domain Boundary Reduction**
  | Domain | Tools | Memory | Flat | AgenticCyOps | Reduction |

### 9.2 Figures — **B**
- [ ] Bar chart: ASR by AP by config (3 bars × 6 APs, CyberOps)
- [ ] **Bar chart: Cross-domain ASR comparison (4 grouped bars per AP analogue)**
- [ ] Bar chart: Weighted vs unweighted boundary reduction
- [ ] Heatmap: Ablation (5 principles × relevant APs)
- [ ] Bar chart: Validator diversity
- [ ] If C done: propagation vs poisoning rate

### 9.3 Stats — **C**
- [ ] McNemar's: Flat vs AgenticCyOps, ACL vs AgenticCyOps (per AP, CyberOps)
- [ ] Chi-squared test for homogeneity: cross-domain ASR consistency
- [ ] 95% CIs on all rates
- [ ] Latency: mean ± std

### 9.4 Write Rebuttal — **All**

**Opening:**
- [ ] "The submitted paper deliberately scoped its contribution to the architectural level — the attack surface decomposition and defensive principle derivation constitute the primary novelty. Here we present empirical validation from our evaluation testbed: ~1,900 instrumented trial runs across **four enterprise domains** (cybersecurity operations, healthcare, financial fraud detection, legal case management), six attack scenarios, three configurations, and seven model families (Qwen, GLM, DeepSeek, Meta, Mistral, Anthropic, OpenAI). The five defensive principles require **zero framework code changes** across domains — only configuration files and tool stubs differ."

**R10 (Cross-Domain) first** — this is the headline table, not R1.

**Per-reviewer responses:**

- [ ] **All (implementation):** testbed scale, R10 (cross-domain), R1 (CyberOps depth), R6 (benign), R4 (ablation)
- [ ] **197A (novelty + generalizability):**
  - "Identical Host orchestrator, consensus module, and memory management agent deployed across four enterprise verticals with zero code modification — R10 confirms consistent interception"
  - ACL-Hardened comparison: "network ACLs fail against semantic attacks across all domains"
  - Ablation: "principle necessity confirmed in CyberOps and cross-validated in finance (R4)"
  - "We additionally validate against the domain-agnostic TAMAS benchmark (R3)"
- [ ] **197B (boundaries + validators):**
  - R2 weighted + R11 cross-domain boundaries (consistent reduction ratio)
  - R7 diversity: "diverse validators reduce consensus failure by X%"
  - R5 latency: overhead is acceptable
- [ ] **197C (empirical + TAMAS + baseline):**
  - R3 TAMAS: "P1–P5 wrappers on generic TAMAS agents — zero domain-specific logic"
  - ACL-Hardened across all 4 domains
  - R8 memory poisoning

**AP-5/AP-6 talking points:**
- [ ] "AP-5 validates human escalation: X% of irreversible bulk actions correctly escalated"
- [ ] "AP-6 demonstrates temporal integrity: versioned ledger detected X% of replay attempts"

**Multi-domain talking points:**
- [ ] "The 'Code Changes: 0' column in R10 is the empirical proof of our architectural claim — the same five principles secure tool orchestration and memory management regardless of whether the tools are firewalls, MRI scanners, or court filing systems"
- [ ] "Cross-domain ablation spot check confirms principle necessity transfers: removing P2 in the finance domain produces the same degradation pattern as in CyberOps"

**Extended evaluation note:**
- [ ] "We present representative results across four domains. Our extended evaluation includes validator integrity under Byzantine conditions, production-tool integration, and additional domain verticals. The complete testbed will be released as open-source upon acceptance."

**Limitations (honest):**
- [ ] AP-4 partial block
- [ ] Any TAMAS gaps
- [ ] Consensus latency tradeoff
- [ ] Mock tools vs production tools
- [ ] Adapter domains use fewer trials (10 vs 30) — wider CIs

**Close:**
- [ ] "The testbed, all domain adapters, and experimental data will be released as open-source upon acceptance."

### 9.5 Final Review — **All**
- [ ] Numbers match raw logs
- [ ] Zero reactive language
- [ ] Scale visible: "~1,900 runs", "4 domains", "7 model families", "zero code changes"
- [ ] R10 is front and center — it's the single most persuasive element
- [ ] Cross-domain consistency emphasized over individual domain depth
- [ ] Check venue word limit
- [ ] Submit

---

## Run Count Summary

| Evaluation | Runs | Domains |
|-----------|------|---------|
| A: CyberOps (6 APs + benign) | 600 | CyberOps |
| F: Multi-Domain (3 APs + benign × 3 domains) | 315 | Healthcare, Finance, Legal |
| D: TAMAS | ~400 | Generic (5 scenarios) |
| B: Trust Boundaries | Analytical | All 4 |
| Ablation (CyberOps) | 270 | CyberOps |
| Ablation spot check (Finance) | 30 | Finance |
| Validator Diversity | 90 | CyberOps |
| GLM-4.7 Diversity | 30 | CyberOps |
| E: Consensus Overhead | From A logs | CyberOps |
| C: Memory Poisoning | 90 | CyberOps |
| **Total** | **~1,925** | **4 domains + TAMAS** |

---

## Daily Schedule

| Day | Person A | Person B | Person C |
|-----|----------|----------|----------|
| **1** | 0.1–0.2 Env + vLLM + 1.1 (T1–T8 stubs) | 0.1 Env + 1.2 Memory (domain-agnostic) | 0.3 Structure + 1.3 Manifests + Enforcer |
| **2** | 1.1 (T9–T16) + 1.4 Host (domain-agnostic) | 1.5 Agents (domain-agnostic) + wrapper | 1.6 Consensus (domain-agnostic) |
| **3** | 2.1 Flat + CyberOps E2E | 2.2 ACL-Hardened + 3.1 Harness (domain-agnostic) | 2.3 AgenticCyOps + CyberOps E2E |
| **4** | 3.4 AP-3 + 3.6 AP-5 scripts | 3.2 AP-1 + 3.5 AP-4 scripts | **3.9 Healthcare + 3.10 Finance + 3.11 Legal adapters** |
| **5** | 6.1 TAMAS setup + 6.2 GPT-4o baseline | 4.1 Run CyberOps AP-1, AP-2, AP-5 (270) | 5.1–5.3 Boundaries + cross-domain boundary calc |
| **6** | 6.3 TAMAS defended | 4.1 Run CyberOps AP-3, AP-4, AP-6, benign (330) | **4.2 Run Eval F: Healthcare + Finance + Legal (315)** |
| **7** | 6.4 TAMAS results + 4.3 GLM diversity | 7.1 Ablation P1–P3 (180) | 7.1 Ablation P4–P5 (90) + 4.4 Latency |
| **8** | 4.5 Prelim check (all domains) | 7.2 Cross-domain ablation (30) + 7.3 Validator diversity (90) + 7.4 | 8.1 Memory poisoning (90) |
| **9** | 9.1 Results tables (R1–R11) | 9.2 Figures (incl. cross-domain chart) | 9.3 Stats (incl. chi-squared homogeneity) |
| **10** | 9.4 Rebuttal: responses + R10 headline | 9.4 Rebuttal: tables + multi-domain points | 9.4 Rebuttal: limits + 9.5 Review |

---

## Risk Mitigation

- [ ] **vLLM crash:** `start_servers.sh` with health-check + auto-restart
- [ ] **GPU OOM:** Run validators sequentially (swap on GPU 2)
- [ ] **TAMAS too slow:** Day 6 decision — run as-is with caveat
- [ ] **Mock tools unrealistic:** Use real tool docs (Wazuh, MISP, HL7/FHIR, SWIFT, PACER)
- [ ] **High FP on benign:** Tune validators on benign set (Day 3) first
- [ ] **Null result:** Report honestly
- [ ] **Claude rate limit:** Tenacity retry; fallback to all-local (V1+V2+V3)
- [ ] **AP-5 escalation doesn't trigger:** Check Recovery Loop criticality threshold
- [ ] **AP-6 replay not detected:** Verify ledger hashing includes incident ID + timestamp
- [ ] **Domain adapter breaks:** All use same base_server template — if CyberOps works, adapters work
- [ ] **Cross-domain results inconsistent:** This is actually interesting — report it and analyze why (domain-specific LLM biases)