"""
SOAR Host Orchestrator.

Central coordinator that routes incidents through 4 phases sequentially.
Domain-agnostic — loads configs/tools/prompts from domains/{domain}/.

Config modes:
  "flat":           No enforcement. Agents call anything directly.
  "acl_hardened":   Manifest enforcement (P2) only. No consensus/MMA.
  "agenticcyops":   Full P1-P5 enforcement.
"""

import json
from typing import Optional
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from config import BASE_DIR
from logging_utils import ExperimentLogger
from host.manifest_enforcer import ManifestEnforcer
from host.handoff import PhaseHandoff
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
        result = await agent.execute(context)

        # Process proposed tool calls
        executed_responses = []
        for tc in result.proposed_tool_calls:
            response = await self._process_tool_call(phase, tc, context)
            executed_responses.append(response)
            self.enforcer.record_action(phase)

        result.tool_responses = executed_responses

        # Process proposed memory writes
        for mw in result.memory_writes:
            await self._process_memory_write(phase, mw, context)

        return result.to_dict()

    async def _process_tool_call(self, phase: str, tc, context: dict) -> dict:
        """Process a tool call with config-appropriate enforcement."""
        tool_id = tc.tool_id

        # P2: Manifest check (skip for flat config)
        if self.config in ("acl_hardened", "agenticcyops"):
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
                return {"status": "denied", "tool_id": tool_id, "reason": reason}

        # P3: Consensus check (agenticcyops only)
        if self.config == "agenticcyops" and self.consensus:
            if self.enforcer.requires_consensus(phase, tool_id):
                approved = await self.consensus.validate(
                    tc.to_proposal(), context
                )
                if not approved:
                    if self.logger:
                        self.logger.log_tool_call(
                            agent=f"{phase}_agent",
                            tool=tool_id,
                            auth_decision="deny",
                            mechanism="P3_verified_execution",
                            interception_step=2,
                        )
                    return {"status": "denied", "tool_id": tool_id, "reason": "consensus_rejected"}

            # Bulk action check
            count = self.enforcer._action_counts.get(phase, 0)
            if self.enforcer.check_bulk_action(phase, count):
                if self.logger:
                    self.logger.log_escalation(
                        source=f"{phase}_agent",
                        reason=f"Bulk action threshold exceeded ({count} actions)",
                        severity="high",
                    )
                return {"status": "escalated", "tool_id": tool_id, "reason": "bulk_action_threshold"}

        # Execute tool
        if self.tool_registry:
            response = await self.tool_registry.call_tool(
                tool_id, tc.arguments, source=f"{phase}_agent"
            )
        else:
            response = {"status": "no_registry", "tool_id": tool_id}

        if self.logger:
            self.logger.log_tool_call(
                agent=f"{phase}_agent",
                tool=tool_id,
                auth_decision="allow",
                mechanism="P2_capability_scoping" if self.config != "flat" else "none",
            )

        return response

    async def _process_memory_write(self, phase: str, mw: dict, context: dict):
        """Process a memory write with config-appropriate enforcement."""
        store_id = mw.get("store_id", "")
        content = mw.get("content", "")

        if self.config == "agenticcyops":
            # Route through MMA gateway
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
                        },
                        timeout=10,
                    )
                    return resp.json()
            except Exception:
                return {"status": "mma_unreachable"}

        elif self.config == "acl_hardened":
            allowed, reason = self.enforcer.validate_memory_write(phase, store_id)
            if not allowed:
                if self.logger:
                    self.logger.log_memory_write(
                        agent=f"{phase}_agent",
                        store=store_id,
                        auth_decision="deny",
                        mechanism="P5_access_control",
                    )
                return {"status": "denied", "reason": reason}

        # flat config or allowed — write directly (would use ChromaDB directly in real impl)
        if self.logger:
            self.logger.log_memory_write(
                agent=f"{phase}_agent",
                store=store_id,
                auth_decision="allow",
                mechanism="none" if self.config == "flat" else "P5_access_control",
            )
        return {"status": "written"}
