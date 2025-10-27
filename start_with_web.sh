#!/bin/bash
# Start pianolog with web interface

cd /home/aduston/pianolog

echo "Starting Piano Practice Tracker with Web Interface..."
echo ""
echo "Web interface will be available at:"
echo "  - Local:   http://localhost:5000"
echo "  - Network: http://raspberrypi.local:5000"
echo ""
echo "To access via http://raspberrypi.local/pianolog, run ./setup_nginx.sh first"
echo ""

source venv/bin/activate
python main.py --prompt-each-session
