#!/bin/bash
BASE_URL=${BASE_URL:-http://localhost:8545}
WH_TOKEN=${WH_TOKEN:-https://hooks.example/ai}
THRESHOLD=${THRESHOLD:-50000}

while true; do
  date
  python tools/ai_inspect.py --base-url "$BASE_URL"
  python tools/ai_alert.py --base-url "$BASE_URL" --token-threshold "$THRESHOLD" --webhook "$WH_TOKEN"
  sleep 300
done
