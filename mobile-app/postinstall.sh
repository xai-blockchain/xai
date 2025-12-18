#!/bin/bash

# Postinstall script for XAI Wallet

echo "Running postinstall..."

# Run rn-nodeify to shim Node.js modules
./node_modules/.bin/rn-nodeify --install crypto,stream,buffer,process,vm --hack

echo "Postinstall complete!"
