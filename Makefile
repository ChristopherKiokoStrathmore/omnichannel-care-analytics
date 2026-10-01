.PHONY: install test run

install:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

run:
	python scripts/run_analysis.py
