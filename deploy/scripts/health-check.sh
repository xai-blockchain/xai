#!/usr/bin/env bash
# ==========================================================================
# XAI Testnet Host Health Check (Local)
# ==========================================================================
# Run on xai-testnet or services-testnet to validate local node(s) and
# host-level resources.
# ==========================================================================

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

JSON_OUTPUT=false
QUIET=false
SKIP_SERVICES=false
SKIP_FINALITY=false

for arg in "$@"; do
  case "$arg" in
    --json) JSON_OUTPUT=true ;;
    --quiet|-q) QUIET=true ;;
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

# Thresholds
MIN_DISK_GB=${MIN_DISK_GB:-10}
MIN_MEM_MB=${MIN_MEM_MB:-1024}
MAX_LOAD_RATIO=${MAX_LOAD_RATIO:-0.9}
MIN_PEERS=${MIN_PEERS:-3}
MAX_HEIGHT_DRIFT=${MAX_HEIGHT_DRIFT:-3}
MAX_FINALITY_LAG=${MAX_FINALITY_LAG:-5}
EXPECTED_VALIDATORS=${EXPECTED_VALIDATORS:-4}
FINALITY_MIN_SIGNATURES=${FINALITY_MIN_SIGNATURES:-3}

FAILURES=0
WARNINGS=0

HOST_SHORT=$(hostname -s 2>/dev/null || hostname)

NODES=()
SERVICES=()

if [ -n "${NODE_DEFS:-}" ]; then
  IFS=',' read -r -a defs <<< "$NODE_DEFS"
  for def in "${defs[@]}"; do
    # name:port:role:p2p:ws:metrics
    NODES+=("$def")
  done
elif [ "$HOST_SHORT" = "xai-testnet" ]; then
  NODES+=("node1:12545:mining:12333:12765:12000")
  NODES+=("node2:12555:mining:12334:12766:12001")
  SERVICES+=("Explorer:12080:/health:http")
  SERVICES+=("Faucet:12081:/health:http")
  SERVICES+=("Indexer:12084:/health:http")
  SERVICES+=("WS Proxy:12082::tcp")
  SERVICES+=("GraphQL:12400:/graphql:graphql")
elif [ "$HOST_SHORT" = "services-testnet" ]; then
  NODES+=("node3:12546:validator:12335:12767:12002")
  NODES+=("node4:12556:validator:12336:12768:12003")
  SERVICES+=("Indexer Backup:12103:/health:http")
  SERVICES+=("WS Proxy Backup:12203::tcp")
fi

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

port_open() {
  local port="$1"
  if [ "$HAS_NC" = false ]; then
    echo "skip"
    return 0
  fi
  if nc -z -w2 127.0.0.1 "$port" >/dev/null 2>&1; then
    echo "open"
  else
    echo "closed"
  fi
}

check_system() {
  log "${CYAN}${BOLD}═══ System ═══${NC}"

  local avail_kb
  avail_kb=$(df -k / | awk 'NR==2 {print $4}')
  local avail_gb=$((avail_kb / 1024 / 1024))
  if [ "$avail_gb" -lt "$MIN_DISK_GB" ]; then
    warn "Low disk space: ${avail_gb}GB available"
  else
    ok "Disk space: ${avail_gb}GB available"
  fi

  local avail_mem
  avail_mem=$(free -m | awk 'NR==2 {print $7}')
  if [ "$avail_mem" -lt "$MIN_MEM_MB" ]; then
    warn "Low memory: ${avail_mem}MB available"
  else
    ok "Memory: ${avail_mem}MB available"
  fi

  local load
  load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
  local cores
  cores=$(nproc)
  local threshold
  threshold=$(awk -v c="$cores" -v r="$MAX_LOAD_RATIO" 'BEGIN {printf "%.2f", c*r}')
  if awk -v l="$load" -v t="$threshold" 'BEGIN {exit !(l>t)}'; then
    warn "High CPU load: ${load} (cores=${cores})"
  else
    ok "CPU load: ${load} (cores=${cores})"
  fi
}

declare -A NODE_OK NODE_HEIGHT NODE_PEERS NODE_MINING NODE_STATUS NODE_HASH NODE_ROLE NODE_ERRORS

check_node() {
  local name="$1"
  local rpc="$2"
  local role="$3"
  local p2p="$4"
  local ws="$5"
  local metrics="$6"

  local base_url="http://127.0.0.1:${rpc}"
  local node_ok=true
  local errors=()

  local health stats peers latest
  health=$(curl -s --max-time 5 "${base_url}/health")
  stats=$(curl -s --max-time 5 "${base_url}/stats")
  peers=$(curl -s --max-time 5 "${base_url}/peers?verbose=true")
  latest=$(curl -s --max-time 5 "${base_url}/block/latest?summary=1")

  if [ -z "$health" ]; then
    node_ok=false
    errors+=("health")
  fi
  if [ -z "$stats" ]; then
    node_ok=false
    errors+=("stats")
  fi
  if [ -z "$peers" ]; then
    node_ok=false
    errors+=("peers")
  fi
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

  local latest_hash
  latest_hash=$(json_get "$latest" '.hash // .summary.hash // ""')

  local p2p_state ws_state metrics_code
  p2p_state="skip"
  ws_state="skip"
  metrics_code="skip"
  if [ -n "$p2p" ]; then
    p2p_state=$(port_open "$p2p")
  fi
  if [ -n "$ws" ]; then
    ws_state=$(port_open "$ws")
  fi
  if [ -n "$metrics" ]; then
    metrics_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${metrics}/metrics")
  fi

  if [ "$p2p_state" = "closed" ]; then
    warn "$name P2P port $p2p unreachable"
  fi
  if [ "$ws_state" = "closed" ]; then
    warn "$name WS port $ws unreachable"
  fi
  if [ "$metrics_code" != "skip" ] && [ "$metrics_code" != "200" ]; then
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
    ok "$name (port ${rpc}) healthy | height=${height} peers=${peer_count} mining=${is_mining}"
  else
    fail "$name (port ${rpc}) issues: ${NODE_ERRORS[$name]}"
  fi
}

check_consensus() {
  local min_height=0
  local max_height=0
  local first=true

  for def in "${NODES[@]}"; do
    IFS=':' read -r name _rpc _role _p2p _ws _metrics <<< "$def"
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
    IFS=':' read -r name rpc _role _p2p _ws _metrics <<< "$def"
    local block_json
    block_json=$(curl -s --max-time 5 "http://127.0.0.1:${rpc}/blocks/${min_height}")
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
  local rpc=""
  for def in "${NODES[@]}"; do
    IFS=':' read -r name node_rpc role _p2p _ws _metrics <<< "$def"
    if [ "$role" = "mining" ]; then
      rpc="$node_rpc"
      break
    fi
  done
  if [ -z "$rpc" ]; then
    warn "Finality: no mining node available to query"
    FINALITY_OK=false
    return
  fi

  local status_json
  status_json=$(curl -s --max-time 5 "http://127.0.0.1:${rpc}/finality/status")
  if [ -z "$status_json" ]; then
    fail "Finality: unable to reach local finality status"
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
  cert_json=$(curl -s --max-time 5 "http://127.0.0.1:${rpc}/finality/certificates?limit=1")
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
}

check_services() {
  log "${CYAN}${BOLD}═══ Services ═══${NC}"

  for svc in "${SERVICES[@]}"; do
    IFS=':' read -r name port path kind <<< "$svc"
    if [ -z "$port" ]; then
      continue
    fi
    if [ "$kind" = "tcp" ]; then
      local state
      state=$(port_open "$port")
      if [ "$state" = "open" ]; then
        ok "${name} port ${port}"
      else
        warn "${name} port ${port} unreachable"
      fi
      continue
    fi

    if [ "$kind" = "graphql" ]; then
      local response gql_type
      response=$(curl -s --max-time 5 -H 'Content-Type: application/json' \
        -d '{"query":"{ __typename }"}' "http://127.0.0.1:${port}${path}")
      gql_type=$(json_get "$response" '.data.__typename // empty')
      if [ -n "$gql_type" ]; then
        ok "${name} responded (${gql_type})"
      else
        warn "${name} health check failed"
      fi
      continue
    fi

    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${port}${path}")
    if [ "$code" = "200" ]; then
      ok "${name} health"
    else
      warn "${name} health check returned ${code}"
    fi
  done
}

render_json() {
  local nodes_json='[]'
  for def in "${NODES[@]}"; do
    IFS=':' read -r name rpc role _p2p _ws _metrics <<< "$def"
    local node_json
    node_json=$(jq -n \
      --arg name "$name" \
      --arg role "$role" \
      --arg status "${NODE_STATUS[$name]}" \
      --arg hash "${NODE_HASH[$name]}" \
      --arg errors "${NODE_ERRORS[$name]}" \
      --argjson ok "${NODE_OK[$name]:-false}" \
      --argjson height "${NODE_HEIGHT[$name]:-0}" \
      --argjson peers "${NODE_PEERS[$name]:-0}" \
      --argjson mining "${NODE_MINING[$name]:-false}" \
      '{name:$name, role:$role, ok:$ok, status:$status, height:$height, peers:$peers, mining:$mining, latest_hash:$hash, errors:$errors}')
    nodes_json=$(jq -n --argjson arr "$nodes_json" --argjson node "$node_json" '$arr + [$node]')
  done

  jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg host "$HOST_SHORT" \
    --argjson failures "$FAILURES" \
    --argjson warnings "$WARNINGS" \
    --argjson consensus_ok "${CONSENSUS_OK:-false}" \
    --argjson finality_ok "${FINALITY_OK:-false}" \
    --argjson nodes "$nodes_json" \
    '{timestamp:$timestamp, host:$host, failures:$failures, warnings:$warnings, consensus_ok:$consensus_ok, finality_ok:$finality_ok, nodes:$nodes}'
}

main() {
  if [ "$JSON_OUTPUT" = false ]; then
    log "${BOLD}XAI Host Health Check - $(date)${NC}"
    log "${BLUE}Host:${NC} ${HOST_SHORT}"
    log ""
  fi

  CONSENSUS_OK=true
  FINALITY_OK=true

  check_system

  if [ "${#NODES[@]}" -eq 0 ]; then
    warn "No node definitions found for host ${HOST_SHORT} (set NODE_DEFS to override)"
  else
    log ""
    log "${CYAN}${BOLD}═══ Nodes ═══${NC}"
    for def in "${NODES[@]}"; do
      IFS=':' read -r name rpc role p2p ws metrics <<< "$def"
      check_node "$name" "$rpc" "$role" "$p2p" "$ws" "$metrics"
    done

    log ""
    log "${CYAN}${BOLD}═══ Consensus ═══${NC}"
    check_consensus

    if [ "$SKIP_FINALITY" = false ]; then
      log ""
      log "${CYAN}${BOLD}═══ Finality ═══${NC}"
      check_finality
    fi
  fi

  if [ "$SKIP_SERVICES" = false ] && [ "${#SERVICES[@]}" -gt 0 ]; then
    log ""
    check_services
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
