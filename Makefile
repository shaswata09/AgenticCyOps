# DEFER -- analysis targets. None of these calls a language model.
PY ?= python

# Paper figures use the re-adjudicated local panel (Local4); set DEFER_PANEL=
# (empty) to plot the as-run Div4 values instead.
DEFER_PANEL ?= local4
export DEFER_PANEL

.PHONY: paper-tables paper-reports parse stats tables reports asb-reports figures readme-figures replay-tables b2 primaries-tables tamas-tables test freeze-check check-payloads

paper-tables: parse stats tables

# PDF reports from the generated tables (per run, consolidated, ASB panels)
paper-reports: reports asb-reports

parse:
	$(PY) -m analysis.parse_logs

stats:
	$(PY) -m analysis.statistical_tests

tables:
	$(PY) -m analysis.generate_tables

reports:
	$(PY) -m analysis.generate_reports

ASB_PANELS ?= q235_div4_div4,q235_div4_div3,q235_div4_single,q235_div4_lin3
asb-reports:
	for g in $$(echo $(ASB_PANELS) | tr ',' ' '); do $(PY) -m analysis.asb_analytics --groups $$g; done
	$(PY) -m analysis.asb_analytics --groups $(ASB_PANELS) --out-dir results/asb/asb_analytics_panels

# Paper figures: every PDF regenerated from results/ and logs/, no manual step.
# Depends on `parse` so figures and tables are built from the same all_trials.csv
# and cannot drift apart.
figures: parse
	$(PY) -m analysis.make_figures --out paper/figs
	$(MAKE) readme-figures

# The result figures shown in README.md (PNG previews written by make_figures).
README_FIGS = judgment_boundary interception_tiers ap_heatmap paired_variants ablation \
              validator_behavior panel_composition transfer channels cost state_carryover
readme-figures:
	mkdir -p docs/figures
	for f in $(README_FIGS); do cp paper/figs/preview/$$f.png docs/figures/$$f.png; done

# Every panel-dependent number in the paper, re-adjudicated from the cached
# local votes in cache/validators/ (CPU only, no model is queried).
replay-tables:
	$(PY) -m analysis.replay_tables > /dev/null
	$(PY) -c "from analysis.replay_tables import write_local4_trials, write_local_panel_csv; write_local4_trials(); write_local_panel_csv()"

# Live v2.9 calibration run vs its replay (results/b2_live.json).
b2:
	$(PY) -m analysis.b2_live > /dev/null

# The boundary for gpt-oss-120b and Llama-3.1-8B (results/primaries_v29.md,
# docs/figures/primaries_boundary.png) and TAMAS (results/tamas.md,
# docs/figures/tamas.png); both read the cached Local4 votes.
primaries-tables:
	$(PY) -m analysis.primaries_tables > /dev/null

tamas-tables:
	$(PY) -m analysis.tamas_tables > /dev/null

check-payloads:
	$(PY) -m attacks.payload_schema --validate-all
	$(PY) -m attacks.payload_schema --assert-measurable
	$(PY) -m pytest -q -p no:cacheprovider tests/test_payload_hygiene.py

test:
	$(PY) -m pytest -q

freeze-check:
	scripts/check_freeze.sh
