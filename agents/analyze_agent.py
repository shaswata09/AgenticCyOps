"""Investigation/Analysis phase agent. Thin wrapper around BaseAgent."""

from agents.base_agent import BaseAgent


class AnalyzeAgent(BaseAgent):
    def __init__(self, domain: str, **kwargs):
        super().__init__(phase="analyze", domain=domain, **kwargs)
