.DEFAULT_GOAL := help
SHELL := /bin/bash

PYTHON      := python3.12
VENV        := .venv
BIN         := $(VENV)/bin
COMPOSE     := docker compose -f infra/docker-compose.yml --env-file .env

# Go is vendored into the repo so the build needs no sudo and no Xcode licence.
GO          := $(CURDIR)/.toolchain/go/bin/go
GOENV       := GOTOOLCHAIN=local GOPATH=$(CURDIR)/.toolchain/gopath CGO_ENABLED=0

PY_SERVICES := catalog ingest spectrum cosmology anomaly skymap tutor chat playground

# ---------------------------------------------------------------- help
.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_.-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- setup
.env: ## Create .env from the example
	@test -f .env || cp .env.example .env
	@echo "created .env — add your ADS_API_TOKEN when you get one"

$(VENV): ## Create the Python 3.12 virtualenv
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip wheel

.PHONY: setup
setup: .env $(VENV) ## Full dev setup: venv + editable installs
	$(BIN)/pip install -e "libs/cmblab-core[dev]"
	@for s in $(PY_SERVICES); do \
		if [ -f services/$$s/pyproject.toml ]; then \
			echo "--> installing services/$$s"; \
			$(BIN)/pip install -e services/$$s; \
		fi; \
	done
	@echo "done. next: make data-bootstrap"

.PHONY: bootstrap
bootstrap: ## One command: install everything, fetch the data, and start
	@$(PYTHON) scripts/dev.py bootstrap

.PHONY: toolchain
toolchain: ## Download the Go toolchain into .toolchain (no sudo required)
	@$(PYTHON) scripts/dev.py toolchain

.PHONY: node
node: ## Download the Node toolchain into .toolchain (no sudo required)
	@$(PYTHON) scripts/dev.py node

# ---------------------------------------------------------------- data
.PHONY: data-bootstrap
data-bootstrap: ## Download + clean the minimum working dataset (~170 MB)
	$(BIN)/cmblab-ingest bootstrap

.PHONY: data-list
data-list: ## Show every known archive product
	$(BIN)/cmblab-ingest list

.PHONY: spectrum
spectrum: ## Run the headline analysis on the command line
	$(BIN)/cmblab-spectrum cross wmap9 da-v1 da-v2 --mask wmap9:mask-kq75 --lmax 800

# ---------------------------------------------------------------- infra
.PHONY: infra-up
infra-up: .env ## Start Postgres + Redis + MinIO
	$(COMPOSE) up -d postgres redis minio minio-init
	@echo "postgres :5432   redis :6379   minio :9000 (console :9001)"

.PHONY: infra-down
infra-down: ## Stop infrastructure
	$(COMPOSE) down

.PHONY: infra-nuke
infra-nuke: ## Stop infrastructure AND delete all volumes (destructive)
	$(COMPOSE) down -v

.PHONY: infra-logs
infra-logs: ## Tail infrastructure logs
	$(COMPOSE) logs -f

.PHONY: migrate
migrate: ## Apply SQL migrations to a running Postgres
	@for f in infra/migrations/*.sql; do \
		echo "--> $$f"; \
		$(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 \
			-U $${POSTGRES_USER:-cmblab} -d $${POSTGRES_DB:-cmblab} < $$f; \
	done

.PHONY: psql
psql: ## Open a psql shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-cmblab} -d $${POSTGRES_DB:-cmblab}

# ---------------------------------------------------------------- services
.PHONY: up down restart status logs
up: ## Start every backend service + the gateway
	./scripts/dev.sh up

down: ## Stop everything
	./scripts/dev.sh down

restart: ## Restart everything
	./scripts/dev.sh restart

status: ## Health-check every service
	./scripts/dev.sh status

logs: ## Tail all service logs
	./scripts/dev.sh logs

.PHONY: dev-catalog dev-ingest dev-spectrum dev-cosmology dev-anomaly
.PHONY: dev-skymap dev-tutor dev-chat dev-playground
dev-catalog:    ; $(BIN)/uvicorn cmblab_catalog.main:app    --reload --port 8001
dev-spectrum:   ; $(BIN)/uvicorn cmblab_spectrum.main:app   --reload --port 8003
dev-cosmology:  ; $(BIN)/uvicorn cmblab_cosmology.main:app  --reload --port 8004
dev-anomaly:    ; $(BIN)/uvicorn cmblab_anomaly.main:app    --reload --port 8005
dev-skymap:     ; $(BIN)/uvicorn cmblab_skymap.main:app     --reload --port 8007
dev-tutor:      ; $(BIN)/uvicorn cmblab_tutor.main:app      --reload --port 8008
dev-chat:       ; $(BIN)/uvicorn cmblab_chat.main:app       --reload --port 8009
dev-playground: ; $(BIN)/uvicorn cmblab_playground.main:app --reload --port 8010

.PHONY: fit
fit: ## Run an MCMC cosmological fit on the command line (gate G5)
	$(BIN)/cmblab-cosmology fit --steps 500 --walkers 20

.PHONY: worker
worker: ## Run a Celery worker (QUEUE=ingest|spectrum|cosmology|anomaly)
	$(BIN)/celery -A cmblab_core.jobs.celery_app:app worker \
		--loglevel=INFO --concurrency=$${CONCURRENCY:-4} -Q $${QUEUE:-ingest}

.PHONY: build
build: ## Build the gateway binary and the production frontend
	@$(PYTHON) scripts/dev.py build

.PHONY: gateway
gateway: gateway-build ## Run the Go gateway
	./services/gateway/bin/gateway

.PHONY: gateway-build
gateway-build: toolchain ## Compile the Go gateway
	cd services/gateway && $(GOENV) $(GO) build -o bin/gateway ./cmd/gateway

.PHONY: gateway-test
gateway-test: toolchain ## Vet and test the gateway
	cd services/gateway && $(GOENV) $(GO) vet ./...

.PHONY: web
web: ## Run the Vite dev server
	npm --prefix web run dev

.PHONY: web-install
web-install: ## Install frontend dependencies
	npm --prefix web install

.PHONY: web-build
web-build: ## Production build of the frontend
	npm --prefix web run build

# ---------------------------------------------------------------- quality
.PHONY: test
test: ## Run the Python test suite
	$(BIN)/pytest -v

.PHONY: test-physics
test-physics: ## Run only the physics validation gates
	$(BIN)/pytest -v -m physics

.PHONY: lint
lint: ## Lint and type-check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	npm --prefix web run typecheck

.PHONY: fmt
fmt: ## Auto-format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

.PHONY: clean
clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache
