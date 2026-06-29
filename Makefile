PYTHON ?= $(if $(wildcard $(CURDIR)/backend/.venv/bin/python),$(CURDIR)/backend/.venv/bin/python,$(if $(wildcard $(CURDIR)/.venv/bin/python),$(CURDIR)/.venv/bin/python,python3))
APP_PYTHON ?= $(PYTHON)
APP_HOST ?= localhost
APP_PORT ?= 8000
FRONTEND_HOST ?= localhost
FRONTEND_PORT ?= 5173
REDIS_PORT ?= 6380
OPEN_BROWSER ?= 1
RUN_MIGRATIONS ?= 1
SIM_MODE ?= 1
HONCHO ?= $(if $(wildcard $(CURDIR)/backend/.venv/bin/honcho),$(CURDIR)/backend/.venv/bin/honcho,$(if $(wildcard $(CURDIR)/.venv/bin/honcho),$(CURDIR)/.venv/bin/honcho,$(if $(wildcard $(HOME)/.local/bin/honcho),$(HOME)/.local/bin/honcho,honcho)))
BACKEND_ENV ?= $(CURDIR)/backend/.env

# Local LLM servers started by `make local-dev`.
# Disable with RUN_LLAMA_CPP=0 or RUN_OLLAMA=0 when you do not need them.
RUN_LLAMA_CPP ?= 1
RUN_OLLAMA ?= 1
LLAMA_CPP_HOST ?= 127.0.0.1
LLAMA_CPP_PORT ?= 8081
LLAMA_CPP_BIN ?= /home/polat/Desktop/Projects/llama.cpp/build/bin/llama-server
LLAMA_CPP_MODEL ?= /home/polat/Desktop/Projects/llama.cpp/models/Qwen_Qwen3-14B-Q4_K_M.gguf
LLAMA_CPP_CTX ?= 4096
LLAMA_CPP_NGL ?= 40
OLLAMA_HOST_ADDR ?= 127.0.0.1
OLLAMA_PORT ?= 11434
OLLAMA_HOST ?= $(OLLAMA_HOST_ADDR):$(OLLAMA_PORT)

SYSTEMCTL ?= systemctl
SUDO ?= sudo

APP_ENV ?= local

# Do not load backend/.env into every Honcho process by default.
# The backend should load its own settings; loading backend/.env globally can break local auth cookies.
HONCHO_ENV_ARGS ?=

PYTHONNOUSERSITE ?= 1
PYTHONDONTWRITEBYTECODE ?= 1

export APP_PYTHON
export APP_HOST
export APP_PORT
export FRONTEND_HOST
export FRONTEND_PORT
export REDIS_PORT
export RUN_MIGRATIONS
export SIM_MODE
export RUN_LLAMA_CPP
export RUN_OLLAMA
export LLAMA_CPP_HOST
export LLAMA_CPP_PORT
export LLAMA_CPP_BIN
export LLAMA_CPP_MODEL
export LLAMA_CPP_CTX
export LLAMA_CPP_NGL
export OLLAMA_HOST
export OLLAMA_PORT


DEV_PROCS := redis
# ifeq ($(RUN_LLAMA_CPP),1)
# DEV_PROCS += llama_cpp
# endif
ifeq ($(RUN_OLLAMA),1)
DEV_PROCS += ollama
endif
DEV_PROCS += backend frontend
ifeq ($(OPEN_BROWSER),1)
DEV_PROCS += browser
endif

.PHONY: local-dev check-local-tools kill-dev kill-ports kill-workers reset-frontend-cache reset-dev

local-dev: check-local-tools kill-dev
	$(HONCHO) $(HONCHO_ENV_ARGS) -f Procfile.dev start $(DEV_PROCS)

local-dev-with-backend-env:
	$(MAKE) -f Makefile.local local-dev HONCHO_ENV_ARGS="-e $(BACKEND_ENV)"

local-dev-no-observability:
	$(MAKE) -f Makefile.local local-dev

check-local-tools:
	@$(HONCHO) --help >/dev/null 2>&1 || { echo "honcho executable is not usable: $(HONCHO). Reinstall with: $(PYTHON) -m pip install --force-reinstall honcho"; exit 1; }
	@$(APP_PYTHON) -c 'import uvicorn, fastapi, alembic' >/dev/null 2>&1 || { echo "Backend Python deps missing for $(APP_PYTHON). Install backend requirements."; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "npm is not installed."; exit 1; }
	@command -v redis-server >/dev/null 2>&1 || { echo "redis-server is required."; exit 1; }
ifeq ($(RUN_LLAMA_CPP),1)
	@test -x "$(LLAMA_CPP_BIN)" || { echo "llama.cpp server binary is not executable: $(LLAMA_CPP_BIN). Set LLAMA_CPP_BIN=... or run: make local-dev RUN_LLAMA_CPP=0"; exit 1; }
	@test -f "$(LLAMA_CPP_MODEL)" || { echo "llama.cpp model not found: $(LLAMA_CPP_MODEL). Set LLAMA_CPP_MODEL=... or run: make local-dev RUN_LLAMA_CPP=0"; exit 1; }
endif
ifeq ($(RUN_OLLAMA),1)
	@command -v ollama >/dev/null 2>&1 || { echo "ollama is required. Install Ollama or run: make local-dev RUN_OLLAMA=0"; exit 1; }
endif

kill-ports:
	@for port in $(APP_PORT) $(FRONTEND_PORT) $(REDIS_PORT) $(LLAMA_CPP_PORT) $(OLLAMA_PORT); do \
		pids="$$(lsof -ti tcp:$$port 2>/dev/null || true)"; \
		if [ -n "$$pids" ]; then \
			echo "[kill-ports] killing tcp:$$port pids=$$pids"; \
			kill $$pids 2>/dev/null || true; \
			sleep 0.3; \
			kill -9 $$pids 2>/dev/null || true; \
		fi; \
	done
	@pgrep -f '[g]st-launch-1.0' | xargs -r kill 2>/dev/null || true
	@sleep 0.3
	@pgrep -f '[g]st-launch-1.0' | xargs -r kill -9 2>/dev/null || true
	@pgrep -f '[f]fplay' | xargs -r kill 2>/dev/null || true
	@sleep 0.3
	@pgrep -f '[f]fplay' | xargs -r kill -9 2>/dev/null || true

kill-dev:
	-pgrep -f "[h]oncho .*Procfile.dev start" | xargs -r kill
	-pgrep -f "[u]vicorn backend.app.main:app" | xargs -r kill
	-pgrep -f "[r]edis-server --port $(REDIS_PORT)" | xargs -r kill
	-pgrep -f "[l]lama-server.*--port $(LLAMA_CPP_PORT)" | xargs -r kill
	-sleep 1
	-pgrep -f "[h]oncho .*Procfile.dev start" | xargs -r kill -9
	-pgrep -f "[u]vicorn backend.app.main:app" | xargs -r kill -9
	-pgrep -f "[r]edis-server --port $(REDIS_PORT)" | xargs -r kill -9
	-pgrep -f "[l]lama-server.*--port $(LLAMA_CPP_PORT)" | xargs -r kill -9
	-$(MAKE) -f Makefile.local kill-ports

kill-workers:
	-pgrep -f "[c]elery.*backend.entrypoints.workers.celery_app" | xargs -r kill
	-sleep 1
	-pgrep -f "[c]elery.*backend.entrypoints.workers.celery_app" | xargs -r kill -9

reset-frontend-cache:
	rm -rf frontend/node_modules/.vite

reset-dev: kill-dev kill-workers reset-frontend-cache