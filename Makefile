# AgenticCyOps revision-v2 -- analysis targets (no LLM calls)
PY ?= python

.PHONY: paper-tables paper-reports parse stats tables reports asb-reports figures test freeze-check check-payloads

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

check-payloads:
	$(PY) -m attacks.payload_schema --validate-all
	$(PY) -m attacks.payload_schema --assert-measurable
	$(PY) -m pytest -q -p no:cacheprovider tests/test_payload_hygiene.py

test:
	$(PY) -m pytest -q

freeze-check:
	scripts/check_freeze.sh
