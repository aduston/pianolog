#!/bin/bash
# Uninstallation script for Piano Practice Tracker service

set -e

echo "Uninstalling Piano Practice Tracker service..."

# Stop the service if running
echo "Stopping service..."
sudo systemctl stop piano-practice-tracker.service || true

# Disable service
echo "Disabling service..."
sudo systemctl disable piano-practice-tracker.service || true

# Remove service file
echo "Removing service file..."
sudo rm -f /etc/systemd/system/piano-practice-tracker.service

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "Service uninstalled successfully!"
