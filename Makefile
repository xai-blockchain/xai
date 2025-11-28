.PHONY: test-p2p-security p2p-hardening-check ci-p2p

# Run P2P-focused tests
test-p2p-security:
	@if [ -z "$${VIRTUAL_ENV}" ]; then echo "No venv active; using system python."; fi
	@PYTEST_BIN=$${PYTEST_BIN:-pytest} $(PYTEST_BIN) tests/chaos/test_partition_reconnect_utxo_digest.py tests/xai_tests/unit/test_p2p_security_probes.py

# Run P2P hardening static checks
p2p-hardening-check:
	@scripts/ci/p2p_hardening_check.sh

# Convenience CI target: run hardening checks and P2P tests
ci-p2p: p2p-hardening-check test-p2p-security
