"""Adaptive (GCG) attack generation + evaluation.

Against each downloaded local primary agent model we run greedy
coordinate gradient (GCG) to produce adversarial suffix strings that
maximise the probability the target model emits the attacker tool
call in response to a poisoned InjecAgent case.  We then re-run the
benchmark with the suffixed attack text to measure adaptive ASR and
delta vs the static baseline.

Workflow
========

1. ``representative_subset.py``  selects a stratified 50-case subset of
   the 1,054 base InjecAgent cases, balanced across the 17 attack
   categories.
2. ``gcg_runner.py`` loads a target model via HuggingFace, runs GCG
   per case for a configurable number of steps, and saves the
   adversarial suffix + loss curve.
3. ``run_adaptive.py`` constructs adversarial versions of each case
   (suffix appended to the attacker-instruction text), then routes
   them through the existing ``DefensePipeline`` to measure adaptive
   ASR for every (domain, config) pair.
4. Optional transfer-attack step: the suffixes generated against
   Llama-4-Scout / Qwen3-235B are evaluated against GLM-4.7-FP8 in
   inference mode only.
"""
