# AgenticCyOps revision-v2 -- analysis targets (no LLM calls)
PY ?= python

.PHONY: paper-tables parse stats tables test freeze-check

paper-tables: parse stats tables

parse:
	$(PY) -m analysis.parse_logs

stats:
	$(PY) -m analysis.statistical_tests

tables:
	$(PY) -m analysis.generate_tables

test:
	$(PY) -m pytest -q

freeze-check:
	scripts/check_freeze.sh
