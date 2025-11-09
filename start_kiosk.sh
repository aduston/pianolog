#!/bin/bash
# Kiosk mode script for pianolog web interface
# This script opens the pianolog web interface in fullscreen kiosk mode

# Wait a few seconds for the system and web server to be ready
sleep 10

# Disable screen blanking and screensaver
xset s off
xset s noblank
# Note: -dpms option not supported on this display, skipping

# Start chromium in kiosk mode
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --disable-features=TranslateUI \
  --disable-component-update \
  --check-for-update-interval=31536000 \
  --password-store=basic \
  http://localhost:5000?kiosk=true
