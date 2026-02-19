.PHONY: test cov lint fmt check

test:                            ## Run all tests
	.venv/bin/python -m pytest tests/ -v

cov:                             ## Run tests with coverage report
	.venv/bin/python -m pytest tests/ -v --cov=packages --cov-report=term-missing

lint:                            ## Check lint and formatting
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

fmt:                             ## Auto-fix lint and format
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .

check:                           ## Lint + test (pre-push)
	$(MAKE) lint && $(MAKE) test
