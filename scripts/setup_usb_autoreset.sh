#!/bin/bash
# Setup automatic USB reset for Kawai piano when power-cycled

set -e

echo "======================================================"
echo "Kawai Piano - Automatic USB Reset Setup"
echo "======================================================"
echo ""

# 1. Create udev rule for automatic reset
echo "[1/3] Creating udev rule for automatic USB reset..."
sudo tee /etc/udev/rules.d/99-kawai-piano-autoreset.rules > /dev/null << 'EOF'
# Automatically reset Kawai piano when it re-appears on USB bus
# This fixes the issue where power-cycling the piano leaves it in a stale state
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0f54", ATTRS{idProduct}=="0104", \
    RUN+="/bin/sh -c 'sleep 2 && /usr/bin/usbreset /dev/bus/usb/$env{BUSNUM}/$env{DEVNUM}'"
EOF

echo "   ✓ Created /etc/udev/rules.d/99-kawai-piano-autoreset.rules"

# 2. Disable USB autosuspend for piano
echo "[2/3] Disabling USB autosuspend for Kawai piano..."
sudo tee /etc/udev/rules.d/50-kawai-piano-power.rules > /dev/null << 'EOF'
# Disable USB autosuspend for Kawai piano to prevent power management issues
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0f54", ATTRS{idProduct}=="0104", \
    ATTR{power/control}="on", ATTR{power/autosuspend}="-1"
EOF

echo "   ✓ Created /etc/udev/rules.d/50-kawai-piano-power.rules"

# 3. Reload udev rules
echo "[3/3] Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "   ✓ udev rules reloaded"
echo ""
echo "======================================================"
echo "Setup Complete!"
echo "======================================================"
echo ""
echo "The system will now automatically reset the USB connection"
echo "when you power-cycle the piano."
echo ""
echo "To test:"
echo "  1. Turn off the piano"
echo "  2. Wait 5 seconds"
echo "  3. Turn the piano back on"
echo "  4. The USB connection should automatically recover!"
echo ""
echo "Monitor the process with:"
echo "  sudo journalctl -f | grep -i 'kawai\\|usb'"
echo ""
