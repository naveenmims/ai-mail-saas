#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/etc/aimail/aimail-api.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

# Generate a short new salt
NEWSALT="s$(date -u +%Y%m%d_%H%M%S)"

# If DEMO_DASHBOARD_SALT exists, replace it; else append it
if grep -q '^DEMO_DASHBOARD_SALT=' "$ENV_FILE"; then
  sudo sed -i "s/^DEMO_DASHBOARD_SALT=.*/DEMO_DASHBOARD_SALT=$NEWSALT/" "$ENV_FILE"
else
  echo "DEMO_DASHBOARD_SALT=$NEWSALT" | sudo tee -a "$ENV_FILE" >/dev/null
fi

sudo systemctl restart aimail-api
sleep 1

echo "OK: Set DEMO_DASHBOARD_SALT=$NEWSALT"
echo "Quick test:"
# Note: token is intentionally not printed here for safety
