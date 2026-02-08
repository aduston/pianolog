#!/usr/bin/env python3
"""
USB reset utility for Kawai piano.

When the piano is power-cycled, the USB connection may not re-enumerate properly.
This script resets the USB device to force reconnection.
"""
import subprocess
import sys
import time

def find_kawai_usb():
    """Find the Kawai piano USB device."""
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'Kawai' in line or '0f54:0104' in line:
                # Parse: Bus 001 Device 020: ID 0f54:0104 ...
                parts = line.split()
                bus = parts[1]
                device = parts[3].rstrip(':')
                return bus, device
        return None, None
    except Exception as e:
        print(f"Error finding device: {e}")
        return None, None

def reset_usb_device(bus, device):
    """Reset a USB device using usbreset."""
    device_path = f"/dev/bus/usb/{bus}/{device}"

    print(f"Resetting USB device at {device_path}...")

    # Use usbreset if available, otherwise use kernel unbind/bind
    try:
        # Try usbreset first (if installed)
        subprocess.run(['usbreset', device_path], check=True)
        print("Device reset successfully using usbreset")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Fallback: unbind/bind method
    try:
        # Find device in sysfs
        result = subprocess.run(
            ['find', '/sys/bus/usb/devices/', '-name', f'{bus}-*'],
            capture_output=True, text=True
        )

        for dev_path in result.stdout.splitlines():
            # Read device info
            try:
                with open(f'{dev_path}/devnum', 'r') as f:
                    devnum = f.read().strip()
                    if devnum == device:
                        # Found it - unbind and rebind
                        driver_path = f'{dev_path}/driver'
                        result = subprocess.run(['readlink', '-f', driver_path],
                                              capture_output=True, text=True)
                        if result.returncode == 0:
                            driver = result.stdout.strip()
                            dev_name = dev_path.split('/')[-1]

                            print(f"Unbinding device {dev_name}...")
                            with open(f'{driver}/unbind', 'w') as f:
                                f.write(dev_name)

                            time.sleep(1)

                            print(f"Rebinding device {dev_name}...")
                            with open(f'{driver}/bind', 'w') as f:
                                f.write(dev_name)

                            print("Device reset successfully using unbind/bind")
                            return True
            except:
                continue

    except Exception as e:
        print(f"Error during fallback reset: {e}")

    return False

def main():
    """Main entry point."""
    print("Kawai Piano USB Reset Utility")
    print("=" * 50)

    bus, device = find_kawai_usb()

    if not bus or not device:
        print("Kawai piano not found on USB bus.")
        print("Make sure the piano is powered on.")
        return 1

    print(f"Found Kawai piano: Bus {bus}, Device {device}")

    if reset_usb_device(bus, device):
        print("\nWaiting for device to re-enumerate...")
        time.sleep(3)

        # Verify it came back
        new_bus, new_device = find_kawai_usb()
        if new_bus and new_device:
            print(f"✓ Piano reconnected: Bus {new_bus}, Device {new_device}")
            return 0
        else:
            print("✗ Piano did not reconnect. Try unplugging and replugging USB.")
            return 1
    else:
        print("✗ Failed to reset device.")
        print("Try running with sudo or manually unplug/replug the USB cable.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
