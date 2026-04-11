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
    ):
        self.domain = domain
        self.config = config
        self.llm_url = llm_url
        self.mma_url = mma_url
        self.tool_registry = tool_registry
        self.consensus = consensus
        self.agents = agents or {}
        self.logger = logger

        self.enforcer = ManifestEnforcer(domain=domain, logger=logger)
        self.handoff = PhaseHandoff(logger=logger)

        # P1 + P2-L2 + P2-L3 + P3: only instantiated for agenticcyops config
        if config == "agenticcyops":
            self.auth_interface = AuthenticatedInterface(domain=domain, logger=logger)
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
            )
        else:
            self.auth_interface = None
            self.param_validator = None
            self.output_classifier = None
            self.verified_execution = None

        self._llm = AsyncOpenAI(base_url=llm_url, api_key="unused")

    async def run_incident(self, incident: dict) -> dict:
        """Full pipeline: Monitor -> Analyze -> Admin -> Report."""
        context = {
            "incident": incident,
            "incident_id": incident.get("incident_id", str(uuid4())),
            "domain": self.domain,
            "config": self.config,
            "phases": {},
        }

        self.enforcer.reset_counts()

        # P3: Reset per-incident state
        if self.verified_execution:
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

        # Register incident status for P3-L0.5 lifecycle check (AP-11 fix)
        if self.verified_execution:
            inc_status = incident.get("incident_status", incident.get("status", "open"))
            self.verified_execution.operational_context.register_incident_status(
                context["incident_id"], inc_status)

        # Seed change_log from incident payload for AP-11 testing
        if self.verified_execution:
            recent_change = incident.get("recent_change")
            if recent_change:
                self.verified_execution.operational_context.record_change(
                    tool_id=recent_change.get("tool", recent_change.get("action", "")),
                    action=recent_change.get("action", ""),
                    target=recent_change.get("target", ""),
                    incident_id=context["incident_id"])

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
                context[f"{phase}_handoff"] = handoff_ctx

        return context

    async def run_phase(self, phase: str, context: dict) -> dict:
        """Execute a single phase with enforcement based on config."""
        agent = self.agents[phase]

        # Agent proposes actions
        try:
            result = await agent.execute(context)
        except Exception as e:
            from agents.base_agent import AgentResult
            result = AgentResult(phase=phase, summary=f"Agent error: {str(e)[:200]}")
            if self.logger:
                self.logger.log(source=f"{phase}_agent", destination="error",
                               action="agent_error", extra={"error": str(e)[:200]})

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

        # Process scripted memory ops from incident payload (for baseline verification)
        memory_ops = context.get("incident", {}).get("memory_ops", {})
        if memory_ops:
            # Scripted reads for this phase
            for mr in memory_ops.get("reads", []):
                if mr.get("phase") == phase and self.config == "agenticcyops":
                    try:
                        async with httpx.AsyncClient() as client:
                            import hashlib as _hl
                            import hmac as _hm
                            _key_path = BASE_DIR / "configs" / "hmac_key.txt"
                            _tok = ""
                            if _key_path.exists():
                                _k = _key_path.read_text().strip()
                                _tok = _hm.new(_k.encode(),
                                    f"{phase}:{mr['store']}".encode(),
                                    _hl.sha256).hexdigest()[:16]
                            resp = await client.post(
                                f"{self.mma_url}/memory/read",
                                json={"phase": phase, "store_id": mr["store"],
                                      "query": mr.get("query", ""), "n_results": 3,
                                      "auth_token": _tok},
                                timeout=10)
                            # Log ALL memory reads for baseline verification
                            if self.logger:
                                self.logger.log(
                                    source=f"{phase}_agent",
                                    destination=mr["store"],
                                    action="memory_read",
                                    auth_decision="allow" if resp.status_code == 200 else "deny",
                                    mechanism="P5_access_control",
                                )
                            # AP-14 fix: Log sanitization events from read results
                            if resp.status_code == 200 and self.logger:
                                try:
                                    read_data = resp.json()
                                    docs = read_data.get("documents", [])
                                    metas = read_data.get("metadatas", [])
                                    sanitized_count = sum(
                                        1 for m in metas
                                        if isinstance(m, dict) and m.get("_sanitized")
                                    )
                                    if sanitized_count > 0 or any(
                                        "[REDACTED" in d for d in docs if isinstance(d, str)
                                    ):
                                        self.logger.log(
                                            source=f"{phase}_agent",
                                            destination=mr["store"],
                                            action="memory_read",
                                            auth_decision="allow",
                                            mechanism="P5_injection_sanitization",
                                            extra={
                                                "sanitized_entries": sanitized_count,
                                                "store": mr["store"],
                                                "phase": phase,
                                            },
                                        )
                                except Exception:
                                    pass
                    except Exception:
                        pass  # MMA unreachable — logged at gateway level

            # Scripted writes for this phase
            for mw in memory_ops.get("writes", []):
                if mw.get("phase") == phase:
                    await self._process_memory_write(phase, {
                        "store_id": mw["store"],
                        "content": mw.get("content", ""),
                        "metadata": mw.get("metadata", {}),
                        "doc_id": f"{phase}_{mw['store']}_{context.get('incident_id', 'unknown')}",
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

    async def _process_tool_call(self, phase: str, tc, context: dict) -> dict:
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
                    )
                return {"status": "denied", "tool_id": tool_id, "reason": f"403: {reason}"}

        elif self.config == "agenticcyops":
            # ── Step 1: P1-L1 — Component identity ──
            if self.auth_interface:
                verified, reason = self.auth_interface.verify_component(tool_id, "tools")
                if not verified:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P1_authenticated_interface",
                            interception_step=1)
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(reason)}

            # ── Step 2: P2-L1 — Manifest enforcement ──
            allowed, reason = self.enforcer.validate_tool_call(phase, tool_id)
            if not allowed:
                if self.logger:
                    self.logger.log_tool_call(
                        agent=f"{phase}_agent",
                        tool=tool_id,
                        auth_decision="deny",
                        mechanism="P2_capability_scoping",
                        interception_step=2,
                    )
                return {"status": "denied", "tool_id": tool_id,
                        "reason": self._sanitize_reason(reason)}

            # ── Step 3: P2-L2 — Parameter validation ──
            if self.param_validator:
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
                            extra={"p2l2_reason": p_reason, **p_details},
                        )
                    return {"status": "denied", "tool_id": tool_id,
                            "reason": self._sanitize_reason(p_reason)}

        # P3: Verified Execution — full multi-layer pipeline (agenticcyops only)
        # Fix #1: Force P3 for negative-impact tools regardless of requires_consensus
        _p3_approved_at = None  # Fix L7: reliable variable init (not dir())
        if self.config == "agenticcyops" and self.verified_execution:
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
                        )
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

        # ── Post-execution checks (agenticcyops only) ──
        if self.config == "agenticcyops":
            # ── Step 6: P1-L2 — Response integrity ──
            if self.auth_interface and isinstance(response, dict):
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
                            extra={"p1l2_reason": resp_reason},
                        )
                    return {"status": "response_rejected", "tool_id": tool_id,
                            "reason": "Response validation failed."}

            # ── Step 6b: P3-L7 — Execution verification (Fix #3) ──
            # Compare approved proposal against what was actually executed
            # (same tc object — hash match verifies no TOCTOU modification)
            if self.verified_execution and _p3_approved_at is not None:
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
                            extra={"l7_reason": l7_reason},
                        )
                    return {"status": "execution_mismatch", "tool_id": tool_id,
                            "reason": "Execution verification failed."}

            # ── Step 7: P2-L3 — Output classification (Fix #8: actual redaction) ──
            if self.output_classifier and isinstance(response, dict):
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
                            extra={"p2l3_reason": class_reason, **class_details},
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
            )

        return response

    async def _process_memory_write(self, phase: str, mw: dict, context: dict):
        """Process a memory write with config-appropriate enforcement."""
        store_id = mw.get("store_id", "")
        content = mw.get("content", "")

        if self.config == "agenticcyops":
            # Route through MMA gateway with auth token (Fix #7)
            import hashlib as _hashlib
            import hmac as _hmac_mod
            auth_token = ""
            hmac_key_path = BASE_DIR / "configs" / "hmac_key.txt"
            if hmac_key_path.exists():
                _key = hmac_key_path.read_text().strip()
                auth_token = _hmac_mod.new(
                    _key.encode(), f"{phase}:{store_id}".encode(), _hashlib.sha256
                ).hexdigest()[:16]

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.mma_url}/memory/write",
                        json={
                            "phase": phase,
                            "store_id": store_id,
                            "document": content,
                            "doc_id": mw.get("doc_id", f"{phase}_{store_id}_{context.get('incident_id', 'unknown')}"),
                            "incident_evidence": context.get("incident", {}).get("description", ""),
                            "metadata": mw.get("metadata", {}),
                            "auth_token": auth_token,
                        },
                        timeout=10,
                    )
                    result = resp.json()
                    # Log memory write for baseline verification
                    if self.logger:
                        accepted = result.get("accepted", resp.status_code == 200)
                        sim = result.get("similarity_score", 0.0)
                        self.logger.log_memory_write(
                            agent=f"{phase}_agent",
                            store=store_id,
                            auth_decision="allow" if accepted else "deny",
                            mechanism="P4_memory_integrity",
                            cosine_similarity=sim,
                        )
                    return result
            except Exception:
                return {"status": "mma_unreachable"}

        elif self.config == "acl_hardened":
            # ACL: Check access but NO write-boundary filtering (P4 absent)
            allowed, reason = self.enforcer.validate_memory_write(phase, store_id)
            if not allowed:
                if self.logger:
                    self.logger.log_memory_write(
                        agent=f"{phase}_agent",
                        store=store_id,
                        auth_decision="deny",
                        mechanism="acl_network_layer",
                    )
                return {"status": "denied", "reason": f"403: {reason}"}

        # flat config or acl_hardened allowed — write directly (no P4 filtering)
        if self.logger:
            self.logger.log_memory_write(
                agent=f"{phase}_agent",
                store=store_id,
                auth_decision="allow",
                mechanism="none" if self.config == "flat" else "acl_network_layer",
            )
        return {"status": "written"}
