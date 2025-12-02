#!/bin/bash
#
# Clean Private Key Exposure from Shell History
#
# This script removes potentially exposed private keys from shell history files.
# Run this if you previously used insecure --private-key CLI arguments.
#
# Usage: ./clean_private_key_history.sh
#

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}XAI Wallet - Clean Shell History${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "This script will remove commands containing private keys from your shell history."
echo ""
echo -e "${RED}WARNING: This operation modifies your shell history files.${NC}"
echo -e "${RED}A backup will be created before modification.${NC}"
echo ""
read -p "Continue? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "Cancelled."
    exit 0
fi

# Patterns to search for (private key exposure)
patterns=(
    "--private-key"
    "--privkey"
    "private_key="
    "PRIVATE_KEY="
    "XAI_PRIVATE_KEY="
)

cleaned=0

# Clean bash history
if [[ -f "$HOME/.bash_history" ]]; then
    echo ""
    echo -e "${YELLOW}Checking bash history...${NC}"

    # Create backup
    cp "$HOME/.bash_history" "$HOME/.bash_history.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ Backup created: $HOME/.bash_history.backup.$(date +%Y%m%d_%H%M%S)"

    # Count matches
    matches=0
    for pattern in "${patterns[@]}"; do
        count=$(grep -c "$pattern" "$HOME/.bash_history" 2>/dev/null || true)
        matches=$((matches + count))
    done

    if [[ $matches -gt 0 ]]; then
        echo "  ⚠ Found $matches potentially insecure command(s)"

        # Remove lines containing patterns
        for pattern in "${patterns[@]}"; do
            sed -i "/$pattern/d" "$HOME/.bash_history"
        done

        echo "  ✓ Cleaned bash history"
        cleaned=$((cleaned + matches))
    else
        echo "  ✓ No issues found in bash history"
    fi
fi

# Clean zsh history
if [[ -f "$HOME/.zsh_history" ]]; then
    echo ""
    echo -e "${YELLOW}Checking zsh history...${NC}"

    # Create backup
    cp "$HOME/.zsh_history" "$HOME/.zsh_history.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ Backup created: $HOME/.zsh_history.backup.$(date +%Y%m%d_%H%M%S)"

    # Count matches
    matches=0
    for pattern in "${patterns[@]}"; do
        count=$(grep -c "$pattern" "$HOME/.zsh_history" 2>/dev/null || true)
        matches=$((matches + count))
    done

    if [[ $matches -gt 0 ]]; then
        echo "  ⚠ Found $matches potentially insecure command(s)"

        # Remove lines containing patterns
        for pattern in "${patterns[@]}"; do
            sed -i "/$pattern/d" "$HOME/.zsh_history"
        done

        echo "  ✓ Cleaned zsh history"
        cleaned=$((cleaned + matches))
    else
        echo "  ✓ No issues found in zsh history"
    fi
fi

# Clean fish history
if [[ -f "$HOME/.local/share/fish/fish_history" ]]; then
    echo ""
    echo -e "${YELLOW}Checking fish history...${NC}"

    # Create backup
    cp "$HOME/.local/share/fish/fish_history" "$HOME/.local/share/fish/fish_history.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ Backup created: $HOME/.local/share/fish/fish_history.backup.$(date +%Y%m%d_%H%M%S)"

    # Count matches
    matches=0
    for pattern in "${patterns[@]}"; do
        count=$(grep -c "$pattern" "$HOME/.local/share/fish/fish_history" 2>/dev/null || true)
        matches=$((matches + count))
    done

    if [[ $matches -gt 0 ]]; then
        echo "  ⚠ Found $matches potentially insecure command(s)"

        # Remove lines containing patterns
        for pattern in "${patterns[@]}"; do
            sed -i "/$pattern/d" "$HOME/.local/share/fish/fish_history"
        done

        echo "  ✓ Cleaned fish history"
        cleaned=$((cleaned + matches))
    else
        echo "  ✓ No issues found in fish history"
    fi
fi

# Clear in-memory history for current shell
echo ""
echo -e "${YELLOW}Clearing in-memory history...${NC}"
history -c 2>/dev/null || true
echo "  ✓ In-memory history cleared (if bash)"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [[ $cleaned -gt 0 ]]; then
    echo -e "${YELLOW}⚠ Removed $cleaned potentially insecure command(s) from history${NC}"
    echo ""
    echo "IMPORTANT NEXT STEPS:"
    echo ""
    echo "1. If you used those private keys, transfer funds to new wallets immediately"
    echo "2. Generate new wallets with encrypted keystores:"
    echo "   xai-wallet generate-address --save-keystore"
    echo ""
    echo "3. Never use private keys as CLI arguments again"
    echo "   Use --keystore instead for all operations"
    echo ""
else
    echo -e "${GREEN}✓ No issues found in shell history${NC}"
    echo ""
    echo "Good! Continue using secure methods:"
    echo "  - Encrypted keystore files (--keystore)"
    echo "  - Interactive secure input (default)"
    echo ""
fi

echo "Backups saved with timestamp for safety."
echo ""
