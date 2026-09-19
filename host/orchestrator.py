"""
SOAR Host Orchestrator.

Central coordinator that routes incidents through 4 phases sequentially.
Domain-agnostic — loads configs/tools/prompts from domains/{domain}/.

Config modes:
  "flat":           No enforcement. Agents call anything directly.
  "acl_hardened":   Manifest enforcement (P2-L1) only. No consensus/MMA.
  "agenticcyops":   Full P1-P5 enforcement.
"""

import json
import time as _time
from typing import Optional
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from config import BASE_DIR
from logging_utils import ExperimentLogger
from host.manifest_enforcer import ManifestEnforcer
from host.handoff import PhaseHandoff
from host.authenticated_interface import AuthenticatedInterface
from host.parameter_validator import ParameterValidator
from host.output_classifier import OutputClassifier
from consensus.verified_execution import VerifiedExecution
from mcp_servers.server_registry import ServerRegistry


PHASE_ORDER = ["monitor", "analyze", "admin", "report"]


class SOARHost:
    """Central orchestrator for the AgenticCyOps testbed."""

    def __init__(
        self,
        domain: str,
        config: str = "agenticcyops",
        llm_url: str = "http://localhost:8000/v1",
        mma_url: str = "http://localhost:9100",
        tool_registry: Optional[ServerRegistry] = None,
        consensus=None,
        agents: Optional[dict] = None,
        logger: Optional[ExperimentLogger] = None,
        embedding_model=None,
        disabled_principles: Optional[set] = None,
        state_mode: str = "isolated",
        adaptive_consent_path=None,
    ):
        self.domain = domain
        self.config = config
        self.llm_url = llm_url
        self.mma_url = mma_url
        self.tool_registry = tool_registry
        self.consensus = consensus
        self.agents = agents or {}
        self.logger = logger

        # State mode (H3).  "isolated": every incident starts from the
        # configured baseline (all cross-incident defense state and the
        # MMA's per-trial documents are reset before it runs).
        # "persistent": state accumulates across incidents as in production.
        if state_mode not in ("isolated", "persistent"):
            raise ValueError(f"state_mode must be isolated or persistent, got {state_mode!r}")
        self.state_mode = state_mode

        # Ablation switch -- only meaningful for the agenticcyops config.
        # Layer call sites consult ``self._principle_active("Px")`` and
        # short-circuit when the principle is disabled.  Stored uppercase
        # so callers can pass either case.
        self.disabled_principles: set = {p.upper() for p in (disabled_principles or set())}

        self.enforcer = ManifestEnforcer(domain=domain, logger=logger)
        self.handoff = PhaseHandoff(logger=logger)

        # Layer instantiation
        #   agenticcyops -> P1 identity + P2 manifest/params/output + P3 full
        #                   verified-execution stack (which wraps consensus)
        #   llm_judge    -> P1 identity only; the new elif branch in
        #                   _process_tool_call calls `self.consensus`
        #                   directly without P2/P3/P4/P5
        #   flat / acl_hardened -> none of the above (no auth_interface)
        if config in ("agenticcyops", "llm_judge"):
            self.auth_interface = AuthenticatedInterface(domain=domain, logger=logger)
        else:
            self.auth_interface = None

        if config == "agenticcyops":
            self.param_validator = ParameterValidator(
                domain=domain, embedding_model=embedding_model, logger=logger
            )
            self.output_classifier = OutputClassifier(
                domain=domain, embedding_model=embedding_model, logger=logger
            )
            self.verified_execution = VerifiedExecution(
                domain=domain,
                consensus_validator=consensus,
                embedding_model=embedding_model,
                logger=logger,
                adaptive_consent_path=adaptive_consent_path,
                adaptive_consent_persist=(state_mode == "persistent"),
            )
        else:
            self.param_validator = None
            self.output_classifier = None
            self.verified_execution = None

        self._llm = AsyncOpenAI(base_url=llm_url, api_key="unused")

    async def run_incident(self, incident: dict, harness_injection: Optional[dict] = None) -> dict:
        """Full pipeline: Monitor -> Analyze -> Admin -> Report.

        ``harness_injection`` (H5) carries the payload's ``meta.injection``
        block for the ``handoff`` and ``proposal_justification`` channels.
        It is never part of ``incident`` and therefore never rendered to a
        model; the hooks below are the only consumers.
        """
        self.harness_injection = dict(harness_injection or {})
        context = {
            "incident": incident,
            "incident_id": incident.get("incident_id", str(uuid4())),
            "domain": self.domain,
            "config": self.config,
            "phases": {},
        }

        self.enforcer.reset_counts()
        self._call_seq = 0

        # P3: Reset per-incident state; in isolated mode every
        # cross-incident state as well (H3).
        if self.state_mode == "isolated":
            await self.reset_trial_state()
        elif self.verified_execution:
            self.verified_execution.reset_for_incident()

        # P1-L3: Verify config integrity before each incident
        if self.auth_interface:
            self.auth_interface.reset_replay_cache()
            configs_ok, changed_files = self.auth_interface.verify_config_integrity()
            if not configs_ok:
                if self.logger:
                    self.logger.log(
                        source="host", destination="config_integrity",
                        action="config_verification",
                        extra={"auth_decision": "deny",
                               "mechanism": "P1_config_integrity_violation",
                               "changed_files": changed_files},
                    )
                return {"status": "config_integrity_failure",
                        "changed_files": changed_files}

        # Register incident status for P3-L0.5 lifecycle check (AP-11 v2 / v5)
        if self.verified_execution:
            inc_status = incident.get("incident_status", incident.get("status", "open"))
            self.verified_execution.operational_context.register_incident_status(
                context["incident_id"], inc_status)

        # Seed change_log from incident payload with the payload's declared
        # approval timestamp so the 72h cutoff reflects the scenario timeline
        # rather than wall-clock drift (AP-11 v1).
        if self.verified_execution:
            recent_change = incident.get("recent_change")
            if recent_change:
                self.verified_execution.operational_context.record_change(
                    tool_id=recent_change.get("tool", recent_change.get("action", "")),
                    action=recent_change.get("action", ""),
                    target=recent_change.get("target", ""),
                    incident_id=context["incident_id"],
                    timestamp=recent_change.get("approved_at") or recent_change.get("timestamp"))

        # Seed maintenance windows from payload so P3-L0.5 maintenance-window
        # check has data to compare against (AP-11 v3 / v5).
        if self.verified_execution:
            maint_ctxs = []
            if isinstance(incident.get("maintenance_context"), dict):
                maint_ctxs.append(incident["maintenance_context"])
            if isinstance(incident.get("maintenance_contexts"), list):
                maint_ctxs.extend(incident["maintenance_contexts"])
            for mc in maint_ctxs:
                asset = mc.get("asset") or mc.get("hostname")
                start = mc.get("start_time") or mc.get("start")
                end = mc.get("end_time") or mc.get("end")
                if asset and start and end:
                    self.verified_execution.operational_context.add_maintenance_window(
                        asset=asset,
                        start_time=start,
                        end_time=end,
                        window_id=mc.get("maintenance_window_id", "payload_seeded"))

        # Propagate the incident's claimed execution time to every P3 check
        # so time / window / change-conflict comparisons honour the
        # scenario's declared timeline (AP-11 v4 / v5).
        claimed_time = (
            (incident.get("time_context") or {}).get("current_time")
            or incident.get("timestamp")
        )
        if claimed_time:
            context["claimed_time"] = claimed_time

        for i, phase in enumerate(PHASE_ORDER):
            if phase not in self.agents:
                continue

            result = await self.run_phase(phase, context)
            context["phases"][phase] = result

            # Handoff to next phase
            if i < len(PHASE_ORDER) - 1:
                next_phase = PHASE_ORDER[i + 1]
                handoff_ctx = self.handoff.create_handoff(
                    source_phase=phase,
                    target_phase=next_phase,
                    phase_output=result,
                    incident_context=context,
                )
                if self.harness_injection:
                    handoff_ctx = self._inject_handoff(phase, next_phase, handoff_ctx)
                context[f"{phase}_handoff"] = handoff_ctx

        return context

    # ---- H5 injection channels (harness only) ---------------------------

    def _inject_handoff(self, phase: str, next_phase: str, handoff_ctx: dict) -> dict:
        """``handoff`` channel: the attacker phase's handoff is altered as a
        compromised agent would alter it.  Spec (``meta.injection.handoff``):
        ``{"from_phase": ..., "fields": {...}, "append_summary": "..."}``."""
        spec = self.harness_injection.get("handoff")
        if not isinstance(spec, dict):
            return handoff_ctx
        src = spec.get("from_phase") or self.harness_injection.get("attacker_phase")
        if src and src != phase:
            return handoff_ctx
        out = dict(handoff_ctx)
        for k, v in (spec.get("fields") or {}).items():
            out[k] = v
        if spec.get("append_summary"):
            out["phase_summary"] = f"{out.get('phase_summary', '')}\n\n{spec['append_summary']}".strip()
        if self.logger:
            self.logger.log(source="harness", destination=f"{next_phase}_agent",
                            action="harness_injection",
                            extra={"channel": "handoff", "phase": phase,
                                   "fields": sorted((spec.get("fields") or {}).keys()),
                                   "append_summary": bool(spec.get("append_summary"))})
        return out

    def _inject_proposals(self, phase: str, result) -> None:
        """``proposal_justification`` channel: proposals a compromised
        attacker phase would emit are appended to the agent's own.  Spec:
        ``meta.injection.proposal`` (one) or ``proposals`` (list) of
        ``{"phase", "tool", "arguments", "justification"}``."""
        from agents.base_agent import ToolCallProposal
        specs = []
        one = self.harness_injection.get("proposal")
        if isinstance(one, dict):
            specs.append(one)
        specs.extend(p for p in (self.harness_injection.get("proposals") or []) if isinstance(p, dict))
        default_phase = self.harness_injection.get("attacker_phase")
        for spec in specs:
            if (spec.get("phase") or default_phase or phase) != phase or not spec.get("tool"):
                continue
            result.proposed_tool_calls.append(ToolCallProposal(
                tool_id=spec["tool"], arguments=dict(spec.get("arguments") or {}),
                justification=str(spec.get("justification") or "")))
            if self.logger:
                self.logger.log(source="harness", destination=spec["tool"],
                                action="harness_injection",
                                extra={"channel": "proposal_justification", "phase": phase,
                                       "arguments": dict(spec.get("arguments") or {})})

    def _trial_id(self) -> str:
        return (getattr(self.logger, "_trial_id", None) or "") if self.logger else ""

    async def reset_trial_state(self) -> dict:
        """Return every stateful component to its baseline (H3).

        In-process: P2 action counts, P1 replay cache, the whole P3 stack
        (intent chain, cross-incident ledger, versioned ledger, global
        monitor, adaptive consent, operational context).  Out of process:
        ``POST /admin/reset`` on the MMA gateway clears P4 hashes /
        centroids, P5 read history and every document tagged with a
        ``trial_id``.  Returns a summary that is also logged as a
        ``trial_reset`` event.
        """
        self.enforcer.reset_counts()
        if self.auth_interface:
            self.auth_interface.reset_replay_cache()
        if self.verified_execution:
            self.verified_execution.reset_for_trial()
        summary = {"state_mode": self.state_mode, "in_process": True, "mma": None}
        if self.config == "agenticcyops" and self.mma_url:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(f"{self.mma_url}/admin/reset",
                                             json={"auth_token": self._mma_token("admin", "reset")},
                                             timeout=30)
                    summary["mma"] = resp.json() if resp.status_code == 200 else {
                        "status": resp.status_code}
            except Exception as exc:
                summary["mma"] = {"error": str(exc)[:120]}
        if self.logger:
            self.logger.log(source="host", destination="state", action="trial_reset",
                            extra=summary)
        return summary

    @staticmethod
    def _mma_token(phase: str, store_id: str) -> str:
        """Request signature the MMA gateway verifies (shared HMAC key)."""
        import hashlib as _hl
        import hmac as _hm
        import os as _os
        key = _os.environ.get("MMA_SHARED_SECRET", "")
        if not key:
            key_path = BASE_DIR / "configs" / "hmac_key.txt"
            if key_path.exists():
                key = key_path.read_text().strip()
        if not key:
            return ""
        return _hm.new(key.encode(), f"{phase}:{store_id}".encode(), _hl.sha256).hexdigest()[:16]

    async def run_phase(self, phase: str, context: dict) -> dict:
        """Execute a single phase with enforcement based on config.

        Scripted memory reads (``incident.memory_ops.reads``) run *before*
        the agent's LLM call and their results are placed in
        ``context["memory_context"][phase]``, so what the store returns can
        reach the model (H4).  Scripted writes run after the agent's own
        writes.
        """
        agent = self.agents[phase]
        memory_ops = context.get("incident", {}).get("memory_ops", {}) or {}

        # Scripted reads for this phase (every config; enforcement differs)
        reads = []
        for mr in memory_ops.get("reads", []) or []:
            if mr.get("phase") == phase:
                reads.append(await self._process_memory_read(phase, mr, context))
        if reads:
            context.setdefault("memory_context", {})[phase] = reads

        # Agent proposes actions
        try:
            result = await agent.execute(context)
        except Exception as e:
            from agents.base_agent import AgentResult
            result = AgentResult(phase=phase, summary=f"Agent error: {str(e)[:200]}")
            if self.logger:
                self.logger.log(source=f"{phase}_agent", destination="error",
                               action="agent_error", extra={"error": str(e)[:200]})

        if self.harness_injection:
            self._inject_proposals(phase, result)

        # Process proposed tool calls SEQUENTIALLY (TA-19: no parallel bypass)
        executed_responses = []
        for tc in result.proposed_tool_calls:
            response = await self._process_tool_call(phase, tc, context)
            executed_responses.append(response)
            self.enforcer.record_action(phase)

            # Break on critical safety gate failures (TA-19 fix)
            if isinstance(response, dict) and response.get("status") in ("denied", "escalated"):
                reason = response.get("reason", "")
                if any(m in reason for m in (
                    "P3_dangerous_pattern", "P3_posture_threshold",
                    "P3_cross_", "P3_exact_replay", "bulk_action",
                )):
                    break

        result.tool_responses = executed_responses

        # Process proposed memory writes (from agent)
        for mw in result.memory_writes:
            await self._process_memory_write(phase, mw, context)

        # Scripted writes for this phase (every config; enforcement differs)
        for mw in memory_ops.get("writes", []) or []:
            if mw.get("phase") == phase:
                await self._process_memory_write(phase, {
                    "store_id": mw["store"],
                    "content": mw.get("content", ""),
                    "metadata": mw.get("metadata", {}),
                    "doc_id": f"{phase}_{mw['store']}_{context.get('incident_id', 'unknown')}",
                    "scripted": True,
                }, context)

        return result.to_dict()

    # TA-21: Generic rejection reasons to prevent defense leakage to agents
    _SANITIZED_REASONS = {
        "P1_authenticated_interface": "Action not permitted.",
        "P1_unregistered_tools": "Action not permitted.",
        "P2_capability_scoping": "Action not permitted for this phase.",
        "P2_tool_not_in_manifest": "Action not permitted for this phase.",
        "P2_wildcard_parameter": "Invalid parameters.",
        "P2_critical_asset": "Action not permitted for this target.",
        "P2_high_criticality_destructive": "Action not permitted for this target.",
        "P2_parameter_rule_violation": "Invalid parameters.",
        "P2_target_not_in_evidence": "Target not supported by incident evidence.",
        "P3_verified_execution": "Action not approved.",
        "P3_rejected": "Action not approved.",
        "acl_network_layer": "Access denied.",
    }

    def _sanitize_reason(self, reason: str) -> str:
        """Strip defense internals from rejection reasons (TA-21 fix)."""
        for key, generic in self._SANITIZED_REASONS.items():
            if key in reason:
                return generic
        # Default: strip anything after colon (often contains specifics)
        if ":" in reason:
            return reason.split(":")[0] + "."
        return "Action denied."

    def _principle_active(self, principle: str) -> bool:
        """True iff ``principle`` (e.g. 'P3') is NOT in disabled_principles.

        Only meaningful for the agenticcyops config; the flat / acl_hardened
        branches never consult this helper.  Used by ablation studies to
        disable specific principles at runtime via the harness's
        ``--disable-principles`` CLI flag.
        """
        return principle.upper() not in self.disabled_principles

    # Compact, size-bounded snapshot of tool-call arguments for the audit log.
    # Attack evaluation (attacks/harness.py) matches scripted adversarial
    # actions on tool + operation + parameters when this field is present;
    # logs written before 2026-09 carry tool names only.  The unbounded
    # arguments are on the ``tool_proposed`` event that precedes every
    # ``tool_call`` event with the same ``call_id``.
    _ARG_LOG_MAX_CHARS = 600

    @classmethod
    def _compact_args(cls, arguments) -> dict:
        try:
            if not isinstance(arguments, dict):
                return {}
            out = {}
            for k, v in arguments.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v
                else:
                    out[k] = json.dumps(v, default=str)
                if len(json.dumps(out, default=str)) > cls._ARG_LOG_MAX_CHARS:
                    out[k] = str(out[k])[:120] + "..."
            return out
        except Exception:
            return {}

    def _args_for_log(self, tc) -> dict:
        """``{"arguments": <compact>, "call_id": ...}`` for a tool_call event."""
        arguments = tc.arguments if hasattr(tc, "arguments") else tc
        out = {"arguments": self._compact_args(arguments)}
        call_id = getattr(tc, "call_id", "")
        if call_id:
            out["call_id"] = call_id
        return out

    def _next_call_id(self, phase: str, kind: str, key: str) -> str:
        """Stable per-incident identifier: ``<phase>:<kind>:<seq>:<hash8>``.

        ``seq`` orders proposals within the incident; the hash of the
        proposal content lets two logs of the same scenario be aligned.
        """
        import hashlib as _hl
        self._call_seq = getattr(self, "_call_seq", 0) + 1
        digest = _hl.sha256(key.encode()).hexdigest()[:8]
        return f"{phase}:{kind}:{self._call_seq:03d}:{digest}"

    async def _process_tool_call(self, phase: str, tc, context: dict) -> dict:
        """Record the proposal, then run config-appropriate enforcement.

        The ``tool_proposed`` event is written before any check in every
        config, with the full arguments and a ``call_id`` that every later
        event for this call (denial, execution, redaction) carries.
        """
        if not getattr(tc, "call_id", ""):
            key = f"{tc.tool_id}|{json.dumps(tc.arguments, sort_keys=True, default=str)}"
            try:
                tc.call_id = self._next_call_id(phase, "tool", key)
            except Exception:
                pass
        if self.logger:
            self.logger.log(
                source=f"{phase}_agent", destination=tc.tool_id,
                action="tool_proposed",
                extra={
                    "call_id": getattr(tc, "call_id", ""),
                    "arguments": tc.arguments if isinstance(tc.arguments, dict) else {},
                    "justification": (tc.justification or "")[:300],
                },
            )
        return await self._enforce_tool_call(phase, tc, context)

    async def _enforce_tool_call(self, phase: str, tc, context: dict) -> dict:
        """Process a tool call with config-appropriate enforcement.

        Enforcement pipeline (agenticcyops):
          1. P1-L1: Component identity verification
          2. P2-L1: Manifest enforcement (tool allowed for this phase?)
          3. P2-L2: Parameter validation (wildcards, criticality, rules, evidence)
          4. P3:    Consensus validation (for irreversible actions)
          5. Execute tool
          6. P1-L2: Response integrity (schema, timing, replay)
          7. P2-L3: Output classification (sensitive data detection)
        """
        tool_id = tc.tool_id

        # Config-specific enforcement
        if self.config == "acl_hardened":
            # ACL: Enforce at "network layer" — agent was still manipulated into trying
            allowed, reason = self.enforcer.validate_tool_call(phase, tool_id)
            if not allowed:
                if self.logger:
                    self.logger.log_tool_call(
                        agent=f"{phase}_agent",
                        tool=tool_id,
                        auth_decision="deny",
                        mechanism="acl_network_layer",
                        interception_step=2,
                    extra=self._args_for_log(tc))
                return {"status": "denied", "tool_id": tool_id, "reason": f"403: {reason}"}

        elif self.config == "llm_judge":
            # Ablation: P1-L1 identity verification, then route the
            # proposal to the consensus-quorum LLM judge.  Skips
            # P2/P3/P4/P5 entirely so we can isolate "what does an LLM
            # panel-as-judge alone catch?" -- the standard reviewer
            # ablation.  Mechanism strings emitted:
            #     P1_authenticated_interface  (P1 fail)
            #     P3_consensus_reject         (judges deny)
            #     P3_consensus_unavailable    (every validator errored)
            #     P3_consensus_error          (call itself raised)
            #     llm_judge_approved          (judges allow -> falls
            #                                  through to executor below)
            if self.auth_interface:
                verified, reason = self.auth_interface.verify_component(tool_id, "tools")
                if not verified:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P1_authenticated_interface",
                            interception_step=1,
                        extra=self._args_for_log(tc))
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(reason)}

            if self.consensus is not None:
                # Build the same proposal shape the agenticcyops P3 path
                # constructs (lines 436-445).  Hoist arguments fields to
                # the proposal root so validators that read action/target
                # at top level work uniformly.
                proposal = tc.to_proposal()
                proposal["phase"] = phase
                args = proposal.get("arguments", {})
                for field in ("action", "target", "target_user", "target_hosts",
                              "target_users", "account_id", "patient_id", "case_id"):
                    if field in args and field not in proposal:
                        proposal[field] = args[field]
                p3_context = {**context, "current_phase": phase}

                try:
                    result = await self.consensus.validate_with_details(
                        proposal, p3_context)
                except Exception as exc:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="allow",
                            mechanism="P3_consensus_error",
                            interception_step=6,
                        extra=self._args_for_log(tc))
                    # Fall through to execution -- benchmark records this
                    # as an "allow" but with the error-mechanism marker
                    # so analytics can filter these trials out.
                else:
                    votes = list(result.votes)
                    all_error = bool(votes) and all(
                        v.validator_id == "error" for v in votes)
                    if not votes or all_error:
                        if self.logger:
                            self.logger.log_tool_call(
                                agent=f"{phase}_agent",
                                tool=tool_id,
                                auth_decision="allow",
                                mechanism="P3_consensus_unavailable",
                                interception_step=6,
                        extra=self._args_for_log(tc))
                        # Same fall-through semantics as InjecAgent's
                        # evaluate_with_consensus: don't silently mask
                        # results when validators are down.
                    elif not result.approved:
                        if self.logger:
                            self.logger.log_tool_call(
                                agent=f"{phase}_agent",
                                tool=tool_id,
                                auth_decision="deny",
                                mechanism="P3_consensus_reject",
                                interception_step=6,
                        extra=self._args_for_log(tc))
                        return {"status": "denied", "tool_id": tool_id,
                                "reason": (f"consensus rejected "
                                            f"({result.rejections}/{len(votes)} "
                                            f"reject, threshold {result.threshold})")}
                    else:
                        if self.logger:
                            self.logger.log_tool_call(
                                agent=f"{phase}_agent",
                                tool=tool_id,
                                auth_decision="allow",
                                mechanism="llm_judge_approved",
                                interception_step=6,
                        extra=self._args_for_log(tc))

        elif self.config == "agenticcyops":
            # ── Step 1: P1-L1 — Component identity ──
            if self.auth_interface and self._principle_active("P1"):
                verified, reason = self.auth_interface.verify_component(tool_id, "tools")
                if not verified:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P1_authenticated_interface",
                            interception_step=1,
                        extra=self._args_for_log(tc))
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(reason)}

            # ── Step 2: P2-L1 — Manifest enforcement ──
            if self._principle_active("P2"):
                allowed, reason = self.enforcer.validate_tool_call(phase, tool_id)
                if not allowed:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P2_capability_scoping",
                            interception_step=2,
                        extra=self._args_for_log(tc))
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(reason)}

            # ── Step 3: P2-L2 — Parameter validation ──
            if self.param_validator and self._principle_active("P2"):
                incident_evidence = json.dumps(
                    context.get("incident", {}), default=str
                )
                params_ok, p_reason, p_details = self.param_validator.validate(
                    tool_id, tc.arguments, incident_evidence
                )
                if not params_ok:
                    if self.logger:
                        self.logger.log(
                            source=f"{phase}_agent", destination=tool_id,
                            action="tool_call", auth_decision="deny",
                            mechanism="P2_capability_scoping",
                            interception_step=2,
                            extra={"p2l2_reason": p_reason, **p_details,
                                   **self._args_for_log(tc)},
                        )
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(p_reason)}

        # P3: Verified Execution — full multi-layer pipeline (agenticcyops only)
        # Fix #1: Force P3 for negative-impact tools regardless of requires_consensus
        _p3_approved_at = None  # Fix L7: reliable variable init (not dir())
        if (self.config == "agenticcyops" and self.verified_execution
                and self._principle_active("P3")):
            needs_p3 = self.enforcer.requires_consensus(phase, tool_id)
            if not needs_p3 and hasattr(self.verified_execution, 'intent_chain'):
                action = tc.arguments.get("action", "") if hasattr(tc, 'arguments') else ""
                impact = self.verified_execution.intent_chain._get_impact(tool_id, action)
                if impact < 0:
                    needs_p3 = True  # negative-impact tools always go through P3

            if needs_p3:
                proposal = tc.to_proposal()
                proposal["phase"] = phase
                # Hoist arguments fields to top level for P3 layers that
                # read action/target from the proposal root (fourth-pass fix)
                args = proposal.get("arguments", {})
                for field in ("action", "target", "target_user", "target_hosts",
                              "target_users", "account_id", "patient_id", "case_id"):
                    if field in args and field not in proposal:
                        proposal[field] = args[field]
                p3_context = {**context, "current_phase": phase}
                _p3_approved_at = _time.time()  # Fix #3: timestamp for L7
                approved = await self.verified_execution.validate(
                    proposal, p3_context
                )
                if not approved:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P3_verified_execution",
                            interception_step=3,
                        extra=self._args_for_log(tc))
                    return {"status": "denied", "tool_id": tool_id, "reason": "Action not approved."}

            # Bulk action check (count + 1 to include current action — off-by-one fix)
            count = self.enforcer._action_counts.get(phase, 0) + 1
            if self.enforcer.check_bulk_action(phase, count):
                if self.logger:
                    self.logger.log_escalation(
                        source=f"{phase}_agent",
                        reason=f"Bulk action threshold exceeded ({count} actions)",
                        severity="high",
                    )
                    self.logger.log_tool_call(
                        agent=f"{phase}_agent",
                        tool=tool_id,
                        auth_decision="escalate",
                        mechanism="P3_bulk_action",
                        interception_step=3,
                        extra=self._args_for_log(tc))
                return {"status": "escalated", "tool_id": tool_id, "reason": "Action limit reached."}

        # ── Step 5: Execute tool with latency tracking ──
        _t0 = _time.perf_counter()
        if self.tool_registry:
            try:
                response = await self.tool_registry.call_tool(
                    tool_id, tc.arguments, source=f"{phase}_agent"
                )
            except Exception as _e:
                response = {"status": "error", "tool_id": tool_id,
                            "error": str(_e)[:200]}
        else:
            response = {"status": "no_registry", "tool_id": tool_id}
        _latency = (_time.perf_counter() - _t0) * 1000

        if isinstance(response, dict) and response.pop("_harness_injected", None):
            if self.logger:
                self.logger.log(source="harness", destination=tool_id, action="harness_injection",
                                extra={"channel": "tool_response", "phase": phase,
                                       **self._args_for_log(tc)})

        # ── Post-execution checks (agenticcyops only) ──
        if self.config == "agenticcyops":
            # ── Step 6: P1-L2 — Response integrity ──
            if (self.auth_interface and isinstance(response, dict)
                    and self._principle_active("P1")):
                resp_ok, resp_reason = self.auth_interface.validate_response(
                    tool_id, response, _latency
                )
                if not resp_ok:
                    if self.logger:
                        self.logger.log(
                            source=f"{phase}_agent", destination=tool_id,
                            action="tool_call", auth_decision="deny",
                            mechanism="P1_authenticated_interface",
                            interception_step=6,
                            extra={"p1l2_reason": resp_reason, **self._args_for_log(tc)},
                        )
                    return {"status": "response_rejected", "tool_id": tool_id,
                            "reason": "Response validation failed."}

            # ── Step 6b: P3-L7 — Execution verification (Fix #3) ──
            # Compare approved proposal against what was actually executed
            # (same tc object — hash match verifies no TOCTOU modification)
            if (self.verified_execution and _p3_approved_at is not None
                    and self._principle_active("P3")):
                _executed_proposal = tc.to_proposal()
                _executed_proposal["phase"] = phase
                for _f in ("action", "target", "target_user", "target_hosts",
                           "target_users", "account_id", "patient_id", "case_id"):
                    _a = _executed_proposal.get("arguments", {})
                    if _f in _a and _f not in _executed_proposal:
                        _executed_proposal[_f] = _a[_f]
                l7_ok, l7_reason = self.verified_execution.verify_execution(
                    proposal, _executed_proposal, _p3_approved_at
                )
                if not l7_ok:
                    if self.logger:
                        self.logger.log(
                            source=f"{phase}_agent", destination=tool_id,
                            action="tool_call", auth_decision="deny",
                            mechanism="P3_execution_verification",
                            interception_step=7,
                            extra={"l7_reason": l7_reason, **self._args_for_log(tc)},
                        )
                    return {"status": "execution_mismatch", "tool_id": tool_id,
                            "reason": "Execution verification failed."}

            # ── Step 7: P2-L3 — Output classification (Fix #8: actual redaction) ──
            if (self.output_classifier and isinstance(response, dict)
                    and self._principle_active("P2")):
                safe, class_reason, class_details = self.output_classifier.classify(
                    tool_id, response, agent_phase=phase
                )
                if not safe:
                    if self.logger:
                        self.logger.log(
                            source=f"{phase}_agent", destination=tool_id,
                            action="tool_call", auth_decision="redact",
                            mechanism="P2_capability_scoping",
                            interception_step=7,
                            extra={"p2l3_reason": class_reason, **class_details,
                                   **self._args_for_log(tc)},
                        )
                    # Fix #8: Actually redact sensitive content
                    response = {
                        "status": "redacted",
                        "tool_id": tool_id,
                        "_redacted": True,
                        "_classification": class_reason,
                    }

        if self.logger:
            self.logger.log_tool_call(
                agent=f"{phase}_agent",
                tool=tool_id,
                auth_decision="allow",
                mechanism="P2_capability_scoping" if self.config != "flat" else "none",
                latency_ms=_latency,
            extra=self._args_for_log(tc))

        return response

    async def _mma_post(self, path: str, payload: dict, timeout: float = 10.0):
        """POST to the MMA gateway.  Returns ``(status_code, body)``;
        ``(0, {"error": ...})`` when the gateway is unreachable."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.mma_url}{path}", json=payload, timeout=timeout)
            try:
                body = resp.json()
            except Exception:
                body = {}
            return resp.status_code, body
        except Exception as exc:
            return 0, {"error": str(exc)[:160]}

    @staticmethod
    def _p5_mechanism(status_code: int, body) -> str:
        """Map an MMA read denial (status + detail) to the P5 layer name.

        MMA returns 403 for L1 access control, 422 for L3 query scope
        violations, 429 for L4 read-pattern anomalies, with the specific
        reason in ``detail``.
        """
        detail = body.get("detail", "") if isinstance(body, dict) else ""
        if status_code == 403:
            return "P5_access_control"
        if status_code in (422, 429) and str(detail).startswith("P5_"):
            return str(detail).split(".")[0].split(":")[0].strip()
        return f"P5_denied_{status_code}"

    async def _process_memory_read(self, phase: str, mr: dict, context: dict) -> dict:
        """Scripted memory read with config-appropriate enforcement (H4).

        flat          -> the store, no checks (``mechanism="none"``)
        acl_hardened  -> manifest ACL, then the store (``acl_network_layer``)
        agenticcyops  -> MMA gateway with P5 L1-L5
        Returns ``{"store", "query", "documents", "status"}`` for the
        agent's context; documents are empty on denial.
        """
        store = mr.get("store", "")
        query = mr.get("query", "")
        call_id = self._next_call_id(phase, "mem_read", f"{store}|{query}")
        if self.logger:
            self.logger.log(source=f"{phase}_agent", destination=store,
                            action="memory_read_proposed",
                            extra={"call_id": call_id, "query": query, "scripted": True})
        out = {"store": store, "query": query, "documents": [], "status": "denied"}

        if self.config == "acl_hardened":
            allowed, reason = self.enforcer.validate_memory_read(phase, store)
            if not allowed:
                if self.logger:
                    self.logger.log_memory_read(agent=f"{phase}_agent", store=store,
                                                auth_decision="deny", mechanism="acl_network_layer",
                                                extra={"call_id": call_id})
                out["reason"] = f"403: {reason}"
                return out

        bypass = self.config != "agenticcyops"
        status, body = await self._mma_post("/memory/read", {
            "phase": phase, "store_id": store, "query": query, "n_results": 3,
            "auth_token": self._mma_token(phase, store),
            "skip_p5": bypass or not self._principle_active("P5"),
        })
        if status == 0:
            if self.logger:
                self.logger.log_memory_read(agent=f"{phase}_agent", store=store,
                                            auth_decision="error", mechanism="mma_unreachable",
                                            extra={"call_id": call_id, "error": body.get("error")})
            out["status"] = "error"
            return out

        if status == 200:
            docs = body.get("documents", []) if isinstance(body, dict) else []
            metas = body.get("metadatas", []) if isinstance(body, dict) else []
            out.update({"documents": docs, "status": "ok"})
            mech = ("none" if self.config == "flat"
                    else "acl_network_layer" if self.config == "acl_hardened"
                    else "P5_access_control")
            if self.logger:
                self.logger.log_memory_read(agent=f"{phase}_agent", store=store,
                                            auth_decision="allow", mechanism=mech,
                                            num_results=len(docs), extra={"call_id": call_id},
                                            )
                # P5-L5 sanitisation evidence on the returned entries
                sanitized = sum(1 for m in metas if isinstance(m, dict) and m.get("_sanitized"))
                if sanitized or any("[REDACTED" in d for d in docs if isinstance(d, str)):
                    self.logger.log(source=f"{phase}_agent", destination=store,
                                    action="memory_read", auth_decision="allow",
                                    mechanism="P5_injection_sanitization",
                                    extra={"sanitized_entries": sanitized, "store": store,
                                           "phase": phase, "call_id": call_id})
            return out

        mech = self._p5_mechanism(status, body) if self.config == "agenticcyops" else f"store_denied_{status}"
        if self.logger:
            self.logger.log_memory_read(agent=f"{phase}_agent", store=store,
                                        auth_decision="deny", mechanism=mech,
                                        extra={"call_id": call_id})
        return out

    async def _process_memory_write(self, phase: str, mw: dict, context: dict):
        """Process a memory write with config-appropriate enforcement.

        A ``memory_write_proposed`` event precedes every check in every
        config; its ``call_id`` is carried by the resulting ``memory_write``
        event.
        """
        store_id = mw.get("store_id", "")
        content = mw.get("content", "")
        doc_id = mw.get("doc_id", f"{phase}_{store_id}_{context.get('incident_id', 'unknown')}")
        call_id = self._next_call_id(phase, "mem_write", f"{store_id}|{doc_id}|{content}")
        mem_meta = {"call_id": call_id, "doc_id": doc_id}
        if self.logger:
            import hashlib as _h
            self.logger.log(
                source=f"{phase}_agent", destination=store_id,
                action="memory_write_proposed",
                extra={**mem_meta,
                       "content_sha256": _h.sha256(str(content).encode()).hexdigest()[:16],
                       "content_len": len(str(content)),
                       "scripted": bool(mw.get("scripted", False))},
                scan_text=content,
            )

        mech_ok = ("none" if self.config == "flat"
                   else "acl_network_layer" if self.config == "acl_hardened"
                   else "P4_memory_integrity")

        if self.config == "acl_hardened":
            # ACL: manifest check but NO write-boundary filtering (P4 absent)
            allowed, reason = self.enforcer.validate_memory_write(phase, store_id)
            if not allowed:
                if self.logger:
                    self.logger.log_memory_write(
                        agent=f"{phase}_agent", store=store_id,
                        auth_decision="deny", mechanism="acl_network_layer",
                        extra=mem_meta)
                return {"status": "denied", "reason": f"403: {reason}"}

        # Every config writes to the same store through the gateway; flat and
        # acl_hardened bypass P4 / P5 (no gateway defenses in those systems).
        bypass = self.config != "agenticcyops"
        status, body = await self._mma_post("/memory/write", {
            "phase": phase,
            "store_id": store_id,
            "document": content,
            "doc_id": doc_id,
            "incident_evidence": context.get("incident", {}).get("description", ""),
            "metadata": {**(mw.get("metadata", {}) or {}),
                         "trial_id": self._trial_id() or "untagged",
                         "config": self.config},
            "auth_token": self._mma_token(phase, store_id),
            # Ablation switches -- MMA bypasses the corresponding check when
            # set.  Default (full enforcement) for agenticcyops.
            "skip_p4": bypass or not self._principle_active("P4"),
            "skip_p5": bypass or not self._principle_active("P5"),
        })
        if status == 0:
            if self.logger:
                self.logger.log_memory_write(
                    agent=f"{phase}_agent", store=store_id,
                    auth_decision="error", mechanism="mma_unreachable",
                    payload=content, extra={**mem_meta, "error": body.get("error")})
            return {"status": "mma_unreachable"}

        # Parse specific P4/P5 mechanism from the MMA response.  MMA returns
        # 403 for P5 access control, 422 for P4 memory-integrity rejection,
        # with the specific reason (e.g. P4_similarity_reject,
        # P4_drift_outlier, P4_metadata_invalid) in ``detail``.
        if status == 200:
            accepted = body.get("accepted", True) if isinstance(body, dict) else True
            sim = body.get("similarity_score", 0.0) if isinstance(body, dict) else 0.0
            mechanism = mech_ok
        else:
            accepted = False
            sim = 0.0
            detail = body.get("detail", "") if isinstance(body, dict) else ""
            if bypass:
                mechanism = f"store_denied_{status}"
            elif status == 403:
                mechanism = "P5_access_control"
            elif status == 422 and "P4_" in detail:
                mechanism = next((tok.rstrip(".,:") for tok in detail.split()
                                  if tok.startswith("P4_")), "P4_memory_integrity")
            else:
                mechanism = f"P4_denied_{status}"
        if self.logger:
            self.logger.log_memory_write(
                agent=f"{phase}_agent", store=store_id,
                auth_decision="allow" if accepted else "deny",
                mechanism=mechanism,
                cosine_similarity=sim if not bypass else None,
                payload=content, extra=mem_meta)
        return body if isinstance(body, dict) else {"status": "written"}
