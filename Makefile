.PHONY: run metrics clean-traces clean-notes clean-memory reset-data

run:
	python main.py

metrics:
	python scripts/report_metrics.py

clean-traces:
	rm -f data/traces.jsonl

clean-notes:
	rm -rf data/notes
	mkdir -p data/notes
	touch data/notes/.gitkeep

clean-memory:
	rm -f data/memory.json

reset-data:
	rm -rf data
	mkdir -p data/notes
	touch data/.gitkeep
	touch data/notes/.gitkeep