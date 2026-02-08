#!/bin/bash
# Installation script for Piano Practice Tracker service

set -e

echo "Installing Piano Practice Tracker as a system service..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy service file to systemd directory
echo "Copying service file..."
sudo cp "$SCRIPT_DIR/piano-practice-tracker.service" /etc/systemd/system/

# Reload systemd to recognize new service
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service..."
sudo systemctl enable piano-practice-tracker.service

# Start the service
echo "Starting service..."
sudo systemctl start piano-practice-tracker.service

# Show status
echo ""
echo "Service installed and started!"
echo "=" * 60
echo ""
echo "Useful commands:"
echo "  View status:  sudo systemctl status piano-practice-tracker"
echo "  View logs:    sudo journalctl -u piano-practice-tracker -f"
echo "  Stop:         sudo systemctl stop piano-practice-tracker"
echo "  Restart:      sudo systemctl restart piano-practice-tracker"
echo "  Disable:      sudo systemctl disable piano-practice-tracker"
echo ""
