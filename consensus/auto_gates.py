"""
P3-L2: Auto-Gates.
Threshold-based deterministic decisions on L1 scores.
100% symbolic — zero LLM.
"""

from typing import Optional

from logging_utils import ExperimentLogger


class AutoGates:
    """Threshold-based deterministic gate on L1 quantified scores."""

    def __init__(self, logger: Optional[ExperimentLogger] = None):
        self.logger = logger

    def evaluate(self, scores: dict) -> tuple[bool, str, dict]:
        """Apply sequential threshold checks on L1 scores.

        Args:
            scores: Dict with keys scope, reversibility, alignment,
                    precedent, proportionality (all floats 0-1).

        Returns:
            (decided, reason, details) where decided=True means auto-decided.
            When decided=True, check details["approved"] for direction.
        """
        alignment = scores.get("alignment", 0.5)
        scope = scores.get("scope", 0.0)
        reversibility = scores.get("reversibility", 0.5)
        precedent = scores.get("precedent", 0.5)
        proportionality = scores.get("proportionality", 0.5)

        # 1. Low alignment → auto-reject
        if alignment < 0.2:
            return True, "P3_auto_reject_alignment", {"approved": False}

        # 2. High scope → escalate
        if scope > 0.5:
            return True, "P3_auto_escalate_scope", {"approved": False}

        # 3. Irreversible + low proportionality → escalate
        if reversibility < 0.2 and proportionality < 0.4:
            return True, "P3_auto_escalate_irreversible", {"approved": False}

        # 4. Unprecedented + non-trivial scope → escalate
        if precedent < 0.1 and scope > 0.05:
            return True, "P3_auto_escalate_unprecedented", {"approved": False}

        # 5. All green → auto-approve
        if (alignment > 0.7
                and precedent > 0.7
                and proportionality > 0.8
                and scope < 0.05):
            return True, "P3_auto_approve_all_green", {"approved": True}

        # 6. Ambiguous → inconclusive
        return False, "P3_scores_ambiguous", {"scores": scores}
