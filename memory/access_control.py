"""
P5: Phase-Partitioned Memory Access Control

Enforces which NIST-IR phases (monitor, analyze, admin, report) can
read or write to which memory stores (M1-M12).

Policy is loaded from:
    domains/{domain}/configs/access_policy.json

Format:
    {
        "monitor": {"read": ["M1","M4"], "write": []},
        "analyze": {"read": ["M1","M2","M6","M7"], "write": ["M1","M6"]},
        ...
    }

Usage:
    from memory.access_control import AccessController

    ac = AccessController(domain="cyberops")
    ac.can_read("monitor", "M1")   # True
    ac.can_write("monitor", "M1")  # False
"""

import json
from pathlib import Path

from config import BASE_DIR


class AccessController:
    """P5: Phase-partitioned memory access.

    Reads policy from domains/{domain}/configs/access_policy.json.
    Returns False for any unknown phase or store_id.
    """

    def __init__(self, domain: str, configs_dir: str | Path | None = None):
        """
        Args:
            domain: Domain identifier (e.g. "cyberops").
            configs_dir: Override path to the configs directory.
                         Defaults to BASE_DIR / "domains" / domain / "configs".
        """
        if configs_dir is None:
            configs_dir = BASE_DIR / "domains" / domain / "configs"
        else:
            configs_dir = Path(configs_dir)

        policy_path = configs_dir / "access_policy.json"
        with open(policy_path, "r") as f:
            self._policy: dict = json.load(f)

        self.domain = domain

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def can_read(self, phase: str, store_id: str) -> bool:
        """Check if *phase* is allowed to read from *store_id*.

        Args:
            phase: NIST-IR phase name (monitor, analyze, admin, report).
            store_id: Memory store identifier (M1-M12).

        Returns:
            True if the policy explicitly grants read access, False otherwise.
        """
        phase_policy = self._policy.get(phase)
        if phase_policy is None:
            return False
        return store_id in phase_policy.get("read", [])

    def can_write(self, phase: str, store_id: str) -> bool:
        """Check if *phase* is allowed to write to *store_id*.

        Args:
            phase: NIST-IR phase name (monitor, analyze, admin, report).
            store_id: Memory store identifier (M1-M12).

        Returns:
            True if the policy explicitly grants write access, False otherwise.
        """
        phase_policy = self._policy.get(phase)
        if phase_policy is None:
            return False
        return store_id in phase_policy.get("write", [])

    def accessible_stores(self, phase: str, mode: str = "read") -> list[str]:
        """Return list of store IDs accessible to *phase* for the given mode.

        Args:
            phase: NIST-IR phase name.
            mode: "read" or "write".

        Returns:
            List of store IDs, or empty list for unknown phase/mode.
        """
        phase_policy = self._policy.get(phase)
        if phase_policy is None:
            return []
        return list(phase_policy.get(mode, []))
