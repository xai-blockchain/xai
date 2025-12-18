# XAI Developer Onboarding (Fast Path)

## Clone & Environment
- Repo: `~/blockchain-projects/xai`
- Source env: `cd ~/blockchain-projects/xai && source env.sh` (adds tools and ports)
- Python: use system python3, **no venv needed**; run `pip install -e .` only if deps change.

## Key Commands
- Run node: `python -m xai.core.node` (API on 12001, metrics 12070)
- Run testnet stack: `cd docker/testnet && docker compose up -d --build`
- Get testnet tokens: `python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS` (see [Faucet Guide](TESTNET_FAUCET.md))
- Tests: `pytest` (unit) or `pytest -m integration`
- Lint/format: `black . && isort .`; typecheck: `mypy`; security: `bandit -r src`
- CLI completion: `xai completion --shell bash|zsh > /etc/bash_completion.d/xai` (or source in your shell)

## Auth & RBAC
- API key header: `X-API-Key: <key>`; admin token: `X-Admin-Token: <token>`
- Emergency controls: see `docs/api/ADMIN_EMERGENCY_CURL.md`

## Monitoring
- Prometheus: http://localhost:12090 (testnet)
- Grafana: http://localhost:12091 (testnet) dashboards auto-provisioned

## Troubleshooting
- Logs: `logs/` (app), Docker: `docker compose logs -f`
- Metrics endpoint: `curl http://localhost:12001/metrics`
- Health: `curl http://localhost:12001/health`
