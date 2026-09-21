"""Payload schema (H5): what the model sees vs. what the harness knows.

A variant has two halves::

    {
      "variant_id": "ap3_v1", "name": ..., "description": ...,
      "trigger":   { ... the incident as the SOC would receive it ... },
      "memory_ops": { "reads": [...], "writes": [...] },        # scripted ops
      "meta": {
        "channel": "alert_text" | "tool_response" | "memory" | "handoff"
                   | "proposal_justification",
        "attacker_phase": "admin",
        "canaries": ["CANARY-..."],
        "injection": { ...channel-specific delivery spec... },
        "legacy": { ...keys moved out of the trigger, kept for reference... }
      },
      "success_criteria": { "attacker_phase": ..., "effects": [...] }
    }

``trigger`` (plus ``memory_ops``, which the host strips before rendering)
is the only part handed to the host; ``meta`` is never shown to a model.
``meta.injection`` is delivered by the harness through the named channel:

``tool_response``          ``{"tool": id, "response": {...}, "mode": "merge"|"replace",
                             "calls": n}`` -> ``POST /inject`` on the tool stub.
``memory``                 ``{"store": id, "content": str, "doc_id": str,
                             "metadata": {...}}`` (or ``"entries": [...]``)
                           -> pre-seeded through the gateway with ``harness_seed``.
``handoff``                ``{"from_phase": p, "fields": {...}, "append_summary": str}``
                           -> merged into that phase's handoff by the host.
``proposal_justification`` ``{"phase": p, "tool": id, "arguments": {...},
                             "justification": str}`` (or ``"proposals": [...]``)
                           -> appended to that phase's proposals by the host.
``alert_text``             nothing to deliver: the content is in the trigger.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from config import BASE_DIR

CHANNELS = ("alert_text", "tool_response", "memory", "handoff", "proposal_justification")
PHASES = ("monitor", "analyze", "admin", "report")

# Tool names payloads used before the registry ids were settled.  The
# harness resolves them on delivery and the oracle on scoring; payloads
# should name the registered id directly (T1).
TOOL_ALIASES = {"T11_edr": "T11_epp_av", "T6_siem": "T6_siem_search"}


def resolve_tool(tool_id: Any, registry_ports: Iterable[str] | dict) -> Optional[str]:
    """Registered tool id for ``tool_id``, or ``None``.

    Applies :data:`TOOL_ALIASES`, strips a trailing ``_response`` (the AP-2
    payloads named the *response* of the tool), and checks the result
    against the registry's tool ids (``ServerRegistry._ports`` or any
    iterable of ids).
    """
    if not tool_id:
        return None
    known = set(registry_ports.keys() if isinstance(registry_ports, dict) else registry_ports)
    t = str(tool_id)
    for cand in (t, TOOL_ALIASES.get(t, t)):
        if cand in known:
            return cand
    if t.endswith("_response"):
        base = t[: -len("_response")]
        for cand in (base, TOOL_ALIASES.get(base, base)):
            if cand in known:
                return cand
    return None


@functools.lru_cache(maxsize=None)
def registered_tools(domain: str) -> frozenset:
    """Tool ids the domain's server registry serves (loaded once)."""
    from mcp_servers.server_registry import ServerRegistry
    reg = ServerRegistry(domain=domain, logger=None)
    reg.load_tools()
    reg.assign_ports(9000)
    return frozenset(reg._ports)


def load_variants(domain: str, ap: str) -> list[dict]:
    path = BASE_DIR / "domains" / domain / "payloads" / f"{ap}_variants.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("variants", [])


def meta_of(payload: dict) -> dict:
    m = payload.get("meta")
    return m if isinstance(m, dict) else {}


def split_payload(payload: dict) -> tuple[dict, dict]:
    """``(trigger_for_host, meta)``.

    The trigger carries ``memory_ops`` (scripted reads / writes the host
    performs; the agent never sees them) and nothing from ``meta``.
    """
    trigger = payload.get("trigger", payload)
    trigger = dict(trigger) if isinstance(trigger, dict) else {"description": str(trigger)}
    trigger.pop("meta", None)
    if "memory_ops" in payload:
        trigger["memory_ops"] = payload["memory_ops"]
    return trigger, meta_of(payload)


def injection_of(payload: dict) -> dict:
    inj = meta_of(payload).get("injection")
    inj = dict(inj) if isinstance(inj, dict) else {}
    ap = meta_of(payload).get("attacker_phase")
    if ap and "attacker_phase" not in inj:
        inj["attacker_phase"] = ap
    return inj


def validate_payload(payload: dict, domain: Optional[str] = None) -> list[str]:
    """Schema problems of one variant (empty list when well-formed).

    With ``domain`` the ``tool_response`` tool must resolve to a tool the
    domain's registry serves (an unresolved tool is never delivered).
    """
    problems = []
    meta = meta_of(payload)
    if not meta:
        problems.append("missing meta block")
        return problems
    ch = meta.get("channel")
    if ch not in CHANNELS:
        problems.append(f"channel {ch!r} not in {CHANNELS}")
    ap = meta.get("attacker_phase")
    if ap not in PHASES and ap != "none":
        problems.append(f"attacker_phase {ap!r} not an agent phase")
    if not isinstance(meta.get("canaries", []), list):
        problems.append("canaries must be a list")
    inj = meta.get("injection") or {}
    if ch == "tool_response" and not (inj.get("tool") and "response" in inj):
        problems.append("tool_response channel needs injection.tool and injection.response")
    elif ch == "tool_response" and domain:
        known = registered_tools(domain)
        if inj.get("tool") not in known:
            resolved = resolve_tool(inj.get("tool"), known)
            problems.append(f"tool_response tool {inj.get('tool')!r} is not a registered {domain} tool"
                            + (f" (alias of {resolved!r}: name it directly)" if resolved else ""))
    if ch == "memory" and not (inj.get("entries") or (inj.get("store") and inj.get("content"))):
        problems.append("memory channel needs injection.store+content or injection.entries")
    if ch == "handoff" and not isinstance(inj.get("handoff"), dict):
        problems.append("handoff channel needs injection.handoff")
    if ch == "proposal_justification" and not (inj.get("proposal") or inj.get("proposals")):
        problems.append("proposal_justification channel needs injection.proposal(s)")
    sc = payload.get("success_criteria")
    if not isinstance(sc, dict) or "effects" not in sc:
        problems.append("success_criteria.effects missing")
    return problems


def memory_seed_entries(injection: dict) -> list[dict]:
    """Normalised list of ``{store, content, doc_id, metadata}`` to pre-seed."""
    out = []
    entries = injection.get("entries")
    if isinstance(entries, list):
        out.extend(e for e in entries if isinstance(e, dict))
    elif injection.get("store") and injection.get("content"):
        out.append({k: injection.get(k) for k in ("store", "content", "doc_id", "metadata", "phase")})
    norm = []
    for i, e in enumerate(out):
        if not (e.get("store") and e.get("content")):
            continue
        norm.append({
            "store": str(e["store"]), "content": str(e["content"]),
            "doc_id": str(e.get("doc_id") or f"seed_{i}"),
            "metadata": dict(e.get("metadata") or {}),
            "phase": str(e.get("phase") or "analyze"),
        })
    return norm
