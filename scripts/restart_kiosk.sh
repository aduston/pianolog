#!/bin/bash
# Restart the kiosk browser to pick up front-end changes
# Useful after modifying templates/index.html

echo "Restarting kiosk browser..."

# Kill the existing kiosk browser
pkill -f "chromium.*kiosk"

# Wait a moment for it to fully shut down
sleep 2

# Restart the kiosk
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DISPLAY=:0 "$ROOT_DIR/scripts/start_kiosk.sh" &

echo "Kiosk browser restarting (will be ready in ~12 seconds)..."
