"""
P3-L2: Auto-Gates.
Threshold-based deterministic decisions on L1 scores.
100% symbolic — zero LLM.
"""

from typing import Optional

from logging_utils import ExperimentLogger


class AutoGates:
    """Threshold-based deterministic gate on L1 quantified scores.

    ``mode`` selects the auto-approve rule (the deny and escalate rules are
    identical in every mode, so no configuration can make the gate *less*
    safe than the deployed one):

    ``default``
        The shipped rule: all four scores must be green
        (alignment > 0.7, precedent > 0.7, proportionality > 0.8, scope < 0.05).
        Across every recorded run this never fired once, so the deterministic
        gate has never approved anything.
    ``permissive`` (E16)
        ``alignment > 0.5 and scope < 0.2`` -- deliberately loose enough to
        fire on ordinary benign proposals, so the cost of deterministic
        approval can be measured at all.
    ``noautoapprove`` (E1)
        The auto-approve rule is removed, so every proposal that is not denied
        or escalated reaches the panel.
    """

    MODES = ("default", "permissive", "noautoapprove")

    def __init__(self, logger: Optional[ExperimentLogger] = None,
                 mode: str = "default"):
        if mode not in self.MODES:
            raise ValueError(f"unknown AutoGates mode {mode!r}; expected one of {self.MODES}")
        self.logger = logger
        self.mode = mode

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

        # 5. Auto-approve (the only rule that varies by mode)
        if self.mode == "permissive":
            # E16: loose enough to actually fire, so the cost of deterministic
            # approval is measurable rather than hypothetical.
            if alignment > 0.5 and scope < 0.2:
                return True, "P3_auto_approve_permissive", {"approved": True}
        elif self.mode == "default":
            if (alignment > 0.7
                    and precedent > 0.7
                    and proportionality > 0.8
                    and scope < 0.05):
                return True, "P3_auto_approve_all_green", {"approved": True}
        # mode == "noautoapprove" (E1): fall through to the panel

        # 6. Ambiguous → inconclusive (the panel decides)
        #
        # Logged because it is the only record of what the L1 scorer actually
        # produces. Without it the gate's thresholds can only be guessed: E16
        # set a deliberately loose auto-approve rule (alignment > 0.5 and
        # scope < 0.2) and it still never fired on any proposal, and there was
        # no way to see why. The decided paths already log via
        # VerifiedExecution._log_decision; this covers the fall-through.
        if self.logger:
            self.logger.log(
                source="auto_gates", destination="P3_L2", action="P3_L2_scores",
                auth_decision="inconclusive", mechanism="P3_scores_ambiguous",
                extra={"mode": self.mode,
                       **{k: round(float(v), 4) for k, v in scores.items()
                          if isinstance(v, (int, float))}},
            )
        return False, "P3_scores_ambiguous", {"scores": scores}
