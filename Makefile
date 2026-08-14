PYTHON ?= python

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make run                   Run the desktop assistant"
	@echo "  make metrics               Print runtime metrics"
	@echo "  make test                  Run all unit tests"
	@echo "  make test-evaluation       Run evaluation unit tests"
	@echo "  make eval-validate         Validate eval case JSONL files"
	@echo "  make eval-case CASE=id     Run one eval case"
	@echo "  make eval-case-report CASE=id"
	@echo "  make eval-routing          Run routing eval suite"
	@echo "  make eval-skills           Run skills eval suite"
	@echo "  make eval-tools            Run tools eval suite"
	@echo "  make eval-recovery         Run recovery eval suite"
	@echo "  make eval-regression       Run regression eval suite"
	@echo "  make eval-all              Run all eval cases"
	@echo "  make eval-all-judge        Run all eval cases with LLM judge"
	@echo "  make eval-latest-report    Print latest eval failure report"
	@echo "  make check                 Run core validation checks"
	@echo "  make clean-traces          Remove trace log"
	@echo "  make clean-notes           Remove generated notes"
	@echo "  make clean-memory          Remove memory file"
	@echo "  make reset-data            Reset data directory"
	@echo "  make eval-baseline NAME=name"
	@echo "  make eval-compare BASELINE=path"
	@echo "  make eval-compare-print BASELINE=path"
	@echo "  make eval-mcp              Run MCP eval suite"

.PHONY: run
run:
	$(PYTHON) main.py

.PHONY: metrics
metrics:
	$(PYTHON) scripts/report_metrics.py

.PHONY: test
test:
	$(PYTHON) -m unittest discover -s tests -v

.PHONY: test-evaluation
test-evaluation:
	$(PYTHON) -m unittest discover -s tests/evaluation -v

.PHONY: eval-validate
eval-validate:
	$(PYTHON) scripts/validate_evals.py

.PHONY: eval-case
eval-case:
	@test -n "$(CASE)" || (echo "Usage: make eval-case CASE=case_id" && exit 1)
	$(PYTHON) scripts/run_evals.py --case-id $(CASE)

.PHONY: eval-case-report
eval-case-report:
	@test -n "$(CASE)" || (echo "Usage: make eval-case-report CASE=case_id" && exit 1)
	$(PYTHON) scripts/run_evals.py --case-id $(CASE) --print-failure-report

.PHONY: eval-routing
eval-routing:
	$(PYTHON) scripts/run_evals.py --suite routing

.PHONY: eval-skills
eval-skills:
	$(PYTHON) scripts/run_evals.py --suite skills

.PHONY: eval-tools
eval-tools:
	$(PYTHON) scripts/run_evals.py --suite tools

.PHONY: eval-recovery
eval-recovery:
	$(PYTHON) scripts/run_evals.py --suite recovery

.PHONY: eval-regression
eval-regression:
	$(PYTHON) scripts/run_evals.py --suite regression

.PHONY: eval-all
eval-all:
	$(PYTHON) scripts/run_evals.py

.PHONY: eval-all-judge
eval-all-judge:
	$(PYTHON) scripts/run_evals.py --judge

.PHONY: eval-latest-report
eval-latest-report:
	$(PYTHON) scripts/analyze_eval_failures.py --latest --print

.PHONY: check
check:
	$(PYTHON) -m py_compile \
		app/evaluation/models.py \
		app/evaluation/results.py \
		app/evaluation/snapshot.py \
		app/evaluation/scorers.py \
		app/evaluation/completion.py \
		app/evaluation/grounding.py \
		app/evaluation/failure_analysis.py \
		app/evaluation/judge.py \
		scripts/validate_evals.py \
		scripts/run_evals.py \
		scripts/eval_worker.py \
		scripts/analyze_eval_failures.py \
		app/tools/mock_mcp_tools.py
		app/mcp/provider.py \
		app/mcp/mock_provider.py \
		app/mcp/real_provider.py \
		app/mcp/server_config.py \
		app/mcp/factory.py \
		app/mcp/diagnostics.py \
		scripts/mcp_discover.py \
	$(PYTHON) scripts/validate_evals.py
	$(PYTHON) -m unittest discover -s tests/evaluation -v

.PHONY: clean-traces
clean-traces:
	rm -f data/traces.jsonl

.PHONY: clean-notes
clean-notes:
	rm -rf data/notes
	mkdir -p data/notes
	touch data/notes/.gitkeep

.PHONY: clean-memory
clean-memory:
	rm -f data/memory.json

.PHONY: reset-data
reset-data:
	rm -rf data
	mkdir -p data/notes
	touch data/.gitkeep
	touch data/notes/.gitkeep

.PHONY: eval-baseline
eval-baseline:
	@test -n "$(NAME)" || (echo "Usage: make eval-baseline NAME=baseline_name" && exit 1)
	$(PYTHON) scripts/create_eval_baseline.py --latest --name $(NAME)

.PHONY: eval-baseline-print
eval-baseline-print:
	@test -n "$(NAME)" || (echo "Usage: make eval-baseline-print NAME=baseline_name" && exit 1)
	$(PYTHON) scripts/create_eval_baseline.py --latest --name $(NAME) --print

.PHONY: eval-compare
eval-compare:
	@test -n "$(BASELINE)" || (echo "Usage: make eval-compare BASELINE=path/to/baseline.json" && exit 1)
	$(PYTHON) scripts/compare_eval_reports.py --baseline $(BASELINE) --latest

.PHONY: eval-compare-print
eval-compare-print:
	@test -n "$(BASELINE)" || (echo "Usage: make eval-compare-print BASELINE=path/to/baseline.json" && exit 1)
	$(PYTHON) scripts/compare_eval_reports.py --baseline $(BASELINE) --latest --print

.PHONY: eval-compare-strict
eval-compare-strict:
	@test -n "$(BASELINE)" || (echo "Usage: make eval-compare-strict BASELINE=path/to/baseline.json" && exit 1)
	$(PYTHON) scripts/compare_eval_reports.py --baseline $(BASELINE) --latest --fail-on-regression
.PHONY: eval-mcp
eval-mcp:
	$(PYTHON) scripts/run_evals.py --suite mcp