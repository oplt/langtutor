.PHONY: start local-dev docker-dev prod-dev fix check backend-lint backend-typecheck backend-import-check backend-tests backend-integration-tests backend-guardrails backend-quality frontend-quality frontend-tests frontend-e2e install-hooks commit-ready
.PHONY: kill-dev kill-ports kill-workers reset-dev reset-frontend-cache
.PHONY: start-maple stop-maple observability-status start-observability-stack stop-observability-stack local-dev-no-observability


PYTHON ?= $(if $(wildcard $(CURDIR)/backend/.venv/bin/python),$(CURDIR)/backend/.venv/bin/python,$(if $(wildcard $(CURDIR)/.venv/bin/python),$(CURDIR)/.venv/bin/python,python3))
export PYTHONPATH := $(CURDIR)
BACKEND_QUALITY_PATHS := backend/app backend/tests

start: local-dev

local-dev:
	$(MAKE) -f Makefile.local local-dev

docker-dev:
	@test -f Makefile.docker || { echo "Makefile.docker not found. Use 'make start' or add Makefile.docker."; exit 1; }
	$(MAKE) -f Makefile.docker docker-dev

prod-dev:
	@test -f Makefile.deploy || { echo "Makefile.deploy not found. Use 'make start' or add Makefile.deploy."; exit 1; }
	$(MAKE) -f Makefile.deploy prod-dev

fix:
	cd backend && $(PYTHON) -m ruff check app tests --fix
	cd backend && $(PYTHON) -m ruff format app tests
	cd frontend && npm run lint -- --fix

check:
	$(MAKE) backend-quality
	$(MAKE) frontend-quality
	$(MAKE) frontend-tests

backend-lint:
	@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		cd backend && $(PYTHON) -m ruff format --check tests && $(PYTHON) -m ruff check app tests; \
	else \
		echo "ruff is not installed for $(PYTHON); run: pip install -r backend/requirements-dev.txt"; \
		exit 1; \
	fi

backend-typecheck:
	@if $(PYTHON) -m mypy --version >/dev/null 2>&1; then \
		cd backend && $(PYTHON) -m mypy app/core/background.py; \
	else \
		echo "mypy is not installed for $(PYTHON); run: pip install -r backend/requirements-dev.txt"; \
		exit 1; \
	fi

backend-import-check:
	cd backend && $(PYTHON) -m compileall -q app

backend-tests:
	@if [ -d backend/tests ]; then \
		cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest tests -m "not integration"; \
	else \
		echo "backend/tests not found; skipping backend tests."; \
		exit 1; \
	fi

backend-integration-tests:
	@if [ -d backend/tests ]; then \
		cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest tests -m integration; \
	else \
		echo "backend/tests not found; skipping backend integration tests."; \
		exit 1; \
	fi

backend-guardrails:
	$(MAKE) PYTHON=$(PYTHON) backend-typecheck
	$(MAKE) PYTHON=$(PYTHON) backend-tests

backend-quality: backend-lint backend-import-check backend-guardrails

frontend-quality:
	cd frontend && npm run build
	cd frontend && npm run lint

frontend-tests:
	cd frontend && npm run test

frontend-e2e:
	cd frontend && npm run test:e2e:install --if-present
	cd frontend && npm run test:e2e --if-present

install-hooks:
	pre-commit install

commit-ready: fix check

kill-dev kill-ports kill-workers reset-dev reset-frontend-cache start-maple stop-maple observability-status start-observability-stack stop-observability-stack local-dev-no-observability:
	$(MAKE) -f Makefile.local $@
