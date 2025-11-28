#!/usr/bin/env bash

# Validate P2P hardening configuration before deployment/merge.
# Fails fast if required env keys are missing or placeholder trust stores remain.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIGMAP="$ROOT_DIR/k8s/configmap.yaml"
STATEFULSET="$ROOT_DIR/k8s/statefulset.yaml"
MKDOCS="$ROOT_DIR/mkdocs.yml"
ALERTS="$ROOT_DIR/monitoring/prometheus_alerts.yml"

error() {
    echo "[ERROR] $*" >&2
}

warn() {
    echo "[WARN]  $*" >&2
}

info() {
    echo "[INFO]  $*"
}

require_file() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        error "Missing required file: $path"
        exit 1
    fi
}

require_file "$CONFIGMAP"
require_file "$STATEFULSET"
require_file "$MKDOCS"
require_file "$ALERTS"

required_envs=(
    XAI_PEER_REQUIRE_CLIENT_CERT
    XAI_PEER_NONCE_TTL_SECONDS
    XAI_P2P_MAX_MESSAGE_RATE
    XAI_P2P_MAX_BANDWIDTH_IN
    XAI_P2P_MAX_BANDWIDTH_OUT
    XAI_TRUSTED_PEER_PUBKEYS_FILE
    XAI_TRUSTED_PEER_CERT_FPS_FILE
)

info "Checking ConfigMap for required P2P hardening keys..."
for key in "${required_envs[@]}"; do
    if ! grep -q "$key" "$CONFIGMAP"; then
        error "configmap.yaml missing key: $key"
        exit 1
    fi
done

info "Checking StatefulSet env propagation..."
for key in "${required_envs[@]}"; do
    if ! grep -q "$key" "$STATEFULSET"; then
        error "statefulset.yaml missing env wiring for: $key"
        exit 1
    fi
done

info "Checking trust-store ConfigMap definition..."
if ! grep -q "name: xai-blockchain-trust" "$CONFIGMAP"; then
    error "trust-store ConfigMap (xai-blockchain-trust) missing in configmap.yaml"
    exit 1
fi
if ! grep -q "trust-store" "$STATEFULSET"; then
    error "trust-store volume/mount not present in statefulset.yaml"
    exit 1
fi

info "Checking for placeholder trust store values..."
pub_placeholder="02abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
cert_placeholder="a1b2c3d4e5f60718293a4b5c6d7e8f90112233445566778899aabbccddeeff00"
if grep -q "$pub_placeholder" "$CONFIGMAP"; then
    error "Placeholder peer pubkey remains in configmap.yaml (set ALLOW_PLACEHOLDER_TRUST_STORES=1 to override)."
    [[ "${ALLOW_PLACEHOLDER_TRUST_STORES:-0}" == "1" ]] || exit 1
    warn "Override enabled: placeholder pubkey present."
fi
if grep -q "$cert_placeholder" "$CONFIGMAP"; then
    error "Placeholder peer certificate fingerprint remains in configmap.yaml (set ALLOW_PLACEHOLDER_TRUST_STORES=1 to override)."
    [[ "${ALLOW_PLACEHOLDER_TRUST_STORES:-0}" == "1" ]] || exit 1
    warn "Override enabled: placeholder cert fingerprint present."
fi

info "Validating runbooks are wired into docs navigation..."
for runbook in runbooks/p2p-replay.md runbooks/p2p-rate-limit.md runbooks/p2p-auth.md; do
    if ! grep -q "$runbook" "$MKDOCS"; then
        error "mkdocs.yml missing navigation entry for $runbook"
        exit 1
    fi
done

info "Validating alert runbook links reference docs site..."
if ! grep -q "runbooks/p2p-replay" "$ALERTS"; then
    error "Alert runbook link missing for p2p-replay in prometheus_alerts.yml"
    exit 1
fi
if ! grep -q "runbooks/p2p-rate-limit" "$ALERTS"; then
    error "Alert runbook link missing for p2p-rate-limit in prometheus_alerts.yml"
    exit 1
fi
if ! grep -q "runbooks/p2p-auth" "$ALERTS"; then
    error "Alert runbook link missing for p2p-auth in prometheus_alerts.yml"
    exit 1
fi

info "P2P hardening checks passed."
