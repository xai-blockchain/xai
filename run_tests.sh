#!/bin/bash
# Crypto Project - Run Python Tests (Bash version)
# This script ensures Python is correctly located and runs pytest

set -e

echo -e "\033[36mCrypto Project - Running Python Tests\033[0m"
echo -e "\033[36m======================================\n\033[0m"

# Define Python paths
PYTHON314="/c/Users/decri/AppData/Local/Programs/Python/Python314/python.exe"
PYTHON313="/c/Users/decri/AppData/Local/Programs/Python/Python313/python.exe"

# Check which Python is available
PYTHON_EXE=""
if [ -f "$PYTHON314" ]; then
    PYTHON_EXE="$PYTHON314"
    echo -e "\033[32mUsing Python 3.14\033[0m"
elif [ -f "$PYTHON313" ]; then
    PYTHON_EXE="$PYTHON313"
    echo -e "\033[32mUsing Python 3.13\033[0m"
else
    echo -e "\033[31mERROR: Python not found at expected locations\033[0m"
    exit 1
fi

# Change to Crypto directory
cd "/c/Users/decri/GitClones/Crypto"

# Show Python version
echo -e "\n\033[36mPython version:\033[0m"
"$PYTHON_EXE" --version

# Run pytest
echo -e "\n\033[36mRunning pytest...\033[0m"
"$PYTHON_EXE" -m pytest "$@"

echo -e "\n\033[32mDone!\033[0m"
