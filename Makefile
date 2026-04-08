.PHONY: lint typecheck test docs-build docs-dev corpus-fetch corpus-parse

lint:
	cd dwg2json && ruff check .

typecheck:
	cd dwg2json && mypy src/dwg2json

test:
	cd dwg2json && pytest --cov=dwg2json --cov-report=term-missing

docs-build:
	cd docs && npm ci && npm run docs:build

docs-dev:
	cd docs && npm run docs:dev

corpus-fetch:
	python scripts/fetch_libredwg_test_dwgs.py --dest local_dwg_samples

corpus-parse:
	python scripts/batch_parse_dwgs.py --root local_dwg_samples --out-report local_dwg_samples/parse_report.json
