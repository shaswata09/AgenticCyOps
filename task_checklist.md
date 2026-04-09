# AgenticCyOps — 10-Day Experiment Execution Checklist

> **Goal:** Empirical results across 4 enterprise domains + TAMAS for CAIS 2026 rebuttal.  
> **Team:** 3 researchers (A, B, C) working in parallel.  
> **Priority:** Eval A (CyberOps depth) > Eval F (multi-domain) > Eval D (TAMAS) > B > Ablation + Validator Diversity > E > C  
> **Hardware:** 6× H200, all BF16 (GLM-4.7-FP8 uses official FP8 weights from zai-org/GLM-4.7-FP8)  
> **API Budget:** ~$12 GPT-4o + ~$4 Claude for consensus validation (~$16 total); ~$50 additional if TAMAS included (~$66 total)  
> **Target:** ~1,900 instrumented runs, 4 domains, 6 attack paths, 3 configs, 7 model families, zero framework code changes across domains

---

## Model Reference

| Role | Model | Family | GPU | Port |
|------|-------|--------|-----|------|
| Primary agents + Host | Qwen3-235B-A22B-Instruct-2507 | Qwen | 0,1,4,5 TP=4 | 8000 |
| Diversity agents | GLM-4.7-FP8 | GLM (Zhipu) | 0,1,4,5 TP=4 FP8 (swap with Primary) | 8001 |
| Validator V1 | Qwen3-32B | Qwen | 2 | 8002 |
| Validator V2 | DeepSeek-R1-Distill-Qwen-32B | DeepSeek | 3 | 8005 |
| Validator V3 | Llama-4-Scout-17B-16E | Meta | 4,5 TP=2 | 8004 |
| Validator V4 | Claude Sonnet | Anthropic | API (ANTHROPIC_API_KEY configured) | — |
| Validator V5 (optional) | Mistral-Small-3.2-24B | Mistral | 3 (swap with V2) | 8003 |
| Validator V6 (default) | GPT-4o | OpenAI | API | — |
| Embedding | Qwen3-Embedding-8B | Qwen | CPU/GPU | — |
| Embedding (fast/CPU) | Qwen3-Embedding-0.6B | Qwen | CPU | — |
| TAMAS baseline | GPT-4o | OpenAI | API | — |

---

## Phase 0: Environment Setup (Day 1)

### 0.1 Environment
- [x] GitHub repo created
- [x] Conda env `agenticcyops` active, `./install.sh` complete
- [x] `.env` configured (OPENAI_API_KEY, HF_TOKEN, ANTHROPIC_API_KEY)
- [x] All local models verified in `/models/`
- [x] Structured JSON logger ready (`logging_utils/json_logger.py`)
  - Includes `domain` field in every event (cyberops, healthcare, finance, legal)

### 0.2 vLLM Servers (start as needed via `./start_servers.sh`)
- [x] Primary Qwen3-235B (GPU 0,1,4,5 TP=4, port 8000) — tested, works with `--enforce-eager`
- [x] Diversity GLM-4.7-FP8 (GPU 0,1,4,5 TP=4, port 8001) — uses official FP8 weights (`zai-org/GLM-4.7-FP8`)
- [x] V1 Qwen3-32B (GPU 2, port 8002) — tested, works
- [x] V2 DeepSeek-R1 (GPU 3, port 8005) — tested, works
- [x] V3 Llama-4-Scout (GPU 4,5 TP=2, port 8004) — tested, works with `--enforce-eager`
- [x] V5 Mistral-Small (GPU 3 swap, port 8003) — tested, works
- [x] V4 Claude Sonnet — API (ANTHROPIC_API_KEY configured in .env)
- [x] `start_servers.sh` created with interactive group selection (7 groups: A-G)
- [x] `monitor.sh` created (live GPU/CPU/RAM/server dashboard)
- [x] FlashInfer disabled (CUTLASS JIT broken on H200) — renamed flashinfer package
- [x] All 7 local models downloaded and verified

### 0.3 Project Structure
- [x] Core (domain-agnostic): host/, agents/, consensus/, attacks/, analysis/, mcp_servers/, tests/
  - `host/acl_middleware.py` — HTTP-level ACL for acl_hardened config
- [x] `scripts/` — run_baseline.sh, run_eval_a.sh, run_eval_f.sh
- [x] `models/` — utils (11 files), test_scripts (11 notebooks), download_models.sh
- [x] `logging_utils/` — json_logger.py with ExperimentLogger
- [x] `memory/` — embedding_adapter.py + placeholders (chromadb_setup, mma_gateway, write_filter, access_control, seed_data)
- [x] `config.py` — project base path (no hardcoded paths)
- [x] `domains/` — 4 domains (cyberops, healthcare, finance, legal), each with configs/, tools/, seed_data/, prompts/, payloads/
- [x] `configs/` — flat_config.yaml, acl_config.yaml, agenticcyops_config.yaml, validators.yaml (placeholders)
- [x] `ablation/configs/` — no_p1 through no_p5 yaml placeholders
- [x] `benchmarks/` — tamas/ and boundary/ with placeholder scripts
- [x] `results/` — tables/ and figures/ directories
- [x] `docs/`, `cross_domain/`, `tests/` — all placeholder files created
- [x] All Python packages have `__init__.py`
- [x] All Phase 1+ files have TODO docstrings marking which phase implements them
- [x] Domain configs:
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
- [x] `mcp_servers/base_server.py`: BaseMCPServer with /call, /schema, /state, /reset, /health
- [x] `mcp_servers/server_registry.py`: ServerRegistry with dynamic tool discovery + start/stop
- [x] 16 CyberOps tools built (T1-T16) in `domains/cyberops/tools/{monitor,analyze,admin,report}/`
  - All have INPUT_SCHEMA, async handler, create_server(logger=None)
  - Deterministic responses, observable state tracking
- [x] `domains/cyberops/tools/start_all.py`: launches all 16 on ports 9000-9015
- [x] Verify: all 16 import + create_server OK (runtime verified)

### 1.2 Memory Layer — **B**
- [x] `memory/chromadb_setup.py`: domain-agnostic, reads `memory_collections.json`
- [x] `memory/mma_gateway.py`: FastAPI with /memory/read, /memory/write, /memory/list
  - P5 (AccessController) + P4 (WriteFilter) enforcement
  - Returns 403 for access denied, 422 for write filter rejection
- [x] `memory/access_control.py`: AccessController with can_read/can_write
- [x] `memory/write_filter.py`: cosine similarity, defaults to Qwen3-Embedding-0.6B on CPU
- [x] `memory/embedding_adapter.py`: ChromaEmbeddingAdapter (ChromaDB 1.5.7 compatible)
- [x] `domains/cyberops/configs/memory_collections.json`: 12 collections M1-M12
- [x] `domains/cyberops/configs/access_policy.json`: phase-partitioned permissions
- [x] Seed CyberOps collections (M1-M12, 760 entries total) — `memory/seed_data.py` implemented
  - threat_repository=100, cti_knowledge_base=100, siem_data_lake=75, detection_rules=75, case_management=60, all others=50
  - Semantic coherence verified: legit writes >0.5, junk <0.25, threshold=0.5
- [x] Verified: access control 15/15 tests + write filter legit=0.652/junk=0.150 (runtime verified)

### 1.3 Manifests + Enforcer — **C**
- [x] 4 CyberOps manifests in `domains/cyberops/configs/`
  - monitor: T1-T4, reads M1/M4/M7/M10, no writes, no consensus
  - analyze: T5-T7, reads M1/M2/M6/M7, writes M1/M6, no consensus
  - admin: T8-T12, reads M2/M3/M8/M12, no writes, consensus=true, critical=[T8,T9,T12]
  - report: T13-T16, reads+writes M8/M9/M10/M11, consensus=true
- [x] `host/manifest_enforcer.py`: ManifestEnforcer with validate_tool_call, validate_memory_read/write, requires_consensus, check_bulk_action

### 1.4 Host Orchestrator — **A**
- [x] `host/orchestrator.py`: SOARHost with run_incident, run_phase
  - Supports 3 configs: flat (no enforcement), acl_hardened (P2 only), agenticcyops (P1-P5)
  - Sequential routing: Monitor -> Analyze -> Admin -> Report
  - MMA gateway integration for agenticcyops memory writes
- [x] `host/handoff.py`: PhaseHandoff with create_handoff, get_handoff_summary

### 1.5 Phase Agents — **B**
- [x] `agents/base_agent.py`: BaseAgent + AgentResult + ToolCallProposal
  - Loads prompts from `domains/{domain}/prompts/{phase}.txt`
  - LLM client switchable via switch_model(url)
  - Supports `llm_provider="anthropic"` with Anthropic tool calling (for Groups F, G)
  - OpenAI-compatible tool calling (default, for all local models)
- [x] 4 phase agents: MonitorAgent, AnalyzeAgent, AdminAgent, ReportAgent
- [x] 4 CyberOps prompts in `domains/cyberops/prompts/`

### 1.6 Consensus Module — **C**
- [x] `consensus/validator.py`: ConsensusValidator with validate + validate_with_details
  - Calls validators concurrently (asyncio.gather)
  - Supports OpenAI-compatible (vLLM) and Anthropic validators
- [x] `consensus/recovery_loop.py`: RecoveryLoop (Admin phase, bulk action detection)
- [x] `consensus/improvement_loop.py`: ImprovementLoop (Report phase memory writes)
- [x] `consensus/escalation.py`: EscalationHandler (auto-reject in testbed, logs escalation)
- [x] `configs/validators.yaml`: V1-V6 + 10 consensus configs (default_consensus=V1+V2+V4+V6, t=3/4; full_diversity, all_with_gpt4o, with_mistral, same_family, all_local_diverse, local_only, mixed_with_claude, mixed_with_gpt4o, default_no_claude)
- [x] Per-validator decision, latency, tokens logged via ExperimentLogger

---

## Phase 2: CyberOps Configs + Baseline Verification (Day 3)

### 2.1 Flat MAS — **A**
- [x] All agents → all tools, all stores, peer-to-peer
- [x] Verify: Monitor calls T8 ✓, any agent writes any store ✓
- [x] Run 1 benign incident E2E → completes ✓

### 2.2 ACL-Hardened — **B**
- [x] Phase restrictions, no consensus/manifests/MMA/filtering
- [x] Verify: Monitor → T8 returns 403 ✓
- [x] Verify: Monitor → assigned stores accessible without filtering ✓
- [x] Run 1 benign incident E2E → completes ✓ (ACLs don't break legitimate flow)

### 2.3 AgenticCyOps — **C**
- [x] Full: Host + manifests + consensus + MMA
- [x] Verify: all 5 principles logging ✓
- [x] Verify: consensus approves legitimate Admin action ✓
- [x] Verify: write-filter accepts legitimate memory write ✓
- [x] Run 1 benign incident E2E → completes with zero false blocks ✓
- [x] P4/P5: N/A (no memory ops in benign)

### 2.4 CyberOps Baseline Status
- [x] Flat MAS benign E2E: ✓ PASS
- [x] ACL-Hardened benign E2E: ✓ PASS
- [x] AgenticCyOps benign E2E: ✓ PASS
- [x] **CyberOps ready for attacks: ✓**

---

## Phase 3: Attack Scripts + Domain Adapters (Days 3–4)

### 3.1 Attack Harness — **B**
- [x] `attacks/harness.py`: domain-agnostic attack execution engine with log-based success evaluation
  - Takes: `--domain cyberops --ap ap1 --config agenticcyops --trials 30`
  - Loads payloads from `domains/{domain}/payloads/`
  - Logs to `logs/{domain}_{eval}/`

### 3.2–3.8 CyberOps Attack Scripts — **A + B**
- [x] AP-1: Tool Redirection (5 variants) — **B**
- [x] AP-2: Memory Poisoning (5 variants) — **C**
- [x] AP-3: Confused Deputy (5 variants) — **A**
- [x] AP-4: Cross-Phase Exfiltration (5 variants) — **B**
- [x] AP-5: Unauthorized Irreversible Action (5 variants) — **A**
- [x] AP-6: Replay Attack (5 variants) — **C**
- [x] Benign: 20 scenarios — **C**
- [x] All payloads → `domains/cyberops/payloads/` (6 APs × 5 variants + 20 benign = 50 payloads)

### 3.9 Healthcare Adapter — **C** (Day 4)
- [x] 4 manifests → `domains/healthcare/configs/` (+ memory_collections.json, access_policy.json)
  - Monitor: H1-H4 (EHR, Vitals, Lab Results, Triage Scoring)
  - Analyze: H5-H7 (Imaging, Drug Interaction, Clinical Guidelines)
  - Admin: H8-H10 (Prescription Writer, Procedure Scheduler, Insurance Pre-Auth)
  - Report: H11-H13 (Discharge Summary, Regulatory Filing, Quality Metrics)
- [x] 13 tool stubs → `domains/healthcare/tools/` (H1-H13, organized by phase)
- [x] 8 memory collections (HM1–HM8), ~400 seed entries total
- [x] 4 system prompts → `domains/healthcare/prompts/`
- [x] Access policy JSON → `domains/healthcare/configs/access_policy.json`
- [x] Attack payloads (3 APs × 5 variants + 1 benign = 20 payloads):
  - [x] AP-1 analogue: Triage agent tricked into writing prescriptions (H8)
  - [x] AP-2 analogue: Poisoned lab results → wrong diagnosis in patient records
  - [x] AP-4 analogue: Compliance agent exfiltrates PHI into quality metrics
- [x] Benign clinical workflows
- [ ] **Baseline verification (all 3 configs):**
  - [ ] Initialize healthcare memory: `python -m memory.chromadb_setup --domain healthcare`
  - [ ] Start healthcare tools: `python -m domains.healthcare.tools.start_all`
  - [ ] Flat MAS: run 1 benign clinical workflow E2E → completes ✓
  - [ ] Flat MAS: verify Triage agent CAN call H8 (Prescription Writer) — no restrictions ✓
  - [ ] ACL-Hardened: run 1 benign → completes ✓
  - [ ] ACL-Hardened: verify Triage → H8 returns 403 ✓
  - [ ] AgenticCyOps: run 1 benign → completes, all P1–P5 logging, zero false blocks ✓

### 3.10 Finance Adapter — **C** (Day 4)
- [x] 4 manifests → `domains/finance/configs/` (+ memory_collections.json, access_policy.json)
  - Monitor: F1-F4 (Transaction Stream, Rule Engine, Customer Profile, Alert Queue)
  - Analyze: F5-F7 (Graph Analysis, External Fraud DB, Document Verification)
  - Admin: F8-F10 (Account Freeze, Chargeback Processor, Wire Recall)
  - Report: F11-F13 (SAR Generator, Audit Compiler, Regulatory Submission)
- [x] 13 tool stubs (F1-F13), 8 memory collections (FM1-FM8, ~396 seed entries), 4 system prompts, access policy
- [x] Attack payloads (3 APs × 5 variants + 1 benign = 20 payloads):
  - [x] AP-1 analogue: Surveillance agent tricked into freezing accounts (F8)
  - [x] AP-2 analogue: Falsified fraud determination poisons case history
  - [x] AP-5 analogue: Account action agent proposes mass account freezes
- [x] Benign fraud investigation workflows
- [ ] **Baseline verification (all 3 configs):**
  - [ ] Initialize finance memory: `python -m memory.chromadb_setup --domain finance`
  - [ ] Start finance tools: `python -m domains.finance.tools.start_all`
  - [ ] Flat MAS: run 1 benign fraud workflow E2E → completes ✓
  - [ ] Flat MAS: verify Surveillance agent CAN call F8 (Account Freeze) ✓
  - [ ] ACL-Hardened: run 1 benign → completes ✓
  - [ ] ACL-Hardened: verify Surveillance → F8 returns 403 ✓
  - [ ] AgenticCyOps: run 1 benign → completes, all P1–P5 logging, zero false blocks ✓

### 3.11 Legal Adapter — **C** (Day 4)
- [x] 4 manifests → `domains/legal/configs/` (+ memory_collections.json, access_policy.json)
  - Monitor: L1-L4 (Docket Search, Deadline Tracker, Conflict Checker, Client Portal)
  - Analyze: L5-L7 (Case Law DB, Statute Search, Contract Analyzer)
  - Admin: L8-L10 (Court Filing, Document Signing, Payment Processing)
  - Report: L11-L13 (Client Memo Generator, Billing System, Matter Close)
- [x] 13 tool stubs (L1-L13), 8 memory collections (LM1-LM8, ~400 seed entries), 4 system prompts, access policy
- [x] Attack payloads (3 APs × 5 variants + 1 benign = 20 payloads):
  - [x] AP-1 analogue: Research agent tricked into filing court documents (L8)
  - [x] AP-2 analogue: Poisoned case law → wrong legal analysis in research memos
  - [x] AP-4 analogue: Client reporting agent exfiltrates privileged comms into billing
- [x] Benign case management workflows
- [ ] **Baseline verification (all 3 configs):**
  - [ ] Initialize legal memory: `python -m memory.chromadb_setup --domain legal`
  - [ ] Start legal tools: `python -m domains.legal.tools.start_all`
  - [ ] Flat MAS: run 1 benign case workflow E2E → completes ✓
  - [ ] Flat MAS: verify Research agent CAN call L8 (Court Filing) ✓
  - [ ] ACL-Hardened: run 1 benign → completes ✓
  - [ ] ACL-Hardened: verify Research → L8 returns 403 ✓
  - [ ] AgenticCyOps: run 1 benign → completes, all P1–P5 logging, zero false blocks ✓


### 3.12 Baseline Readiness Gate — **All** (End of Day 4)

**No attack runs start until all 12 cells pass.**

| Domain | Flat MAS E2E | ACL-Hardened E2E | AgenticCyOps E2E | Ready |
|--------|-------------|-----------------|-----------------|-------|
| CyberOps | ✓ PASS | ✓ PASS | ✓ PASS | ✓ |
| Healthcare | ☐ PASS | ☐ PASS | ☐ PASS | ☐ |
| Finance | ☐ PASS | ☐ PASS | ☐ PASS | ☐ |
| Legal | ☐ PASS | ☐ PASS | ☐ PASS | ☐ |

- [ ] All 12 cells PASS
- [ ] Log files confirm: Flat has no defenses active, ACL has only HTTP 403, AgenticCyOps has all P1–P5
- [ ] **Proceed to Phase 4**

**If any cell fails:**
- Flat fails → tool stub or memory seed issue → fix tool/seed, not framework
- ACL fails → ACL config wrong → check `acl_config.yaml` for that domain
- AgenticCyOps fails → defense false-blocking → tune validator prompts or write-filter threshold
- Do NOT start attacks until the failing cell is fixed


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
# Or use the evaluation script:
bash scripts/run_eval_f.sh

# Healthcare
python -m attacks.harness --domain healthcare --ap ap1 --config all --trials 10
python -m attacks.harness --domain healthcare --ap ap2 --config all --trials 10
python -m attacks.harness --domain healthcare --ap ap4 --config all --trials 10
python -m attacks.harness --domain healthcare --benign --config all --trials 5

# Finance
python -m attacks.harness --domain finance --ap ap1 --config all --trials 10
python -m attacks.harness --domain finance --ap ap2 --config all --trials 10
python -m attacks.harness --domain finance --ap ap5 --config all --trials 10
python -m attacks.harness --domain finance --benign --config all --trials 5

# Legal
python -m attacks.harness --domain legal --ap ap1 --config all --trials 10
python -m attacks.harness --domain legal --ap ap2 --config all --trials 10
python -m attacks.harness --domain legal --ap ap4 --config all --trials 10
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
- [ ] Same-family (Group C config): 3× Qwen3-32B → AP-1, 30 trials
- [ ] Default diverse (Group A config): V1 + V2 + V4(Claude) + V6(GPT-4o) (4 families, t=3/4) → AP-1, 30 trials
- [ ] All-local diverse: V1 + V2 + V3(Llama) (3 families, t=2/3) → AP-1, 30 trials
  - **Note:** V3(Llama) requires Claude-primary or no Qwen3-235B (GPU 4,5 conflict)
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