"""
Domain-agnostic LLM-powered phase agent.

Each agent loads its system prompt and tool schemas from the domain config,
uses the primary LLM to reason and propose tool calls, and returns
structured output for handoff.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from openai import OpenAI

from config import BASE_DIR
from logging_utils import ExperimentLogger


@dataclass
class ToolCallProposal:
    tool_id: str
    arguments: dict
    justification: str = ""

    def to_proposal(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "arguments": self.arguments,
            "justification": self.justification,
        }


@dataclass
class AgentResult:
    phase: str
    proposed_tool_calls: list[ToolCallProposal] = field(default_factory=list)
    tool_responses: list[dict] = field(default_factory=list)
    reasoning: str = ""
    summary: str = ""
    memory_reads: list[dict] = field(default_factory=list)
    memory_writes: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    tokens_prompt: int = 0
    tokens_completion: int = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "proposed_tool_calls": [tc.to_proposal() for tc in self.proposed_tool_calls],
            "tool_responses": self.tool_responses,
            "reasoning": self.reasoning,
            "summary": self.summary,
            "memory_reads": self.memory_reads,
            "memory_writes": self.memory_writes,
            "latency_ms": self.latency_ms,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
        }


class BaseAgent:
    """Domain-agnostic LLM-powered agent for a single phase."""

    def __init__(
        self,
        phase: str,
        domain: str,
        config: str = "agenticcyops",
        llm_url: str = "http://localhost:8000/v1",
        manifest: Optional[dict] = None,
        tool_schemas: Optional[list[dict]] = None,
        all_tool_schemas: Optional[list[dict]] = None,
        logger: Optional[ExperimentLogger] = None,
    ):
        self.phase = phase
        self.domain = domain
        self.config = config
        self.llm_url = llm_url
        self.manifest = manifest or {}
        self.tool_schemas = tool_schemas or []
        self.all_tool_schemas = all_tool_schemas or []
        self.logger = logger

        self._client = OpenAI(base_url=llm_url, api_key="unused")
        self._model_name = None  # auto-detected from vLLM
        self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        path = BASE_DIR / "domains" / self.domain / "prompts" / f"{self.phase}.txt"
        if path.exists():
            return path.read_text().strip()
        return f"You are a {self.phase} agent. Analyze the input and propose actions."

    def _detect_model(self):
        if self._model_name is None:
            try:
                models = self._client.models.list()
                if models.data:
                    self._model_name = models.data[0].id
            except Exception:
                pass
            if self._model_name is None:
                self._model_name = "default"

    def switch_model(self, url: str):
        """Switch LLM endpoint (for diversity checks)."""
        self.llm_url = url
        self._client = OpenAI(base_url=url, api_key="unused")
        self._model_name = None

    def _format_context(self, context: dict) -> str:
        """Build user message from incident context and prior phase outputs."""
        parts = []

        incident = context.get("incident", {})
        parts.append("## Incident")
        parts.append(json.dumps(incident, indent=2, default=str))

        # Include prior phase handoffs
        for phase in ("monitor", "analyze", "admin"):
            handoff_key = f"{phase}_handoff"
            if handoff_key in context:
                hd = context[handoff_key]
                parts.append(f"\n## {phase.title()} Phase Results")
                parts.append(hd.get("phase_summary", "No summary available."))
                if hd.get("tool_results"):
                    parts.append(f"Tool results: {json.dumps(hd['tool_results'][:5], default=str)}")

        return "\n\n".join(parts)

    def get_tools_for_llm(self) -> Optional[list[dict]]:
        """Return tool schemas based on config.

        CRITICAL: This controls what the agent can even TRY to call.
        - flat/acl_hardened: Agent sees ALL tools (can attempt out-of-scope calls)
        - agenticcyops: Agent sees ONLY manifest tools (doesn't know others exist)
        """
        if self.config in ("flat", "acl_hardened"):
            return self.all_tool_schemas or self.tool_schemas or None
        else:
            return self.tool_schemas or None

    async def execute(self, context: dict) -> AgentResult:
        """Reason about the task and propose tool calls."""
        import time
        self._detect_model()

        user_message = self._format_context(context)
        tools = self.get_tools_for_llm()

        kwargs = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        start = time.perf_counter()
        response = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        # Extract token usage
        tokens_prompt = 0
        tokens_completion = 0
        if response.usage:
            tokens_prompt = response.usage.prompt_tokens or 0
            tokens_completion = response.usage.completion_tokens or 0

        # Log the LLM call
        if self.logger:
            self.logger.log(
                source=f"{self.phase}_agent",
                destination="llm",
                action="llm_call",
                auth_decision="allow",
                latency_ms=latency_ms,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                extra={
                    "model": self._model_name,
                    "tools_visible": len(tools) if tools else 0,
                    "config": self.config,
                },
            )

        result = self._parse_response(response)
        result.latency_ms = latency_ms
        result.tokens_prompt = tokens_prompt
        result.tokens_completion = tokens_completion
        return result

    def _parse_response(self, response) -> AgentResult:
        """Parse LLM response into AgentResult."""
        message = response.choices[0].message
        result = AgentResult(phase=self.phase)

        # Extract reasoning/content
        content = message.content or ""
        result.reasoning = content

        # Try to parse JSON from content
        try:
            parsed = json.loads(content)
            result.summary = parsed.get("triage_summary",
                             parsed.get("response_summary",
                             parsed.get("summary", content[:200])))
            # Extract memory write proposals
            for key in ("memory_writes", "proposed_writes"):
                if key in parsed:
                    result.memory_writes = parsed[key]
        except (json.JSONDecodeError, TypeError):
            result.summary = content[:200] if content else "No content"

        # Extract tool calls
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                result.proposed_tool_calls.append(
                    ToolCallProposal(
                        tool_id=tc.function.name,
                        arguments=args,
                        justification=f"LLM proposed: {tc.function.name}",
                    )
                )

        return result
