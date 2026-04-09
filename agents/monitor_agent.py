"""Monitor/Triage phase agent. Thin wrapper around BaseAgent."""

from agents.base_agent import BaseAgent


class MonitorAgent(BaseAgent):
    def __init__(self, domain: str, **kwargs):
        super().__init__(phase="monitor", domain=domain, **kwargs)
