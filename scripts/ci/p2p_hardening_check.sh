#!/usr/bin/env bash

# Validate P2P hardening configuration before deployment/merge.
# Fails fast if required env keys are missing or placeholder trust stores remain.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIGMAP="$ROOT_DIR/k8s/configmap.yaml"
STATEFULSET="$ROOT_DIR/k8s/statefulset.yaml"
MKDOCS="$ROOT_DIR/mkdocs.yml"
ALERTS="$ROOT_DIR/monitoring/prometheus_alerts.yml"
P2P_VERSIONS="$ROOT_DIR/config/p2p_versions.yaml"

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
require_file "$P2P_VERSIONS"

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
for runbook in runbooks/p2p-replay.md runbooks/p2p-rate-limit.md runbooks/p2p-auth.md runbooks/p2p-quic.md; do
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
if ! grep -q "runbooks/p2p-quic" "$ALERTS"; then
    error "Alert runbook link missing for p2p-quic in prometheus_alerts.yml"
    exit 1
fi

info "Validating P2P version manifest matches code constants..."
python - <<'PY'
import importlib.util
import pathlib
import sys
import yaml

root = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("p2p_security", root / "src/xai/core/p2p_security.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore

manifest_path = root / "config/p2p_versions.yaml"
data = yaml.safe_load(manifest_path.read_text())
current = str(data.get("current", "")).strip()
releases = data.get("releases") or []

protocol_version = str(getattr(mod.P2PSecurityConfig, "PROTOCOL_VERSION", "")).strip()
supported_versions = {str(v).strip() for v in getattr(mod.P2PSecurityConfig, "SUPPORTED_VERSIONS", set())}

if not current:
    sys.exit("current version missing in manifest")
if protocol_version != current:
    sys.exit(f"protocol version mismatch: P2PSecurityConfig={protocol_version} vs manifest current={current}")
if protocol_version not in supported_versions:
    sys.exit("PROTOCOL_VERSION not present in SUPPORTED_VERSIONS")
matches = [row for row in releases if str(row.get("protocol_version")) == protocol_version]
if not matches:
    sys.exit("current protocol version not documented in releases list")

print(f"[INFO] P2P protocol version manifest aligned (version {protocol_version}).")
PY

info "P2P hardening checks passed."
