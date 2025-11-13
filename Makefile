# AIXN Blockchain - Makefile
# Convenience commands for Docker operations

.PHONY: help build up down restart logs clean test

# Default target
.DEFAULT_GOAL := help

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build

up: ## Start all services
	@echo "$(GREEN)Starting AIXN Blockchain stack...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started. Access:$(NC)"
	@echo "  - API: http://localhost:8080"
	@echo "  - Explorer: http://localhost:8082"
	@echo "  - Grafana: http://localhost:3000"

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-node: ## View logs from AIXN node
	docker-compose logs -f aixn-node

logs-db: ## View logs from PostgreSQL
	docker-compose logs -f postgres

##@ Testnet

testnet-up: ## Start testnet with multiple nodes
	@echo "$(GREEN)Starting AIXN testnet...$(NC)"
	cd docker/testnet && docker-compose up -d

testnet-down: ## Stop testnet
	@echo "$(YELLOW)Stopping testnet...$(NC)"
	cd docker/testnet && docker-compose down

testnet-logs: ## View testnet logs
	cd docker/testnet && docker-compose logs -f

##@ Database

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U aixn -d aixn_blockchain

db-backup: ## Backup database
	@echo "$(GREEN)Backing up database...$(NC)"
	mkdir -p backups
	docker-compose exec -T postgres pg_dump -U aixn aixn_blockchain > backups/db-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "$(GREEN)Backup completed$(NC)"

db-restore: ## Restore database from backup (Usage: make db-restore BACKUP=filename.sql)
	@echo "$(YELLOW)Restoring database from $(BACKUP)...$(NC)"
	cat backups/$(BACKUP) | docker-compose exec -T postgres psql -U aixn aixn_blockchain
	@echo "$(GREEN)Database restored$(NC)"

##@ Maintenance

clean: ## Remove stopped containers and unused images
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f

clean-all: ## Remove all Docker resources (including volumes)
	@echo "$(RED)WARNING: This will delete all blockchain data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -af --volumes; \
		echo "$(GREEN)Cleanup completed$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

ps: ## Show running containers
	docker-compose ps

stats: ## Show container resource usage
	docker stats $(shell docker-compose ps -q)

##@ Testing

test: ## Run tests in container
	@echo "$(GREEN)Running tests...$(NC)"
	docker-compose exec aixn-node pytest tests/

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	docker-compose exec aixn-node pytest tests/integration/

test-security: ## Run security tests
	@echo "$(GREEN)Running security tests...$(NC)"
	docker-compose exec aixn-node pytest tests/security/

##@ Monitoring

monitor: ## Open Grafana dashboard
	@echo "$(GREEN)Opening Grafana...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3000 || \
	command -v open >/dev/null 2>&1 && open http://localhost:3000 || \
	echo "Please open http://localhost:3000 in your browser"

prometheus: ## Open Prometheus
	@echo "$(GREEN)Opening Prometheus...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:9091 || \
	command -v open >/dev/null 2>&1 && open http://localhost:9091 || \
	echo "Please open http://localhost:9091 in your browser"

explorer: ## Open Block Explorer
	@echo "$(GREEN)Opening Block Explorer...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8082 || \
	command -v open >/dev/null 2>&1 && open http://localhost:8082 || \
	echo "Please open http://localhost:8082 in your browser"

##@ Health

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@docker-compose ps
	@echo ""
	@echo "Node API:"
	@curl -s http://localhost:8080/health | jq '.' || echo "$(RED)Node API not responding$(NC)"
	@echo ""
	@echo "Database:"
	@docker-compose exec postgres pg_isready -U aixn || echo "$(RED)Database not ready$(NC)"
	@echo ""
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "$(RED)Redis not ready$(NC)"

##@ Production

prod-up: ## Start production stack with nginx
	@echo "$(GREEN)Starting production stack...$(NC)"
	docker-compose --profile production up -d

prod-deploy: ## Deploy production (build + up)
	@echo "$(GREEN)Deploying to production...$(NC)"
	docker-compose --profile production build
	docker-compose --profile production up -d
	@echo "$(GREEN)Production deployment completed$(NC)"

prod-logs: ## View production logs
	docker-compose --profile production logs -f

##@ Backup & Restore

backup: ## Full backup (blockchain + database)
	@echo "$(GREEN)Creating full backup...$(NC)"
	mkdir -p backups
	@echo "Backing up database..."
	docker-compose exec -T postgres pg_dump -U aixn aixn_blockchain > backups/db-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "Backing up blockchain data..."
	docker run --rm -v crypto_blockchain-data:/data -v $(PWD)/backups:/backup ubuntu tar czf /backup/blockchain-$(shell date +%Y%m%d-%H%M%S).tar.gz /data
	@echo "$(GREEN)Backup completed$(NC)"

restore: ## Restore from backup (interactive)
	@echo "$(YELLOW)Available backups:$(NC)"
	@ls -lh backups/
	@echo ""
	@echo "$(YELLOW)To restore:$(NC)"
	@echo "  Database: make db-restore BACKUP=filename.sql"
	@echo "  Blockchain: docker run --rm -v crypto_blockchain-data:/data -v \$$(PWD)/backups:/backup ubuntu tar xzf /backup/filename.tar.gz -C /"

##@ Development Tools

shell: ## Open shell in node container
	docker-compose exec aixn-node /bin/bash

shell-db: ## Open shell in database container
	docker-compose exec postgres /bin/bash

install-deps: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	pip install -r requirements-dev.txt

format: ## Format code with black
	@echo "$(GREEN)Formatting Python code...$(NC)"
	docker-compose exec aixn-node black src/

lint: ## Lint code with pylint
	@echo "$(GREEN)Linting code...$(NC)"
	docker-compose exec aixn-node pylint src/

type-check: ## Run type checking with mypy
	@echo "$(GREEN)Type checking...$(NC)"
	docker-compose exec aixn-node mypy src/

##@ Information

version: ## Show Docker and Docker Compose versions
	@docker --version
	@docker-compose --version

config: ## Validate and view docker-compose configuration
	docker-compose config

network: ## Show Docker network information
	docker network ls
	@echo ""
	docker network inspect crypto_aixn-network || true

volumes: ## Show Docker volumes
	docker volume ls | grep crypto

# Python interpreter
PYTHON := python
PIP := pip

# Project directories
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs

# Virtual environment
VENV := venv
VENV_BIN := $(VENV)/Scripts
ifeq ($(OS),Windows_NT)
    ACTIVATE := $(VENV_BIN)/activate.bat
else
    VENV_BIN := $(VENV)/bin
    ACTIVATE := source $(VENV_BIN)/activate
endif

##@ Setup and Installation

.PHONY: install
install: ## Install project dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	@echo "✓ Dependencies installed"

.PHONY: install-dev
install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e ".[dev,blockchain,ai]"
	@echo "✓ Development dependencies installed"

.PHONY: venv
venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "✓ Virtual environment created at $(VENV)"
	@echo "  Activate with: $(ACTIVATE)"

.PHONY: setup
setup: venv install-dev pre-commit-install ## Full development environment setup
	@echo "✓ Development environment setup complete"

##@ Code Quality

.PHONY: format
format: ## Format code with black and isort
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)
	@echo "✓ Code formatted"

.PHONY: lint
lint: ## Run all linters (pylint, flake8, mypy)
	@echo "Running Pylint..."
	-$(PYTHON) -m pylint $(SRC_DIR)
	@echo "\nRunning Flake8..."
	-$(PYTHON) -m flake8 $(SRC_DIR)
	@echo "\nRunning MyPy..."
	-$(PYTHON) -m mypy $(SRC_DIR)
	@echo "✓ Linting complete"

.PHONY: pylint
pylint: ## Run pylint only
	$(PYTHON) -m pylint $(SRC_DIR)

.PHONY: flake8
flake8: ## Run flake8 only
	$(PYTHON) -m flake8 $(SRC_DIR)

.PHONY: mypy
mypy: ## Run mypy type checking only
	$(PYTHON) -m mypy $(SRC_DIR)

.PHONY: check
check: format lint ## Format and lint code

##@ Security

.PHONY: security
security: ## Run all security checks
	@echo "Running Bandit security scan..."
	-$(PYTHON) -m bandit -r $(SRC_DIR) -ll
	@echo "\nChecking dependencies with Safety..."
	-$(PYTHON) -m safety check
	@echo "\nRunning pip-audit..."
	-$(PYTHON) -m pip_audit
	@echo "✓ Security checks complete"

.PHONY: bandit
bandit: ## Run bandit security scanner
	$(PYTHON) -m bandit -r $(SRC_DIR) -ll

.PHONY: safety
safety: ## Check dependencies for vulnerabilities
	$(PYTHON) -m safety check

.PHONY: audit
audit: ## Audit pip packages for vulnerabilities
	$(PYTHON) -m pip_audit

##@ Testing

.PHONY: test
test: ## Run all tests
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	$(PYTHON) -m pytest $(TEST_DIR)/unit -v

.PHONY: test-integration
test-integration: ## Run integration tests only
	$(PYTHON) -m pytest $(TEST_DIR)/integration -v

.PHONY: test-security
test-security: ## Run security tests only
	$(PYTHON) -m pytest $(TEST_DIR)/security -v -m security

.PHONY: test-performance
test-performance: ## Run performance tests only
	$(PYTHON) -m pytest $(TEST_DIR)/performance -v -m performance

.PHONY: test-fast
test-fast: ## Run tests excluding slow tests
	$(PYTHON) -m pytest $(TEST_DIR) -v -m "not slow"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing

.PHONY: coverage-html
coverage-html: test-coverage ## Generate HTML coverage report and open it
	@echo "✓ Coverage report generated at htmlcov/index.html"

##@ Pre-commit Hooks

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	$(PYTHON) -m pre_commit install
	$(PYTHON) -m pre_commit install --hook-type commit-msg
	@echo "✓ Pre-commit hooks installed"

.PHONY: pre-commit-uninstall
pre-commit-uninstall: ## Uninstall pre-commit hooks
	$(PYTHON) -m pre_commit uninstall
	$(PYTHON) -m pre_commit uninstall --hook-type commit-msg
	@echo "✓ Pre-commit hooks uninstalled"

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	$(PYTHON) -m pre_commit run --all-files

.PHONY: pre-commit-update
pre-commit-update: ## Update pre-commit hooks to latest versions
	$(PYTHON) -m pre_commit autoupdate

##@ Documentation

.PHONY: docs
docs: ## Build documentation with Sphinx
	cd $(DOCS_DIR) && $(MAKE) html
	@echo "✓ Documentation built at $(DOCS_DIR)/_build/html/index.html"

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	cd $(DOCS_DIR)/_build/html && $(PYTHON) -m http.server 8000

.PHONY: docs-clean
docs-clean: ## Clean documentation build files
	cd $(DOCS_DIR) && $(MAKE) clean

##@ Blockchain Operations

.PHONY: node
node: ## Start blockchain node
	$(PYTHON) -m src.aixn.core.node

.PHONY: explorer
explorer: ## Start block explorer
	$(PYTHON) -m src.aixn.block_explorer

.PHONY: wallet
wallet: ## Start wallet CLI
	$(PYTHON) -m src.aixn.core.wallet

.PHONY: mine
mine: ## Start mining
	$(PYTHON) scripts/aixn_scripts/start_mining.py

.PHONY: testnet
testnet: ## Initialize and start testnet
	$(PYTHON) scripts/aixn_scripts/initialize_wallets.py
	$(PYTHON) scripts/aixn_scripts/premine_blockchain.py
	$(PYTHON) -m src.aixn.core.node --testnet

##@ Docker Operations

.PHONY: docker-build
docker-build: ## Build Docker image
	docker build -t aixn-blockchain:latest .

.PHONY: docker-run
docker-run: ## Run Docker container
	docker run -p 8333:8333 -p 8080:8080 aixn-blockchain:latest

.PHONY: docker-compose-up
docker-compose-up: ## Start all services with docker-compose
	docker-compose up -d

.PHONY: docker-compose-down
docker-compose-down: ## Stop all services with docker-compose
	docker-compose down

.PHONY: docker-compose-logs
docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

##@ Database Operations

.PHONY: db-backup
db-backup: ## Backup blockchain data
	@mkdir -p backups
	@echo "Creating backup..."
	@tar -czf backups/blockchain-backup-$$(date +%Y%m%d-%H%M%S).tar.gz src/aixn/data/
	@echo "✓ Backup created in backups/"

.PHONY: db-restore
db-restore: ## Restore blockchain data (requires BACKUP_FILE variable)
	@test -n "$(BACKUP_FILE)" || (echo "Error: BACKUP_FILE not specified. Use: make db-restore BACKUP_FILE=<file>" && exit 1)
	@echo "Restoring from $(BACKUP_FILE)..."
	@tar -xzf $(BACKUP_FILE) -C .
	@echo "✓ Backup restored"

##@ Monitoring

.PHONY: metrics
metrics: ## Start Prometheus metrics endpoint
	$(PYTHON) -m src.aixn.core.monitoring

.PHONY: logs
logs: ## Tail application logs
	tail -f src/aixn/logs/*.log

.PHONY: health-check
health-check: ## Check node health status
	curl -f http://localhost:8080/health || echo "Node is not responding"

##@ Cleanup

.PHONY: clean
clean: ## Remove build artifacts and cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ .tox/ *.egg
	@echo "✓ Cleaned build artifacts and cache files"

.PHONY: clean-logs
clean-logs: ## Remove log files
	rm -rf src/aixn/logs/*.log
	@echo "✓ Log files removed"

.PHONY: clean-data
clean-data: ## Remove blockchain data (WARNING: destructive)
	@echo "WARNING: This will delete all blockchain data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf src/aixn/data/blockchain/*; \
		echo "✓ Blockchain data removed"; \
	else \
		echo "Cancelled"; \
	fi

.PHONY: clean-all
clean-all: clean clean-logs ## Deep clean (artifacts, cache, logs)
	@echo "✓ Deep clean complete"

##@ Development Utilities

.PHONY: deps-update
deps-update: ## Update all dependencies to latest versions
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) list --outdated
	@echo "Review outdated packages above, then run: pip install --upgrade <package>"

.PHONY: deps-tree
deps-tree: ## Show dependency tree
	$(PIP) install pipdeptree
	pipdeptree

.PHONY: shell
shell: ## Start Python interactive shell with project context
	$(PYTHON) -i -c "from src.aixn.core import *; print('AIXN Shell Ready')"

.PHONY: jupyter
jupyter: ## Start Jupyter notebook
	$(PIP) install jupyter
	jupyter notebook

.PHONY: load-test
load-test: ## Run load tests with Locust
	locust -f tests/performance/locustfile.py --host=http://localhost:8080

##@ Git Operations

.PHONY: git-status
git-status: ## Show git status with ignored files
	git status --ignored

.PHONY: git-clean
git-clean: ## Remove untracked files (dry run first)
	git clean -xdn
	@echo "\nTo actually remove files, run: git clean -xdf"

##@ CI/CD

.PHONY: ci
ci: install-dev check security test-coverage ## Run full CI pipeline locally
	@echo "✓ CI pipeline complete"

.PHONY: validate
validate: lint test ## Quick validation before commit
	@echo "✓ Validation complete"

##@ Release

.PHONY: build
build: clean ## Build distribution packages
	$(PYTHON) -m build
	@echo "✓ Distribution packages built in dist/"

.PHONY: publish-test
publish-test: build ## Publish to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

.PHONY: publish
publish: build ## Publish to PyPI
	$(PYTHON) -m twine upload dist/*

##@ Information

.PHONY: info
info: ## Display project information
	@echo "AIXN Blockchain Project Information"
	@echo "===================================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "Project: $$(grep 'name = ' pyproject.toml | head -1 | cut -d '"' -f 2)"
	@echo "Version: $$(grep 'version = ' pyproject.toml | head -1 | cut -d '"' -f 2)"
	@echo "Source Dir: $(SRC_DIR)"
	@echo "Test Dir: $(TEST_DIR)"

.PHONY: list-scripts
list-scripts: ## List all Python scripts in the project
	@find scripts -name "*.py" -type f

# Default target
.DEFAULT_GOAL := help
