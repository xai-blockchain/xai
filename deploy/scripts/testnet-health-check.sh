#!/bin/bash
# ============================================================================
# Multi-Chain Testnet Health Check
# ============================================================================
# Checks all three testnets (AURA, PAW, XAI) across all four OVH servers
# including primary nodes, secondary nodes, and peer connectivity.
#
# Usage: ./testnet-health-check.sh [--json] [--quiet]
#
# Servers:
#   aura-testnet (158.69.119.76)     - AURA primary
#   paw-testnet (54.39.103.49)       - PAW primary
#   xai-testnet (54.39.129.11)       - XAI primary
#   services-testnet (139.99.149.160) - All secondaries
# ============================================================================

set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Options
JSON_OUTPUT=false
QUIET=false

for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --quiet|-q) QUIET=true ;;
    esac
done

# Results storage for JSON output
declare -A RESULTS

log() {
    if [ "$QUIET" = false ] && [ "$JSON_OUTPUT" = false ]; then
        echo -e "$@"
    fi
}

# ============================================================================
# AURA Chain Health Check (Cosmos SDK)
# ============================================================================
check_aura() {
    log "${CYAN}${BOLD}═══ AURA Network ═══${NC}"

    local primary_ok=false
    local secondary_ok=false
    local peered=false
    local primary_height=0
    local secondary_height=0
    local primary_peers=0
    local secondary_peers=0

    # Primary node (aura-testnet:10657)
    local primary_status=$(ssh -o ConnectTimeout=5 aura-testnet "curl -s http://127.0.0.1:10657/status" 2>/dev/null)
    if [ -n "$primary_status" ]; then
        primary_height=$(echo "$primary_status" | jq -r '.result.sync_info.latest_block_height // 0')
        local catching_up=$(echo "$primary_status" | jq -r 'if .result.sync_info.catching_up == false then "false" else "true" end')
        local moniker=$(echo "$primary_status" | jq -r '.result.node_info.moniker // "unknown"')

        local net_info=$(ssh -o ConnectTimeout=5 aura-testnet "curl -s http://127.0.0.1:10657/net_info" 2>/dev/null)
        primary_peers=$(echo "$net_info" | jq -r '.result.n_peers // 0')
        local peer_names=$(echo "$net_info" | jq -r '[.result.peers[]?.node_info.moniker] | join(", ") // ""')

        if [ "$catching_up" = "false" ]; then
            primary_ok=true
            log "${GREEN}✓${NC} aura-primary (${moniker}): height=${primary_height}, peers=${primary_peers} [${peer_names}]"
        else
            log "${YELLOW}⚠${NC} aura-primary: syncing at height ${primary_height}"
        fi
    else
        log "${RED}✗${NC} aura-primary: not responding"
    fi

    # Secondary node (services-testnet:26657)
    local secondary_status=$(ssh -o ConnectTimeout=5 services-testnet "curl -s http://127.0.0.1:26657/status" 2>/dev/null)
    if [ -n "$secondary_status" ]; then
        secondary_height=$(echo "$secondary_status" | jq -r '.result.sync_info.latest_block_height // 0')
        local catching_up=$(echo "$secondary_status" | jq -r 'if .result.sync_info.catching_up == false then "false" else "true" end')
        local moniker=$(echo "$secondary_status" | jq -r '.result.node_info.moniker // "unknown"')

        local net_info=$(ssh -o ConnectTimeout=5 services-testnet "curl -s http://127.0.0.1:26657/net_info" 2>/dev/null)
        secondary_peers=$(echo "$net_info" | jq -r '.result.n_peers // 0')
        local peer_names=$(echo "$net_info" | jq -r '[.result.peers[]?.node_info.moniker] | join(", ") // ""')

        if [ "$catching_up" = "false" ]; then
            secondary_ok=true
            log "${GREEN}✓${NC} aura-secondary (${moniker}): height=${secondary_height}, peers=${secondary_peers} [${peer_names}]"
        else
            log "${YELLOW}⚠${NC} aura-secondary: syncing at height ${secondary_height}"
        fi
    else
        log "${RED}✗${NC} aura-secondary: not responding"
    fi

    # Check peering
    if [ "$primary_peers" -ge 1 ] && [ "$secondary_peers" -ge 1 ]; then
        peered=true
        log "${GREEN}✓${NC} Peering: primary ↔ secondary connected"
    else
        log "${RED}✗${NC} Peering: nodes not connected (primary_peers=${primary_peers}, secondary_peers=${secondary_peers})"
    fi

    # Check height sync (allow 10 block difference)
    local height_diff=$((primary_height - secondary_height))
    if [ ${height_diff#-} -le 10 ]; then
        log "${GREEN}✓${NC} Sync: heights match (diff=${height_diff})"
    else
        log "${YELLOW}⚠${NC} Sync: height difference=${height_diff}"
    fi

    RESULTS[aura_primary_ok]=$primary_ok
    RESULTS[aura_secondary_ok]=$secondary_ok
    RESULTS[aura_peered]=$peered
    RESULTS[aura_primary_height]=$primary_height
    RESULTS[aura_secondary_height]=$secondary_height
    log ""
}

# ============================================================================
# PAW Chain Health Check (Cosmos SDK)
# ============================================================================
check_paw() {
    log "${CYAN}${BOLD}═══ PAW Network ═══${NC}"

    local primary_ok=false
    local secondary_ok=false
    local peered=false
    local primary_height=0
    local secondary_height=0
    local primary_peers=0
    local secondary_peers=0

    # Primary node (paw-testnet:26657)
    local primary_status=$(ssh -o ConnectTimeout=5 paw-testnet "curl -s http://127.0.0.1:26657/status" 2>/dev/null)
    if [ -n "$primary_status" ]; then
        primary_height=$(echo "$primary_status" | jq -r '.result.sync_info.latest_block_height // 0')
        local catching_up=$(echo "$primary_status" | jq -r 'if .result.sync_info.catching_up == false then "false" else "true" end')
        local moniker=$(echo "$primary_status" | jq -r '.result.node_info.moniker // "unknown"')

        local net_info=$(ssh -o ConnectTimeout=5 paw-testnet "curl -s http://127.0.0.1:26657/net_info" 2>/dev/null)
        primary_peers=$(echo "$net_info" | jq -r '.result.n_peers // 0')
        local peer_names=$(echo "$net_info" | jq -r '[.result.peers[]?.node_info.moniker] | join(", ") // ""')

        if [ "$catching_up" = "false" ]; then
            primary_ok=true
            log "${GREEN}✓${NC} paw-primary (${moniker}): height=${primary_height}, peers=${primary_peers} [${peer_names}]"
        else
            log "${YELLOW}⚠${NC} paw-primary: syncing at height ${primary_height}"
        fi
    else
        log "${RED}✗${NC} paw-primary: not responding"
    fi

    # Secondary node (services-testnet:27657)
    local secondary_status=$(ssh -o ConnectTimeout=5 services-testnet "curl -s http://127.0.0.1:27657/status" 2>/dev/null)
    if [ -n "$secondary_status" ]; then
        secondary_height=$(echo "$secondary_status" | jq -r '.result.sync_info.latest_block_height // 0')
        local catching_up=$(echo "$secondary_status" | jq -r 'if .result.sync_info.catching_up == false then "false" else "true" end')
        local moniker=$(echo "$secondary_status" | jq -r '.result.node_info.moniker // "unknown"')

        local net_info=$(ssh -o ConnectTimeout=5 services-testnet "curl -s http://127.0.0.1:27657/net_info" 2>/dev/null)
        secondary_peers=$(echo "$net_info" | jq -r '.result.n_peers // 0')
        local peer_names=$(echo "$net_info" | jq -r '[.result.peers[]?.node_info.moniker] | join(", ") // ""')

        if [ "$catching_up" = "false" ]; then
            secondary_ok=true
            log "${GREEN}✓${NC} paw-secondary (${moniker}): height=${secondary_height}, peers=${secondary_peers} [${peer_names}]"
        else
            log "${YELLOW}⚠${NC} paw-secondary: syncing at height ${secondary_height}"
        fi
    else
        log "${RED}✗${NC} paw-secondary: not responding"
    fi

    # Check peering
    if [ "$primary_peers" -ge 1 ] && [ "$secondary_peers" -ge 1 ]; then
        peered=true
        log "${GREEN}✓${NC} Peering: primary ↔ secondary connected"
    else
        log "${RED}✗${NC} Peering: nodes not connected"
    fi

    # Check height sync
    local height_diff=$((primary_height - secondary_height))
    if [ ${height_diff#-} -le 10 ]; then
        log "${GREEN}✓${NC} Sync: heights match (diff=${height_diff})"
    else
        log "${YELLOW}⚠${NC} Sync: height difference=${height_diff}"
    fi

    RESULTS[paw_primary_ok]=$primary_ok
    RESULTS[paw_secondary_ok]=$secondary_ok
    RESULTS[paw_peered]=$peered
    RESULTS[paw_primary_height]=$primary_height
    RESULTS[paw_secondary_height]=$secondary_height
    log ""
}

# ============================================================================
# XAI Chain Health Check (Python)
# ============================================================================
check_xai() {
    log "${CYAN}${BOLD}═══ XAI Network ═══${NC}"

    local primary_ok=false
    local secondary_ok=false
    local synced=false
    local primary_height=0
    local secondary_height=0
    local primary_mining=false
    local secondary_mining=false

    # Primary node (xai-testnet:8545)
    local primary_stats=$(ssh -o ConnectTimeout=5 xai-testnet "curl -s http://127.0.0.1:8545/stats" 2>/dev/null)
    if [ -n "$primary_stats" ]; then
        primary_height=$(echo "$primary_stats" | jq -r '.chain_height // 0')
        primary_mining=$(echo "$primary_stats" | jq -r '.is_mining // false')
        local uptime=$(echo "$primary_stats" | jq -r '.node_uptime // 0' | xargs printf "%.0f")
        local uptime_hrs=$((uptime / 3600))

        if [ "$primary_height" -gt 0 ]; then
            primary_ok=true
            local mining_status=""
            if [ "$primary_mining" = "true" ]; then
                mining_status="${GREEN}mining${NC}"
            else
                mining_status="${YELLOW}not mining${NC}"
            fi
            log "${GREEN}✓${NC} xai-primary: height=${primary_height}, ${mining_status}, uptime=${uptime_hrs}h"
        else
            log "${RED}✗${NC} xai-primary: height=0 (not synced)"
        fi
    else
        log "${RED}✗${NC} xai-primary: not responding"
    fi

    # Secondary node (services-testnet:8546)
    local secondary_stats=$(ssh -o ConnectTimeout=5 services-testnet "curl -s http://127.0.0.1:8546/stats" 2>/dev/null)
    if [ -n "$secondary_stats" ]; then
        secondary_height=$(echo "$secondary_stats" | jq -r '.chain_height // 0')
        secondary_mining=$(echo "$secondary_stats" | jq -r '.is_mining // false')
        local uptime=$(echo "$secondary_stats" | jq -r '.node_uptime // 0' | xargs printf "%.0f")
        local uptime_hrs=$((uptime / 3600))

        if [ "$secondary_height" -gt 0 ]; then
            secondary_ok=true
            local mining_status=""
            if [ "$secondary_mining" = "true" ]; then
                mining_status="${YELLOW}mining (should be off)${NC}"
            else
                mining_status="${GREEN}validator-only${NC}"
            fi
            log "${GREEN}✓${NC} xai-secondary: height=${secondary_height}, ${mining_status}, uptime=${uptime_hrs}h"
        else
            log "${RED}✗${NC} xai-secondary: height=0 (not synced)"
        fi
    else
        log "${RED}✗${NC} xai-secondary: not responding"
    fi

    # Check sync (XAI uses HTTP polling, allow 5 block difference)
    local height_diff=$((primary_height - secondary_height))
    if [ ${height_diff#-} -le 5 ]; then
        synced=true
        log "${GREEN}✓${NC} Sync: heights match (diff=${height_diff})"
    else
        log "${YELLOW}⚠${NC} Sync: height difference=${height_diff} (HTTP sync is 30s interval)"
    fi

    # Verify block hashes match at common height (optional deep check)
    if [ "$primary_ok" = true ] && [ "$secondary_ok" = true ]; then
        local min_height=$((secondary_height < primary_height ? secondary_height : primary_height))
        local primary_hash=$(ssh -o ConnectTimeout=5 xai-testnet "curl -s 'http://127.0.0.1:8545/blocks?limit=1&offset=$((primary_height - min_height))' | jq -r '.blocks[0].hash // \"\"'" 2>/dev/null)
        local secondary_hash=$(ssh -o ConnectTimeout=5 services-testnet "curl -s 'http://127.0.0.1:8546/blocks?limit=1&offset=$((secondary_height - min_height))' | jq -r '.blocks[0].hash // \"\"'" 2>/dev/null)

        if [ -n "$primary_hash" ] && [ "$primary_hash" = "$secondary_hash" ]; then
            log "${GREEN}✓${NC} Chain: block ${min_height} hash matches on both nodes"
        elif [ -n "$primary_hash" ] && [ -n "$secondary_hash" ]; then
            log "${RED}✗${NC} Chain: block hash mismatch at height ${min_height} (FORK!)"
        fi
    fi

    RESULTS[xai_primary_ok]=$primary_ok
    RESULTS[xai_secondary_ok]=$secondary_ok
    RESULTS[xai_synced]=$synced
    RESULTS[xai_primary_height]=$primary_height
    RESULTS[xai_secondary_height]=$secondary_height
    RESULTS[xai_primary_mining]=$primary_mining
    RESULTS[xai_secondary_mining]=$secondary_mining
    log ""
}

# ============================================================================
# Summary
# ============================================================================
print_summary() {
    log "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    log "${BOLD}                    TESTNET HEALTH SUMMARY${NC}"
    log "${BOLD}═══════════════════════════════════════════════════════════════${NC}"

    local all_ok=true

    # AURA
    if [ "${RESULTS[aura_primary_ok]}" = "true" ] && [ "${RESULTS[aura_secondary_ok]}" = "true" ] && [ "${RESULTS[aura_peered]}" = "true" ]; then
        log "${GREEN}AURA${NC}:  ✅ Healthy (${RESULTS[aura_primary_height]} blocks, 2 nodes peered)"
    else
        log "${RED}AURA${NC}:  ⚠️  Issues detected"
        all_ok=false
    fi

    # PAW
    if [ "${RESULTS[paw_primary_ok]}" = "true" ] && [ "${RESULTS[paw_secondary_ok]}" = "true" ] && [ "${RESULTS[paw_peered]}" = "true" ]; then
        log "${GREEN}PAW${NC}:   ✅ Healthy (${RESULTS[paw_primary_height]} blocks, 2 nodes peered)"
    else
        log "${RED}PAW${NC}:   ⚠️  Issues detected"
        all_ok=false
    fi

    # XAI
    if [ "${RESULTS[xai_primary_ok]}" = "true" ] && [ "${RESULTS[xai_secondary_ok]}" = "true" ] && [ "${RESULTS[xai_synced]}" = "true" ]; then
        local xai_mode=""
        if [ "${RESULTS[xai_secondary_mining]}" = "false" ]; then
            xai_mode="primary mining, secondary validator"
        else
            xai_mode="⚠️ both mining"
        fi
        log "${GREEN}XAI${NC}:   ✅ Healthy (${RESULTS[xai_primary_height]} blocks, ${xai_mode})"
    else
        log "${RED}XAI${NC}:   ⚠️  Issues detected"
        all_ok=false
    fi

    log "${BOLD}═══════════════════════════════════════════════════════════════${NC}"

    if [ "$all_ok" = true ]; then
        log "${GREEN}${BOLD}All testnets healthy!${NC}"
        return 0
    else
        log "${YELLOW}${BOLD}Some issues detected - review details above${NC}"
        return 1
    fi
}

# ============================================================================
# JSON Output
# ============================================================================
print_json() {
    cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "aura": {
    "primary": {"ok": ${RESULTS[aura_primary_ok]}, "height": ${RESULTS[aura_primary_height]}},
    "secondary": {"ok": ${RESULTS[aura_secondary_ok]}, "height": ${RESULTS[aura_secondary_height]}},
    "peered": ${RESULTS[aura_peered]}
  },
  "paw": {
    "primary": {"ok": ${RESULTS[paw_primary_ok]}, "height": ${RESULTS[paw_primary_height]}},
    "secondary": {"ok": ${RESULTS[paw_secondary_ok]}, "height": ${RESULTS[paw_secondary_height]}},
    "peered": ${RESULTS[paw_peered]}
  },
  "xai": {
    "primary": {"ok": ${RESULTS[xai_primary_ok]}, "height": ${RESULTS[xai_primary_height]}, "mining": ${RESULTS[xai_primary_mining]}},
    "secondary": {"ok": ${RESULTS[xai_secondary_ok]}, "height": ${RESULTS[xai_secondary_height]}, "mining": ${RESULTS[xai_secondary_mining]}},
    "synced": ${RESULTS[xai_synced]}
  }
}
EOF
}

# ============================================================================
# Main
# ============================================================================
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        log ""
        log "${BOLD}Testnet Health Check - $(date)${NC}"
        log ""
    fi

    check_aura
    check_paw
    check_xai

    if [ "$JSON_OUTPUT" = true ]; then
        print_json
    else
        print_summary
    fi
}

main
