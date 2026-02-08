#!/bin/bash
# Start pianolog with web interface
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting Piano Practice Tracker with Web Interface..."
echo ""

WEB_PORT=5000
if lsof -nP -iTCP:${WEB_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port ${WEB_PORT} is already in use; selecting another port..."
    for candidate in 5001 5002 5003 5004 5005; do
        if ! lsof -nP -iTCP:${candidate} -sTCP:LISTEN >/dev/null 2>&1; then
            WEB_PORT=${candidate}
            break
        fi
    done
fi

echo "Web interface will be available at:"
echo "  - Local:   http://localhost:${WEB_PORT}"
echo "  - Network: http://raspberrypi.local:${WEB_PORT}"
echo ""
if [ "${WEB_PORT}" = "5000" ]; then
    echo "To access via http://raspberrypi.local/pianolog, run ./setup_nginx.sh first"
else
    echo "Note: nginx /pianolog proxy expects backend on port 5000."
fi
echo ""

if [ ! -d "venv" ]; then
    echo "No virtual environment found. Creating ./venv ..."
    python3 -m venv venv || {
        echo "Failed to create virtual environment. Install python3-venv and retry."
        exit 1
    }
fi

source venv/bin/activate || {
    echo "Failed to activate virtual environment at ./venv."
    exit 1
}

if ! python -c "import mido" >/dev/null 2>&1; then
    echo "Installing Python dependencies from requirements.txt ..."
    pip install -r requirements.txt || {
        echo "Dependency installation failed."
        exit 1
    }
fi

python main.py --prompt-each-session --web-port "${WEB_PORT}"
