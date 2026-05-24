"""
Two evaluator loops:

  evaluate_filter_defense  — for D1, D2, D3, D7 (defenses that scan
                             untrusted text and emit a block/pass verdict).
  evaluate_prompt_defense  — for D4, D5, D6 (defenses that modify the
                             system prompt; requires a target LLM to
                             determine whether the modified prompt deters
                             the malicious tool call).

Both loops share the same loop structure and emit identically-shaped
result records so downstream metrics/plotting code is uniform.
"""

from pathlib import Path
from typing import Callable

from .attack_loader import (
    load_attack_payloads,
    extract_untrusted_spans,
    build_attack_user_message,
)
from .attack_categories import category
from .log_writer import DefenseEvalLogger


def evaluate_filter_defense(
    domain: str,
    defense_id: str,
    defense_fn: Callable,
    log_dir: Path | str,
    n_trials: int = 3,
    aps: list[str] | None = None,
    extra_meta: dict | None = None,
    payloads_subdir: str = "payloads",
) -> tuple[list[dict], Path]:
    """
    Run a filter-style defense across all (AP, variant, trial) combinations.

    Args:
        defense_fn:      (text, kind, ctx) -> (blocked: bool, info: dict)
                         'blocked=True' means the defense flagged the text as
                         malicious and would have prevented the agent from
                         ingesting it.
        payloads_subdir: Which payload directory under domains/<DOMAIN>/ to
                         read from. Default 'payloads' (original dataset);
                         pass 'optimized_payloads_v1' for adaptive variants.

    Returns:
        (results, log_path) where results is a list of per-trial dicts
        ready for metrics.compute_per_ap_bypass / plotting.
    """
    meta = dict(extra_meta or {})
    meta.setdefault("payloads_subdir", payloads_subdir)
    logger = DefenseEvalLogger(log_dir, defense_id, domain, extra_meta=meta)
    payloads = load_attack_payloads(domain, payloads_subdir=payloads_subdir)
    if aps:
        payloads = [p for p in payloads if p["_ap"] in aps]

    results = []
    try:
        for p in payloads:
            ap = p["_ap"]
            variant = p.get("variant_id") or p.get("name", "v?")
            spans = extract_untrusted_spans(p)

            for trial in range(n_trials):
                if not spans:
                    # No textual surface — defense has nothing to scan.
                    # Structural APs (6, 12, 13, 15) commonly fall here.
                    blocked = False
                    span_info = []
                    reason = "no_untrusted_spans"
                else:
                    span_info = []
                    blocked_any = False
                    for s in spans:
                        try:
                            blk, info = defense_fn(s["text"], s["field"],
                                                   {"ap": ap, "variant": variant})
                        except Exception as e:
                            blk, info = False, {"error": str(e)[:200]}
                        if blk:
                            blocked_any = True
                        span_info.append({"field": s["field"], "blocked": blk, **info})
                    blocked = blocked_any
                    reason = "filter_decision"

                cat = category(ap)
                logger.log(
                    action="trial",
                    ap=ap, variant=variant, trial=trial,
                    blocked=blocked, category=cat,
                    reason=reason, spans=span_info,
                    n_spans=len(spans),
                )
                results.append({
                    "ap": ap, "variant": variant, "trial": trial,
                    "blocked": blocked, "category": cat,
                    "n_spans": len(spans),
                })
    finally:
        logger.close()

    return results, logger.path


def evaluate_prompt_defense(
    domain: str,
    defense_id: str,
    build_messages_fn: Callable,
    call_target_llm_fn: Callable,
    is_malicious_response_fn: Callable,
    log_dir: Path | str,
    n_trials: int = 3,
    aps: list[str] | None = None,
    extra_meta: dict | None = None,
    payloads_subdir: str = "payloads",
) -> tuple[list[dict], Path]:
    """
    Run a prompt-modification defense.

    Args:
        build_messages_fn:        (payload, attack_msg) -> list[dict]
                                  Constructs the (system, user) messages
                                  with the defense's modification applied.
        call_target_llm_fn:       (messages) -> str (raw LLM completion)
        is_malicious_response_fn: (completion, payload) -> bool
                                  True if the LLM emitted (or accepted)
                                  the malicious tool call. In that case
                                  the defense FAILED (bypass=True).
        payloads_subdir:          Which payload directory under
                                  domains/<DOMAIN>/ to read from. Default
                                  'payloads' (original); pass
                                  'optimized_payloads_v1' for adaptive
                                  variants.

    Returns: same shape as evaluate_filter_defense.
    """
    meta = dict(extra_meta or {})
    meta.setdefault("payloads_subdir", payloads_subdir)
    logger = DefenseEvalLogger(log_dir, defense_id, domain, extra_meta=meta)
    payloads = load_attack_payloads(domain, payloads_subdir=payloads_subdir)
    if aps:
        payloads = [p for p in payloads if p["_ap"] in aps]

    results = []
    try:
        for p in payloads:
            ap = p["_ap"]
            variant = p.get("variant_id") or p.get("name", "v?")
            attack_msg = build_attack_user_message(p)

            for trial in range(n_trials):
                try:
                    messages = build_messages_fn(p, attack_msg)
                    completion = call_target_llm_fn(messages)
                    malicious = is_malicious_response_fn(completion, p)
                    blocked = not malicious   # if LLM did NOT comply, defense held
                    info = {"completion_excerpt": completion[:500]}
                except Exception as e:
                    blocked = False
                    info = {"error": str(e)[:200]}

                cat = category(ap)
                logger.log(
                    action="trial",
                    ap=ap, variant=variant, trial=trial,
                    blocked=blocked, category=cat,
                    **info,
                )
                results.append({
                    "ap": ap, "variant": variant, "trial": trial,
                    "blocked": blocked, "category": cat,
                })
    finally:
        logger.close()

    return results, logger.path
