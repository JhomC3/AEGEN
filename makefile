.PHONY: help install lint format test run-dev build push clean verify

# Variable para entorno virtual (uv lo crea por defecto como .venv)
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
UV := $(shell command -v uv 2> /dev/null) # Encuentra uv

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Crea el entorno virtual si no existe usando uv
	@if [ -z "$(UV)" ]; then \
		echo "Error: uv command not found. Please install uv: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment in $(VENV_DIR)...\"; \
		$(UV) venv $(VENV_DIR); \
		echo "Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate\"; \
	else \
		echo "Virtual environment $(VENV_DIR) already exists."; \
	fi

install: venv ## Instala dependencias de desarrollo usando uv y los lockfiles
	@echo "Installing/syncing development dependencies from lockfile..."
	$(UV) pip sync requirements-dev.lock
	@echo "Installing project in editable mode..."
	$(UV) pip install -e .

lock: venv ## Genera/Actualiza los archivos requirements.lock
	@echo "Generating requirements.lock (production)..."
	$(UV) pip compile pyproject.toml --output-file requirements.lock
	@echo "Generating requirements-dev.lock (development)..."
	$(UV) pip compile pyproject.toml --extra dev --extra test --extra lint --extra doc --output-file requirements-dev.lock

lint: ## Ejecuta linters (ruff, black check, mypy, bandit, safety)
	@echo "Running linters..."
	$(PYTHON) -m ruff check .
##	$(PYTHON) -m black --check . # Deshabilitado para evitar conflictos con ruff format # Deshabilitado para evitar conflictos con ruff format
	$(PYTHON) -m mypy src tests
	$(PYTHON) -m bandit -c pyproject.toml -r src

verify: ## Validación completa: linting + tests + architecture simple
	@echo "🎯 AEGEN Verification Suite..."
	@echo "1/3 Linting..."
	@$(MAKE) lint
	@echo "2/3 Testing..."  
	@$(MAKE) test
	@echo "3/3 Architecture..."
	@$(PYTHON) scripts/simple_check.py
	@echo "✅ All checks passed!"

verify-phase: ## Ejecuta quality gates para fase específica (LEGACY)
	@echo "🎯 Running phase quality gates: $(PHASE)"
	$(PYTHON) scripts/quality_gates.py --phase $(PHASE)

format: ## Formatea el código usando ruff
	@echo "Formatting code..."
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check . --fix

test: ## Ejecuta pruebas unitarias y de integración con pytest
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/

test-update-snapshots: ## Ejecuta pruebas y actualiza los snapshots
	@echo "Running tests and updating snapshots..."
	$(PYTHON) -m pytest tests/ --snapshot-update

coverage: test ## Ejecuta pruebas y muestra el reporte de cobertura
	@echo "Generating coverage report..."

run-dev: ## Ejecuta la aplicación en modo desarrollo usando Docker Compose
	@echo "Starting development server via Docker Compose..."
	docker-compose up --build -d # -d para detached mode

run-webhook-dev: venv ## Inicia el túnel ngrok y configura el webhook de Telegram
	@echo "Starting ngrok tunnel and setting Telegram webhook..."
	$(PYTHON) -m scripts.setup_webhook

stop-dev: ## Detiene los contenedores de desarrollo
	@echo "Stopping development containers..."
	docker-compose down

logs-dev: ## Muestra los logs de los contenedores de desarrollo
	@echo "Tailing development logs..."
	docker-compose logs -f

build: ## Construye la imagen Docker de producción
	@echo "Building production Docker image..."
	docker-compose -f docker-compose.yml build app

sync-docs: ## Sincroniza documentación con estado real del proyecto
	@echo "Synchronizing documentation with project state..."
	$(PYTHON) scripts/sync_docs.py

doctor: ## Diagnóstico completo de consistencia docs vs código
	@echo "Running project health check..."
	@echo "1. Checking git status..."
	@git status --porcelain || echo "Git issues detected"
	@echo "2. Verifying documentation sync..."
	$(PYTHON) scripts/sync_docs.py
	@echo "3. Running verification suite..."
	$(MAKE) verify
	@echo "✅ Project health check complete"

dev-check: ## Quick check durante desarrollo (solo architecture)
	@echo "⚡ Quick development check..."
	$(PYTHON) scripts/simple_check.py

status: ## Estado completo del proyecto - 3-2-1 model
	@echo "📊 AEGEN Project Status (3-2-1 Documentation Model)"
	@echo "==================================================="
	@echo "Git Branch: $$(git rev-parse --abbrev-ref HEAD)"
	@echo "Last Commit: $$(git log -1 --pretty=format:'%h - %s (%cr)')"
	@echo "Modified Files: $$(git diff --name-only | wc -l | tr -d ' ')"
	@echo ""
	@echo "📚 Documentation (3 files only):"
	@echo "   ✅ PROJECT_OVERVIEW.md - Vision & roadmap"
	@echo "   ✅ DEVELOPMENT.md - Technical guide"  
	@echo "   ✅ Makefile - Commands"
	@echo ""
	@echo "🏗️ Architecture Status:"
	$(PYTHON) scripts/simple_check.py
	@echo ""
	@echo "📋 Test Files: $$(find tests -name 'test_*.py' 2>/dev/null | wc -l | tr -d ' ')"
	@echo ""
	@echo "📚 Documentation Sync:"
	$(PYTHON) scripts/sync_docs.py

help-dev: ## Muestra comandos de desarrollo esenciales
	@echo "🚀 AEGEN Development Commands (3-2-1 Model)"
	@echo "==========================================="
	@echo "📖 Read: DEVELOPMENT.md for technical guide"
	@echo "📖 Read: PROJECT_OVERVIEW.md for vision/roadmap"
	@echo ""
	@echo "⚡ Development:"
	@echo "   make verify     - Full validation (lint+test+arch)"  
	@echo "   make dev-check  - Quick architecture check"
	@echo "   make format     - Auto-fix code style"
	@echo "   make dev        - Start development server"
	@echo ""
	@echo "📊 Status:"
	@echo "   make status     - Complete project status"
	@echo "   make sync-docs  - Update documentation"

clean: ## Elimina archivos generados (cache, venv, etc.)
	@echo "Cleaning up project..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info coverage.xml htmlcov aegen.log chromadb_dev_data
