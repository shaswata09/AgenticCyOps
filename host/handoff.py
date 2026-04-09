"""
Inter-phase context passing.

Packages each phase's outputs into structured context for the next phase.
Domain-agnostic — works with any agent output format.
"""

from datetime import datetime, timezone
from typing import Optional

from logging_utils import ExperimentLogger


class PhaseHandoff:
    """Manages inter-phase context passing."""

    def __init__(self, logger: Optional[ExperimentLogger] = None):
        self.logger = logger

    def create_handoff(
        self,
        source_phase: str,
        target_phase: str,
        phase_output: dict,
        incident_context: dict,
    ) -> dict:
        """Package phase output as enriched context for the next phase.

        Args:
            source_phase: Phase that just completed ("monitor", "analyze", etc.)
            target_phase: Phase about to start
            phase_output: The completed phase's AgentResult as dict
            incident_context: Running incident context
        """
        handoff = {
            "source_phase": source_phase,
            "target_phase": target_phase,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident_id": incident_context.get("incident_id"),
            "phase_summary": phase_output.get("summary", ""),
            "phase_reasoning": phase_output.get("reasoning", ""),
            "tool_results": phase_output.get("tool_responses", []),
            "memory_reads": phase_output.get("memory_reads", []),
            "prior_phases": {},
        }

        # Include summaries from all prior phases
        for phase, data in incident_context.get("phases", {}).items():
            if isinstance(data, dict):
                handoff["prior_phases"][phase] = data.get("summary", "")

        if self.logger:
            self.logger.log_agent_handoff(
                from_agent=f"{source_phase}_agent",
                to_agent=f"{target_phase}_agent",
                phase_from=source_phase,
                phase_to=target_phase,
            )

        return handoff

    def get_handoff_summary(self, handoff: dict) -> str:
        """Return a concise text summary for logging."""
        src = handoff.get("source_phase", "?")
        tgt = handoff.get("target_phase", "?")
        summary = handoff.get("phase_summary", "no summary")
        n_tools = len(handoff.get("tool_results", []))
        return f"[{src} -> {tgt}] {summary} ({n_tools} tool results)"
