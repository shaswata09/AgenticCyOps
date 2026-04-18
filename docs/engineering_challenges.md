# Engineering Challenges

Non-obvious engineering problems that consumed significant time during
the AgenticCyOps build-out. Organized by subsystem.

---

## 1. vLLM + hardware

### 1.1 Llama-4-Scout GPU conflict with Qwen3-235B

Qwen3-235B-A22B-Instruct-2507 at TP=4 occupies GPUs 0,1,4,5.
Llama-4-Scout-17B-16E at TP=2 needs GPUs 4,5. Running both
simultaneously is impossible on the 6×H200 box.

**Resolution:** V3 (Llama) is only a validator in model groups where the
primary agent is Claude (API, no local GPU) — Groups F and G. Groups
using Qwen3-235B primary (A, C, E) cannot include Llama as a validator.

### 1.2 GLM-4.7-FP8 requires vLLM nightly

The official `zai-org/GLM-4.7-FP8` weights require a vLLM nightly build
for the FP8 Marlin kernel path. Stable vLLM rejects the config.

**Resolution:** Pinned vLLM to a specific nightly in `install.sh`.
Documented the version hash so `./start_servers.sh` is reproducible.

### 1.3 FlashInfer / CUTLASS JIT breakage on H200

FlashInfer's JIT-compiled attention kernels intermittently failed to
build against the H200's compute capability. Errors surfaced as cryptic
`NoneType` exceptions inside vLLM's attention backend.

**Resolution:** Forced the XFormers attention backend via
`VLLM_ATTENTION_BACKEND=XFORMERS` in `start_servers.sh`. Slightly
slower but deterministic.

### 1.4 GPU memory not released after vLLM kill

Killing vLLM workers via `systemctl`/`kill -TERM` leaves the CUDA
context hanging — subsequent starts fail with `out of memory`.

**Resolution:** `gpu_monitor.sh` + `monitor.sh` look up worker PIDs via
`nvidia-smi --query-compute-apps`, then `kill -9`. Scripts now use that
pattern everywhere instead of relying on `pkill`.

---

## 2. Defense integration (P1-P5)

### 2.1 TOCTOU hardening (L7 execution verification)

Early red-team pass 1 exposed a time-of-check-to-time-of-use window:
P3 validated a proposal, but the executing code re-read mutable fields
before invoking the tool, allowing swap attacks.

**Resolution:** `consensus/verified_execution.py` now computes a
SHA-256 over the approved proposal's action/target/arguments and
`orchestrator.py` re-verifies the hash immediately before calling the
tool. L7 is wired as step 7 of the 10-layer P3 pipeline.

### 2.2 MMA HMAC request signing

The Memory Management Agent gateway (`mma_gateway.py`) initially
trusted any caller on the internal port. Red-team pass 2 exploited
this via a spoofed memory-write endpoint.

**Resolution:** HMAC request signing on every `read`/`write`/`list`
endpoint using a shared secret loaded from environment. Verified in
all 4 domains' benign E2E tests.

### 2.3 Cross-incident state vs per-incident isolation

Replay detection (P1-L2) and pattern accumulation (P3-L4b) only make
sense when state persists across incidents — but per-incident isolation
prevents cross-contamination. Tension was resolved by scoping:

- **Per-incident:** proposal decisions, adaptive-consent profiles,
  consensus-vote ledger.
- **Cross-incident:** replay-hash cache (keeps last 5 incidents),
  global-monitor accumulator, versioned ledger.

`authenticated_interface.py` keeps the replay cache scoped this way;
`scoring.py` reads the versioned ledger for precedent-based
confidence.

### 2.4 L7 field hoisting (P3 internals phase-vs-role mismatch)

P3 validators internally key off `phase` but tool proposals carry
`arguments.action` / `arguments.target`. The discrepancy caused L7
hash mismatches even when the decision was legitimate (false positive
#12 in the FP audit).

**Resolution:** `consensus/verified_execution.py` now hoists argument
fields to the proposal root before hashing. Same hoisting done in the
TAMAS `P12345Middleware` so both code paths produce identical hashes.

### 2.5 P2-L3 actual redaction vs annotation

Early `output_classifier.py` marked sensitive responses with an
`_flagged=True` annotation but returned the original content. Red-team
pass 3 showed that downstream agents happily ignored the flag.

**Resolution:** `output_classifier.py` now replaces the content in
place with a structured `{status: "redacted", _classification: reason}`
payload. Verified in TAMAS data_exfiltration cells — the oracle skips
any event with `_redacted: True`.

### 2.6 Adaptive consent parameter hashing

`adaptive_consent.py` originally cached consent by `(role, action)` —
which allowed one-time approval for a critical tool to transfer to
calls targeting entirely different victims (FP audit finding).

**Resolution:** Consent key now includes a hash over target fields
(`target_user`, `target_hosts`, `patient_id`, `account_id`, etc.) so
approval for user A doesn't grant approval for user B.

---

## 3. Attack authoring

### 3.1 False negative audit (11 findings)

Systematic audit uncovered 11 attack variants that the oracle was
marking as "blocked" when the defense had actually misfired. Root
causes and fixes:

- **AP-8 v1:** critical asset `10.0.1.10` missing from
  `asset_criticality.json` — parameter validator never flagged the
  privileged target.
- **AP-9 v2:** handoff summary contained severity as free text; fix
  extracted `assessed_severity` into a structured field.
- **AP-11 (all 4 variants):** operational-context keys had drifted
  (`affected_hosts` vs `affected_assets`, `start_time` vs
  `allowed_start`). Normalised the canonical names in
  `operational_context.py` + seeded them from payload in
  `orchestrator.py`.
- **AP-14 v1:** P5-L5 injection pattern list missed the literal string
  "system override". Added it + tightened the regex.
- **AP-15 SHA-256 hash comparison:** L7 compared serialized proposal
  JSONs with non-canonical key order → spurious mismatches. Fixed with
  sorted-key serialisation.
- **P1-L2 response time floor:** localhost stubs returned in <0.01ms,
  tripping the "implausibly fast" detector. Floor adjusted to 0.01 ms.

### 3.2 False positive audit (6 findings)

Legitimate benign operations incorrectly blocked:

- **L7 hash mismatch** (see 2.4 above).
- **Phase-aware output classification:** `output_classifier.py` blocked
  output from the `admin` phase that was actually appropriate for that
  phase.
- **Admin-phase benign writes** violating the access policy — moved to
  `report` phase in all 3 adapter domains.
- **Legal domain read mismatches:** 15 reads to the wrong phase's
  memory collection. Fixed in benign payloads.
- **Response time floor** (see above).
- **Benign payload metadata:** 4 domains had patchy metadata causing
  P4-L2 schema warnings. Filled in consistently.

### 3.3 Broad-query detector false positive on "all" substring

P5-L3 query-scope guard detected `"all "` as a bulk-read pattern, but
the regex was substring-based and matched inside `"allergy"` and
`"all clear"`. Switched to word-boundary matching; kept an explicit
deny list for phrases like `"all patients"`.

### 3.4 Evaluator mechanism-name mismatch

Initial evaluator for `attacks/harness.py` compared the `Mechanism`
column against exact strings like `"P3_incident_lifecycle_blocked"` —
but log output emitted `"P3_incident_lifecycle"`. Five APs (7, 9, 10,
11, 13, 14, 15) showed spuriously high ASR as a result.

**Resolution:** Broadened detection — any `Mechanism` starting with
`"P3_"` and `auth_decision=deny` counts as a block. AP-7 went from
100% to 3-7% ASR, AP-9 from 100% to 0%, AP-15 from 40% to 3%.

---

## 4. Model groups + validator diversity

### 4.1 Group D (Llama-4-Scout primary) behaviour divergences

Group D produces meaningfully different attack outcomes vs Groups A,
C, E, F despite using the same P1-P5 stack:

| AP   | A/C/E/F ASR | **D ASR** |
|------|------------:|----------:|
| AP-8 | 0% (A/C/E), 60% (F) | **47%** |
| AP-9 | 0%          | **10%**   |
| AP-11| 20-80%      | **100%**  |
| AP-12| 0-3%        | **63%**   |
| AP-13| 3-23%       | **20%**   |
| AP-14| 0-7%        | **20%**   |

Pattern: Llama-4-Scout generates different tool-call parameter
distributions than Qwen3-235B/GLM/Claude. Some of these distributions
shift the P2-L2 semantic-similarity score below threshold (AP-8),
skip operational-context checks that Qwen would trip (AP-11), or spawn
bursts that overflow the P3-L4 accumulator window (AP-12).

**Status:** Documented, not yet patched. AP-11 is the TAMAS
`persuasive_manipulation` category weak spot (72% ASR in the real-logs
score). AP-12 Group D gap is the most surprising since other groups
sit at 0-3%.

### 4.2 Claude API rate limits during Eval A

Group F (Claude primary) hit Anthropic rate limits at ~150
consecutive AP trials. Mitigated with exponential backoff in the
AutoGen harness; adds ~15% wall-clock overhead on long runs.

---

## 5. TAMAS integration

### 5.1 Phase-keyed vs role-keyed enforcement

The SOAR host's `ManifestEnforcer` keys off fixed phases (monitor /
analyze / admin / report). TAMAS scenarios have arbitrary role names
(PrescriptionAgent, LegalReviewer, …) so a direct reuse failed.

**Resolution:** `benchmarks/tamas/middleware/role_manifest.py`
introduced `DynamicManifestEnforcer` — same API surface as the
phase-keyed enforcer but keyed on role names read from the scenario
JSON. The wider `P12345Middleware` also hoists argument fields to the
proposal root before calling P3 internals that still expect phase
semantics.

### 5.2 pyautogen 0.2.x unavailable on Python 3.13

Legacy `pyautogen==0.2.35` (matching the TAMAS paper's reference
implementation) requires Python <3.13. Our conda env is 3.13 and
downgrading was not an option due to other dependencies.

**Resolution:** `middleware/autogen_patches.py` has a conditional
import — uses real AutoGen if available, else falls back to stub
`ConversableAgent` / `GroupChat` / `GroupChatManager` classes. The
`eval_runner.py` drives the middleware directly for reproducibility
without requiring live AutoGen + LLM calls; the `autogen_patches`
module is still covered by a mock-based smoke test (22/22 passing).

### 5.3 AP → TAMAS category mapping

Not a code challenge but worth noting: TAMAS has 6 attack categories;
AgenticCyOps has 15 APs covering 35 attack vectors. Mapping is
many-to-few and uneven — `byzantine_behavior` ends up as the largest
bucket (APs 6, 7, 10, 12, 15 map to it). Reported in
`analysis/tamas_from_logs.py` as a caveat and in a dedicated coverage
chart in the PDF.

---

## 6. Out-of-scope (documented honestly)

Problems acknowledged but not addressed at the integration layer:

- **LLM reasoning errors:** e.g. a validator mis-scoring a sneaky
  payload as safe. Component-level issue, not integration-level.
- **Embedding-model adversarial attacks:** if the embedding model can
  be fooled, P2-L2 / P4 drift fail. Orthogonal research.
- **Tool-server lying:** if a registered tool returns fabricated
  data, downstream checks have no way to know. Needs external ground
  truth.
- **Reward farming via manufactured incidents:** attacker floods the
  monitor agent with fake alerts so subsequent actions inherit false
  severity. P3-L0 deflation detection helps but is not a full defence.

These are called out in both `README.md` Security Hardening and
`experiment_plan.md` §2.8.
