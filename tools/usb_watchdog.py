#!/usr/bin/env python3
"""
USB Watchdog for Kawai Piano

Monitors the piano USB connection and automatically attempts to reset it
when it detects the device is in a stale state (visible in lsusb but not working).
"""
import subprocess
import time
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class USBWatchdog:
    def __init__(self, vendor_id='0f54', product_id='0104', check_interval=10):
        """
        Initialize USB watchdog.

        Args:
            vendor_id: USB vendor ID for Kawai
            product_id: USB product ID for piano
            check_interval: Seconds between checks
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.check_interval = check_interval
        self.device_id = f"{vendor_id}:{product_id}"

    def is_device_in_usb_list(self):
        """Check if device appears in lsusb."""
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            return self.device_id in result.stdout
        except Exception as e:
            logger.error(f"Error checking lsusb: {e}")
            return False

    def is_device_working(self):
        """Check if device is actually working (appears in MIDI devices)."""
        try:
            repo_root = Path(__file__).resolve().parent.parent
            result = subprocess.run(
                ['python3', '-c', 'import mido; print(mido.get_input_names())'],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
                timeout=5
            )
            return 'USB func for MIDI' in result.stdout
        except Exception as e:
            logger.error(f"Error checking MIDI devices: {e}")
            return False

    def reset_usb_bus(self):
        """
        Attempt to reset the USB bus by unbinding/rebinding the USB controller.
        This is a last resort that may temporarily disconnect other USB devices.
        """
        logger.warning("Attempting USB bus reset...")
        try:
            # Find USB controller in /sys
            result = subprocess.run(
                ['find', '/sys/bus/pci/drivers/', '-name', '*usb*'],
                capture_output=True,
                text=True
            )

            for driver_path in result.stdout.strip().split('\n'):
                if driver_path and 'xhci' in driver_path.lower():
                    # Found xHCI USB controller
                    logger.info(f"Found USB controller: {driver_path}")

                    # Get list of devices
                    devices = subprocess.run(
                        ['ls', driver_path],
                        capture_output=True,
                        text=True
                    ).stdout.strip().split('\n')

                    for device in devices:
                        if ':' in device and device != 'bind' and device != 'unbind':
                            # This looks like a PCI device
                            logger.info(f"Unbinding {device}...")
                            try:
                                subprocess.run(
                                    ['sudo', 'tee', f'{driver_path}/unbind'],
                                    input=device.encode(),
                                    check=True,
                                    capture_output=True
                                )
                                time.sleep(2)

                                logger.info(f"Rebinding {device}...")
                                subprocess.run(
                                    ['sudo', 'tee', f'{driver_path}/bind'],
                                    input=device.encode(),
                                    check=True,
                                    capture_output=True
                                )
                                time.sleep(3)

                                logger.info("USB bus reset complete")
                                return True
                            except Exception as e:
                                logger.error(f"Failed to reset {device}: {e}")
                                continue

            logger.error("Could not find USB controller to reset")
            return False

        except Exception as e:
            logger.error(f"USB bus reset failed: {e}")
            return False

    def run(self):
        """Main watchdog loop."""
        logger.info("USB Watchdog started")
        logger.info(f"Monitoring for device: {self.device_id}")

        consecutive_failures = 0

        while True:
            try:
                in_usb = self.is_device_in_usb_list()
                working = self.is_device_working()

                if in_usb and working:
                    # Device is healthy
                    if consecutive_failures > 0:
                        logger.info("Device recovered!")
                    consecutive_failures = 0

                elif in_usb and not working:
                    # Device is visible but not working - STALE STATE
                    consecutive_failures += 1
                    logger.warning(
                        f"Device in stale state (attempt {consecutive_failures}): "
                        f"visible in lsusb but not working"
                    )

                    if consecutive_failures >= 3:
                        logger.error("Device stuck in stale state. Reset required.")
                        logger.info("=" * 60)
                        logger.info("MANUAL ACTION REQUIRED:")
                        logger.info("Please unplug and replug the USB cable")
                        logger.info("=" * 60)

                        # Wait longer before checking again
                        time.sleep(60)
                        consecutive_failures = 0

                elif not in_usb and not working:
                    # Device completely disconnected
                    if consecutive_failures == 0:
                        logger.info("Device disconnected (piano may be off)")
                    consecutive_failures = 0

                else:
                    # Device working but not in usb list (shouldn't happen)
                    consecutive_failures = 0

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Watchdog stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in watchdog loop: {e}")
                time.sleep(self.check_interval)


def main():
    """Entry point."""
    watchdog = USBWatchdog(check_interval=10)
    watchdog.run()


if __name__ == "__main__":
    main()
