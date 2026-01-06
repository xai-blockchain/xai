#!/usr/bin/env bash
# ==========================================================================
# XAI Testnet (4-Validator) Health Check
# ==========================================================================
# Validates the current four-validator testnet across xai-testnet and
# services-testnet, including:
#   - Node API health (/health, /stats, /peers, /block/latest)
#   - Mining role correctness (2 miners + 2 validators)
#   - Peer counts + P2P/WS port reachability
#   - Consensus height + block hash agreement
#   - Finality status + certificate quorum
#   - Supporting services (explorer, faucet, indexer, GraphQL, WS proxy)
#   - Public endpoints (Cloudflare front doors)
#
# Usage: ./testnet-health-check.sh [--json] [--quiet] [--public-only]
#                                   [--internal-only] [--skip-services]
#                                   [--skip-finality]
#
# Defaults target the current testnet layout documented in xai-testnets.
# ==========================================================================

set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

JSON_OUTPUT=false
QUIET=false
SKIP_PUBLIC=false
SKIP_INTERNAL=false
SKIP_SERVICES=false
SKIP_FINALITY=false

for arg in "$@"; do
  case "$arg" in
    --json) JSON_OUTPUT=true ;;
    --quiet|-q) QUIET=true ;;
    --public-only) SKIP_INTERNAL=true ;;
    --internal-only) SKIP_PUBLIC=true ;;
    --skip-services) SKIP_SERVICES=true ;;
    --skip-finality) SKIP_FINALITY=true ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd jq
need_cmd ssh

HAS_NC=true
if ! command -v nc >/dev/null 2>&1; then
  HAS_NC=false
fi

log() {
  if [ "$QUIET" = false ] && [ "$JSON_OUTPUT" = false ]; then
    echo -e "$@"
  fi
}

ok() {
  log "${GREEN}✓${NC} $*"
}

warn() {
  log "${YELLOW}⚠${NC} $*"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  log "${RED}✗${NC} $*"
  FAILURES=$((FAILURES + 1))
}

# Core configuration
PRIMARY_HOST=${XAI_PRIMARY_HOST:-xai-testnet}
SERVICES_HOST=${XAI_SERVICES_HOST:-services-testnet}
SSH_OPTS=${SSH_OPTS:-"-o BatchMode=yes -o ConnectTimeout=5"}
CURL_TIMEOUT=${CURL_TIMEOUT:-5}
MIN_PEERS=${MIN_PEERS:-3}
MAX_HEIGHT_DRIFT=${MAX_HEIGHT_DRIFT:-3}
MAX_FINALITY_LAG=${MAX_FINALITY_LAG:-5}
EXPECTED_VALIDATORS=${EXPECTED_VALIDATORS:-4}
FINALITY_MIN_SIGNATURES=${FINALITY_MIN_SIGNATURES:-3}
REQUIRE_SERVICES=${REQUIRE_SERVICES:-true}
VALIDATORS_JSON=${VALIDATORS_JSON:-/home/hudson/blockchain-projects/xai-testnets/xai-testnet-1/validators.json}

# Public endpoints (Cloudflare)
PUBLIC_RPC=${PUBLIC_RPC:-https://testnet-rpc.xaiblockchain.com}
PUBLIC_API=${PUBLIC_API:-https://testnet-api.xaiblockchain.com}
PUBLIC_WS=${PUBLIC_WS:-https://testnet-ws.xaiblockchain.com}
PUBLIC_EXPLORER=${PUBLIC_EXPLORER:-https://testnet-explorer.xaiblockchain.com}
PUBLIC_FAUCET=${PUBLIC_FAUCET:-https://testnet-faucet.xaiblockchain.com}
PUBLIC_GRAPHQL=${PUBLIC_GRAPHQL:-https://testnet-graphql.xaiblockchain.com/graphql}

# Node layout: name|host|rpc|p2p|ws|metrics|role
NODES=(
  "node1|${PRIMARY_HOST}|12545|12333|12765|12000|mining"
  "node2|${PRIMARY_HOST}|12555|12334|12766|12001|mining"
  "node3|${SERVICES_HOST}|12546|12335|12767|12002|validator"
  "node4|${SERVICES_HOST}|12556|12336|12768|12003|validator"
)

# Tracking
FAILURES=0
WARNINGS=0

declare -A NODE_OK NODE_HEIGHT NODE_PEERS NODE_MINING NODE_STATUS NODE_HASH NODE_ROLE NODE_ERRORS

remote_curl() {
  local host="$1"
  local url="$2"
  ssh $SSH_OPTS "$host" "curl -s --max-time $CURL_TIMEOUT '$url'" 2>/dev/null
}

remote_http_code() {
  local host="$1"
  local url="$2"
  ssh $SSH_OPTS "$host" "curl -s -o /dev/null -w '%{http_code}' --max-time $CURL_TIMEOUT '$url'" 2>/dev/null
}

remote_port_open() {
  local host="$1"
  local port="$2"
  if [ "$HAS_NC" = false ]; then
    echo "skip"
    return 0
  fi
  if ssh $SSH_OPTS "$host" "nc -z -w2 127.0.0.1 $port" >/dev/null 2>&1; then
    echo "open"
  else
    echo "closed"
  fi
}

json_get() {
  echo "$1" | jq -r "$2" 2>/dev/null
}

numeric_or_zero() {
  local value="$1"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    echo "$value"
  else
    echo 0
  fi
}

check_node() {
  local name="$1"
  local host="$2"
  local rpc="$3"
  local p2p="$4"
  local ws="$5"
  local metrics="$6"
  local role="$7"

  local base_url="http://127.0.0.1:${rpc}"
  local node_ok=true
  local errors=()

  local health stats peers latest

  health=$(remote_curl "$host" "${base_url}/health")
  if [ -z "$health" ]; then
    node_ok=false
    errors+=("health")
  fi

  stats=$(remote_curl "$host" "${base_url}/stats")
  if [ -z "$stats" ]; then
    node_ok=false
    errors+=("stats")
  fi

  peers=$(remote_curl "$host" "${base_url}/peers?verbose=true")
  if [ -z "$peers" ]; then
    node_ok=false
    errors+=("peers")
  fi

  latest=$(remote_curl "$host" "${base_url}/block/latest?summary=1")
  if [ -z "$latest" ]; then
    node_ok=false
    errors+=("latest_block")
  fi

  local status
  status=$(json_get "$health" '.status // "unknown"')
  if [ -z "$status" ]; then
    status="unknown"
  fi
  if [ "$status" != "healthy" ]; then
    node_ok=false
    errors+=("health_status=${status}")
  fi

  local height
  height=$(json_get "$stats" '.chain_height // .height // "0"')
  height=$(numeric_or_zero "$height")
  if [ "$height" -le 0 ]; then
    node_ok=false
    errors+=("height")
  fi

  local peer_count
  peer_count=$(json_get "$stats" '.peers // .peer_count // empty')
  peer_count=$(numeric_or_zero "$peer_count")
  if [ "$peer_count" -eq 0 ]; then
    peer_count=$(json_get "$peers" '.connected_total // .count // .network.peers // "0"')
    peer_count=$(numeric_or_zero "$peer_count")
  fi
  if [ "$peer_count" -lt "$MIN_PEERS" ]; then
    node_ok=false
    errors+=("peers=${peer_count}")
  fi

  local is_mining
  is_mining=$(json_get "$stats" '.is_mining // false')
  if [ "$is_mining" != "true" ] && [ "$is_mining" != "false" ]; then
    is_mining=false
  fi
  if [ "$role" = "mining" ] && [ "$is_mining" != "true" ]; then
    node_ok=false
    errors+=("mining_expected")
  fi
  if [ "$role" = "validator" ] && [ "$is_mining" = "true" ]; then
    node_ok=false
    errors+=("mining_disabled_expected")
  fi

  local latest_height latest_hash
  latest_height=$(json_get "$latest" '.block_number // .summary.height // .height // empty')
  latest_height=$(numeric_or_zero "$latest_height")
  latest_hash=$(json_get "$latest" '.hash // .summary.hash // ""')

  local p2p_state ws_state metrics_code
  p2p_state=$(remote_port_open "$host" "$p2p")
  ws_state=$(remote_port_open "$host" "$ws")
  metrics_code=$(remote_http_code "$host" "http://127.0.0.1:${metrics}/metrics")

  if [ "$p2p_state" = "closed" ]; then
    warn "$name P2P port $p2p unreachable"
  fi
  if [ "$ws_state" = "closed" ]; then
    warn "$name WS port $ws unreachable"
  fi
  if [ "$metrics_code" != "200" ]; then
    warn "$name metrics port $metrics returned ${metrics_code:-000}"
  fi

  NODE_OK["$name"]=$node_ok
  NODE_HEIGHT["$name"]=$height
  NODE_PEERS["$name"]=$peer_count
  NODE_MINING["$name"]=$is_mining
  NODE_STATUS["$name"]=$status
  NODE_HASH["$name"]=$latest_hash
  NODE_ROLE["$name"]=$role
  NODE_ERRORS["$name"]=$(IFS=,; echo "${errors[*]}")

  if [ "$node_ok" = true ]; then
    ok "$name (${host}:${rpc}) healthy | height=${height} peers=${peer_count} mining=${is_mining}"
  else
    fail "$name (${host}:${rpc}) issues: ${NODE_ERRORS[$name]}"
  fi
}

check_consensus() {
  local min_height=0
  local max_height=0
  local first=true

  for def in "${NODES[@]}"; do
    IFS='|' read -r name _host _rpc _p2p _ws _metrics _role <<< "$def"
    local height="${NODE_HEIGHT[$name]:-0}"
    if [ "$height" -le 0 ]; then
      fail "Consensus check: missing height for $name"
      CONSENSUS_OK=false
      return
    fi
    if [ "$first" = true ]; then
      min_height=$height
      max_height=$height
      first=false
    else
      if [ "$height" -lt "$min_height" ]; then
        min_height=$height
      fi
      if [ "$height" -gt "$max_height" ]; then
        max_height=$height
      fi
    fi
  done

  local drift=$((max_height - min_height))
  if [ "$drift" -gt "$MAX_HEIGHT_DRIFT" ]; then
    fail "Consensus check: height drift ${drift} (min=${min_height}, max=${max_height})"
    CONSENSUS_OK=false
  else
    ok "Consensus heights within drift (${min_height}-${max_height})"
  fi

  local ref_hash=""
  for def in "${NODES[@]}"; do
    IFS='|' read -r name host rpc _p2p _ws _metrics _role <<< "$def"
    local block_json
    block_json=$(remote_curl "$host" "http://127.0.0.1:${rpc}/blocks/${min_height}")
    if [ -z "$block_json" ]; then
      fail "Consensus check: unable to fetch block ${min_height} from ${name}"
      CONSENSUS_OK=false
      return
    fi
    local block_hash
    block_hash=$(json_get "$block_json" '.hash // .block_hash // .block.hash // .header.hash // ""')
    if [ -z "$block_hash" ]; then
      fail "Consensus check: missing block hash at height ${min_height} for ${name}"
      CONSENSUS_OK=false
      return
    fi
    if [ -z "$ref_hash" ]; then
      ref_hash="$block_hash"
    elif [ "$block_hash" != "$ref_hash" ]; then
      fail "Consensus check: block hash mismatch at ${min_height} (${name})"
      CONSENSUS_OK=false
      return
    fi
  done

  ok "Consensus hash match at height ${min_height} (${ref_hash:0:12})"
}

check_finality() {
  local host="$PRIMARY_HOST"
  local rpc=12545
  local base_url="http://127.0.0.1:${rpc}"
  local status_json
  status_json=$(remote_curl "$host" "${base_url}/finality/status")
  if [ -z "$status_json" ]; then
    fail "Finality: unable to reach ${host}:${rpc}"
    FINALITY_OK=false
    return
  fi

  local enabled total_validators finalized_height quorum_threshold
  enabled=$(json_get "$status_json" '.finality_enabled // false')
  total_validators=$(json_get "$status_json" '.total_validators // 0')
  total_validators=$(numeric_or_zero "$total_validators")
  finalized_height=$(json_get "$status_json" '.highest_finalized_height // "0"')
  finalized_height=$(numeric_or_zero "$finalized_height")
  quorum_threshold=$(json_get "$status_json" '.quorum_threshold // ""')

  if [ "$enabled" != "true" ]; then
    fail "Finality: disabled (${enabled})"
    FINALITY_OK=false
    return
  fi
  if [ "$total_validators" -ne "$EXPECTED_VALIDATORS" ]; then
    fail "Finality: expected ${EXPECTED_VALIDATORS} validators, got ${total_validators}"
    FINALITY_OK=false
  else
    ok "Finality validators: ${total_validators} (quorum ${quorum_threshold})"
  fi

  local head_height=${NODE_HEIGHT[node1]:-0}
  if [ "$head_height" -le 0 ]; then
    head_height=$finalized_height
  fi
  local lag=$((head_height - finalized_height))
  if [ "$finalized_height" -le 0 ] || [ "$lag" -gt "$MAX_FINALITY_LAG" ]; then
    fail "Finality lag too high (finalized=${finalized_height}, head=${head_height}, lag=${lag})"
    FINALITY_OK=false
  else
    ok "Finality height ${finalized_height} (lag ${lag})"
  fi

  local cert_json
  cert_json=$(remote_curl "$host" "${base_url}/finality/certificates?limit=1")
  if [ -z "$cert_json" ]; then
    fail "Finality: certificates endpoint unavailable"
    FINALITY_OK=false
    return
  fi
  local sig_count
  sig_count=$(json_get "$cert_json" '.certificates[0].signatures | length')
  sig_count=$(numeric_or_zero "$sig_count")
  if [ "$sig_count" -lt "$FINALITY_MIN_SIGNATURES" ]; then
    fail "Finality: insufficient signatures on latest certificate (${sig_count})"
    FINALITY_OK=false
  else
    ok "Finality signatures on latest cert: ${sig_count}"
  fi

  if [ -f "$VALIDATORS_JSON" ]; then
    local validator_json expected_set actual_set
    validator_json=$(remote_curl "$host" "${base_url}/finality/validators")
    if [ -n "$validator_json" ]; then
      expected_set=$(jq -r '.[].address' "$VALIDATORS_JSON" 2>/dev/null | sort | tr '\n' ' ' | sed 's/ $//')
      actual_set=$(echo "$validator_json" | jq -r '.validators[]?.address' 2>/dev/null | sort | tr '\n' ' ' | sed 's/ $//')
      if [ -z "$actual_set" ]; then
        fail "Finality: validator set response missing addresses"
        FINALITY_OK=false
      elif [ "$expected_set" != "$actual_set" ]; then
        fail "Finality: validator set mismatch (expected != actual)"
        FINALITY_OK=false
      else
        ok "Finality validator set matches validators.json"
      fi
    else
      warn "Finality: unable to query validator set"
    fi
  fi
}

check_services() {
  local host="$PRIMARY_HOST"

  local explorer_code faucet_code indexer_code ws_state gql_ok

  explorer_code=$(remote_http_code "$host" "http://127.0.0.1:12080/health")
  if [ "$explorer_code" = "200" ]; then
    ok "Explorer health (primary)"
  else
    handle_service_result "Explorer" "$explorer_code"
  fi

  faucet_code=$(remote_http_code "$host" "http://127.0.0.1:12081/health")
  if [ "$faucet_code" = "200" ]; then
    ok "Faucet health (primary)"
  else
    handle_service_result "Faucet" "$faucet_code"
  fi

  indexer_code=$(remote_http_code "$host" "http://127.0.0.1:12084/health")
  if [ "$indexer_code" = "200" ]; then
    ok "Indexer health (primary)"
  else
    handle_service_result "Indexer" "$indexer_code"
  fi

  ws_state=$(remote_port_open "$host" 12082)
  if [ "$ws_state" = "open" ]; then
    ok "WS proxy port 12082 (primary)"
  else
    handle_service_result "WS proxy" "$ws_state"
  fi

  gql_ok=false
  local gql_payload
  gql_payload=$(ssh $SSH_OPTS "$host" "curl -s -H 'Content-Type: application/json' -d '{\"query\":\"{ __typename }\"}' http://127.0.0.1:12400/graphql" 2>/dev/null)
  if [ -n "$gql_payload" ]; then
    local gql_type
    gql_type=$(json_get "$gql_payload" '.data.__typename // empty')
    if [ -n "$gql_type" ]; then
      gql_ok=true
      ok "GraphQL responded (${gql_type})"
    fi
  fi
  if [ "$gql_ok" = false ]; then
    handle_service_result "GraphQL" "unavailable"
  fi

  # Secondary services host
  local backup_indexer_code ws_backup_state
  backup_indexer_code=$(remote_http_code "$SERVICES_HOST" "http://127.0.0.1:12103/health")
  if [ "$backup_indexer_code" = "200" ]; then
    ok "Indexer health (backup)"
  else
    warn "Backup indexer health check returned ${backup_indexer_code:-000}"
  fi

  ws_backup_state=$(remote_port_open "$SERVICES_HOST" 12203)
  if [ "$ws_backup_state" = "open" ]; then
    ok "WS proxy port 12203 (backup)"
  else
    warn "Backup WS proxy port 12203 not reachable"
  fi
}

handle_service_result() {
  local service="$1"
  local result="$2"
  if [ "$REQUIRE_SERVICES" = true ]; then
    fail "${service} health check failed (${result})"
  else
    warn "${service} health check failed (${result})"
  fi
}

check_public() {
  local code

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_RPC/health")
  if [ "$code" = "200" ]; then
    ok "Public RPC /health"
  else
    fail "Public RPC /health returned ${code}"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_RPC/stats")
  if [ "$code" = "200" ]; then
    ok "Public RPC /stats"
  else
    fail "Public RPC /stats returned ${code}"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_API/health")
  if [ "$code" = "200" ]; then
    ok "Public API /health"
  else
    fail "Public API /health returned ${code}"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_EXPLORER/health")
  if [ "$code" = "200" ]; then
    ok "Public Explorer /health"
  else
    fail "Public Explorer /health returned ${code}"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_FAUCET/health")
  if [ "$code" = "200" ]; then
    ok "Public Faucet /health"
  else
    fail "Public Faucet /health returned ${code}"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_GRAPHQL")
  if [ "$code" != "000" ]; then
    ok "Public GraphQL reachable (HTTP ${code})"
  else
    fail "Public GraphQL unreachable"
  fi

  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$CURL_TIMEOUT" "$PUBLIC_WS")
  if [ "$code" != "000" ]; then
    ok "Public WS reachable (HTTP ${code})"
  else
    fail "Public WS unreachable"
  fi
}

render_json() {
  local nodes_json='[]'
  for def in "${NODES[@]}"; do
    IFS='|' read -r name host rpc _p2p _ws _metrics role <<< "$def"
    local node_json
    node_json=$(jq -n \
      --arg name "$name" \
      --arg host "$host" \
      --arg role "$role" \
      --arg status "${NODE_STATUS[$name]}" \
      --arg hash "${NODE_HASH[$name]}" \
      --arg errors "${NODE_ERRORS[$name]}" \
      --argjson ok "${NODE_OK[$name]:-false}" \
      --argjson height "${NODE_HEIGHT[$name]:-0}" \
      --argjson peers "${NODE_PEERS[$name]:-0}" \
      --argjson mining "${NODE_MINING[$name]:-false}" \
      '{name:$name, host:$host, role:$role, ok:$ok, status:$status, height:$height, peers:$peers, mining:$mining, latest_hash:$hash, errors:$errors}')
    nodes_json=$(jq -n --argjson arr "$nodes_json" --argjson node "$node_json" '$arr + [$node]')
  done

  jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson failures "$FAILURES" \
    --argjson warnings "$WARNINGS" \
    --argjson consensus_ok "${CONSENSUS_OK:-false}" \
    --argjson finality_ok "${FINALITY_OK:-false}" \
    --argjson nodes "$nodes_json" \
    '{timestamp:$timestamp, failures:$failures, warnings:$warnings, consensus_ok:$consensus_ok, finality_ok:$finality_ok, nodes:$nodes}'
}

main() {
  if [ "$JSON_OUTPUT" = false ]; then
    log "${BOLD}XAI Testnet Health Check - $(date)${NC}"
    log "${BLUE}Primary host:${NC} ${PRIMARY_HOST} | ${BLUE}Services host:${NC} ${SERVICES_HOST}"
    log ""
  fi

  CONSENSUS_OK=true
  FINALITY_OK=true

  if [ "$SKIP_INTERNAL" = false ]; then
    log "${CYAN}${BOLD}═══ Validator Nodes ═══${NC}"
    for def in "${NODES[@]}"; do
      IFS='|' read -r name host rpc p2p ws metrics role <<< "$def"
      check_node "$name" "$host" "$rpc" "$p2p" "$ws" "$metrics" "$role"
    done

    log ""
    log "${CYAN}${BOLD}═══ Consensus ═══${NC}"
    check_consensus

    if [ "$SKIP_FINALITY" = false ]; then
      log ""
      log "${CYAN}${BOLD}═══ Finality ═══${NC}"
      check_finality
    fi

    if [ "$SKIP_SERVICES" = false ]; then
      log ""
      log "${CYAN}${BOLD}═══ Services ═══${NC}"
      check_services
    fi
  fi

  if [ "$SKIP_PUBLIC" = false ]; then
    log ""
    log "${CYAN}${BOLD}═══ Public Endpoints ═══${NC}"
    check_public
  fi

  if [ "$JSON_OUTPUT" = true ]; then
    render_json
  else
    log ""
    log "${BOLD}Summary${NC}"
    log "Failures: $FAILURES | Warnings: $WARNINGS"
  fi

  if [ "$FAILURES" -gt 0 ]; then
    exit 1
  fi
}

main
