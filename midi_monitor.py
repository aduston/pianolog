"""
MIDI monitoring with automatic reconnection support.
"""
import mido
import pyudev
import subprocess
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class MidiMonitor:
    """
    Monitors MIDI input with automatic device detection and reconnection.
    """

    def __init__(self, device_keyword: str = 'USB func for MIDI', reconnect_interval: float = 5.0, health_check_interval: float = 2.0, enable_usb_reset: bool = True):
        """
        Initialize MIDI monitor.

        Args:
            device_keyword: Keyword to match in device name (empty for first device)
            reconnect_interval: Seconds to wait between reconnection attempts
            health_check_interval: Seconds between health checks of connection
            enable_usb_reset: If True, automatically power-cycle USB port on reconnection failure
        """
        self.device_keyword = device_keyword
        self.reconnect_interval = reconnect_interval
        self.health_check_interval = health_check_interval
        self.enable_usb_reset = enable_usb_reset
        self.inport: Optional[mido.ports.BaseInput] = None
        self.running = False
        self.is_connected = False
        self.last_connected_device: Optional[str] = None
        self.last_health_check = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts_before_reset = 3  # Try 3 times before USB reset
        self.usb_reset_performed = False  # Track if we've already done a USB reset
        self.last_usb_reset_time = 0  # Track when last USB reset was done

        # USB device monitoring for instant reconnection
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb')

        # Callbacks
        self.on_note_on: Optional[Callable[[int, int, int], None]] = None
        self.on_note_off: Optional[Callable[[int, int], None]] = None
        self.on_control_change: Optional[Callable[[int, int], None]] = None
        self.on_midi_connected: Optional[Callable[[str], None]] = None  # Called when MIDI connects
        self.on_midi_disconnected: Optional[Callable[[], None]] = None  # Called when MIDI disconnects

    def find_device(self) -> Optional[str]:
        """
        Find MIDI input device matching keyword.

        Returns:
            Device name if found, None otherwise
        """
        try:
            ports = mido.get_input_names()

            if not ports:
                return None

            # If no keyword, skip the "Midi Through" port
            if not self.device_keyword:
                for port in ports:
                    if 'Midi Through' not in port:
                        return port
                return None

            # Find port matching keyword
            for port in ports:
                if self.device_keyword.lower() in port.lower():
                    return port

            return None
        except Exception as e:
            logger.error(f"Error finding MIDI device: {e}")
            return None

    def connect(self) -> bool:
        """
        Connect to MIDI device.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            port_name = self.find_device()

            if not port_name:
                logger.warning("No MIDI device found")
                # Mark as disconnected if we were previously connected
                if self.is_connected:
                    self.is_connected = False
                    if self.on_midi_disconnected:
                        self.on_midi_disconnected()
                return False

            # Close existing connection if any
            if self.inport:
                try:
                    self.inport.close()
                except:
                    pass

            self.inport = mido.open_input(port_name)
            logger.info(f"Connected to MIDI device: {port_name}")

            # Mark as connected and trigger callback
            was_connected = self.is_connected
            self.is_connected = True
            self.last_connected_device = port_name

            if not was_connected and self.on_midi_connected:
                self.on_midi_connected(port_name)

            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.inport = None
            # Mark as disconnected if we were previously connected
            if self.is_connected:
                self.is_connected = False
                if self.on_midi_disconnected:
                    self.on_midi_disconnected()
            return False

    def force_reconnect_with_power_cycle(self) -> bool:
        """
        Force a reconnection attempt with USB power cycling, bypassing cooldown.
        This is called when the user manually triggers reconnection via the UI.

        Returns:
            True if reconnection successful, False otherwise
        """
        logger.info("Manual reconnection requested - forcing USB power cycle")

        # Disconnect current connection if any
        if self.inport:
            try:
                self.inport.close()
            except:
                pass
            self.inport = None

        # First try a simple connection (device might already be available)
        if self.connect():
            logger.info("Manual reconnection successful without power cycle")
            return True

        # If simple connection fails and USB reset is enabled, force power cycle
        if self.enable_usb_reset:
            logger.info("Simple connection failed - performing USB power cycle")
            if self.reset_usb_port(bypass_cooldown=True):
                # Update tracking after successful reset
                self.last_usb_reset_time = time.time()
                self.reconnect_attempts = 0
                self.usb_reset_performed = True

                # Try to connect after power cycle
                return self.connect()

        return False

    def disconnect(self):
        """Disconnect from MIDI device."""
        if self.inport:
            try:
                self.inport.close()
                logger.info("Disconnected from MIDI device")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.inport = None
                was_connected = self.is_connected
                self.is_connected = False
                if was_connected and self.on_midi_disconnected:
                    self.on_midi_disconnected()

    def check_device_health(self) -> bool:
        """
        Check if the currently connected device still exists.

        Returns:
            True if device exists and is healthy, False otherwise
        """
        if not self.is_connected or not self.last_connected_device:
            return False

        # Check if the device still appears in the available ports
        try:
            available_ports = mido.get_input_names()
            return self.last_connected_device in available_ports
        except Exception as e:
            logger.error(f"Error checking device health: {e}")
            return False

    def reset_usb_port(self, port: int = 1, bypass_cooldown: bool = False) -> bool:
        """
        Power-cycle the USB port to force device re-enumeration.
        This works around piano firmware issues that prevent proper USB re-initialization.

        Args:
            port: USB port number (1-4 on Raspberry Pi 4)
            bypass_cooldown: If True, bypass the cooldown period check

        Returns:
            True if reset was successful, False otherwise
        """
        try:
            logger.info(f"Attempting USB port {port} power cycle...")

            # Turn off both USB 2.0 (hub 1-1) and USB 3.0 (hub 2) virtual hubs
            # This is necessary for proper power cycling on Raspberry Pi
            subprocess.run(['sudo', 'uhubctl', '-l', '1-1', '-p', str(port), '-a', 'off'],
                         check=True, capture_output=True, timeout=10)
            subprocess.run(['sudo', 'uhubctl', '-l', '2', '-p', str(port), '-a', 'off'],
                         check=True, capture_output=True, timeout=10)

            # Wait for power to stabilize
            time.sleep(2)

            # Turn back on
            subprocess.run(['sudo', 'uhubctl', '-l', '1-1', '-p', str(port), '-a', 'on'],
                         check=True, capture_output=True, timeout=10)
            subprocess.run(['sudo', 'uhubctl', '-l', '2', '-p', str(port), '-a', 'on'],
                         check=True, capture_output=True, timeout=10)

            # Wait for device enumeration
            logger.info("USB port reset complete, waiting for device enumeration...")
            time.sleep(3)

            logger.info("USB port power cycle successful")
            return True

        except subprocess.TimeoutExpired:
            logger.error("USB reset timeout")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"USB reset failed: {e}")
            return False
        except Exception as e:
            logger.error(f"USB reset error: {e}")
            return False

    def check_usb_events(self):
        """
        Check for USB device add/remove events (non-blocking).
        This provides instant reconnection when the piano is power-cycled.
        """
        device = self.monitor.poll(timeout=0)
        if device and device.action in ['add', 'remove']:
            logger.info(f"USB device {device.action} event detected")

            # Wait briefly for device enumeration after add
            if device.action == 'add':
                time.sleep(1.0)

            # For both add and remove, trigger a reconnection attempt
            # This will handle both new connections and re-establishing after removal
            if device.action == 'add' and not self.inport:
                logger.info("USB device added - attempting connection")
                # Reset reconnect counter and USB reset flag on new USB device
                self.reconnect_attempts = 0
                self.usb_reset_performed = False
                self.connect()
            elif device.action == 'remove':
                logger.info("USB device removed - disconnecting")
                # Reset reconnect counter on device removal, but NOT usb_reset_performed
                # This prevents multiple resets if piano stays off
                self.reconnect_attempts = 0
                # The device might be ours, so disconnect and let the main loop reconnect
                if self.inport:
                    self.inport = None
                    if self.is_connected:
                        self.is_connected = False
                        if self.on_midi_disconnected:
                            self.on_midi_disconnected()

    def start(self):
        """
        Start monitoring MIDI input.

        This method blocks and runs the monitoring loop. Call from a separate thread
        if you need non-blocking operation.
        """
        self.running = True
        logger.info("MIDI monitor started")

        while self.running:
            # Check for USB device add/remove events (instant reconnection)
            self.check_usb_events()

            # Ensure connected
            if not self.inport:
                logger.info("Attempting to connect to MIDI device...")
                if not self.connect():
                    self.reconnect_attempts += 1

                    # After multiple failed attempts, try USB power cycle (but only once)
                    if (self.enable_usb_reset and
                        self.reconnect_attempts >= self.max_reconnect_attempts_before_reset and
                        not self.usb_reset_performed):

                        # Check if we've done a USB reset recently (within 5 minutes)
                        time_since_last_reset = time.time() - self.last_usb_reset_time
                        if time_since_last_reset < 300:  # 5 minutes
                            logger.info(f"USB reset performed {time_since_last_reset:.0f}s ago, skipping")
                        else:
                            logger.warning(f"Failed {self.reconnect_attempts} reconnection attempts, "
                                         "attempting USB port power cycle...")
                            if self.reset_usb_port():
                                # Mark that we've done a USB reset and when
                                self.usb_reset_performed = True
                                self.last_usb_reset_time = time.time()
                                self.reconnect_attempts = 0
                            else:
                                # If USB reset failed, wait longer before next attempt
                                logger.error("USB port power cycle failed")
                                time.sleep(self.reconnect_interval * 2)
                                continue

                    time.sleep(self.reconnect_interval)
                    continue
                else:
                    # Successfully connected, reset counter and USB reset flag
                    self.reconnect_attempts = 0
                    self.usb_reset_performed = False

            # Periodic health check to detect device removal
            current_time = time.time()
            if current_time - self.last_health_check >= self.health_check_interval:
                self.last_health_check = current_time
                if not self.check_device_health():
                    logger.warning("Device health check failed - device removed")
                    self.inport = None
                    if self.is_connected:
                        self.is_connected = False
                        if self.on_midi_disconnected:
                            self.on_midi_disconnected()
                    time.sleep(self.reconnect_interval)
                    continue

            try:
                # Process MIDI messages (non-blocking)
                for msg in self.inport.iter_pending():
                    self._process_message(msg)

                time.sleep(0.01)  # Small sleep to prevent CPU spinning

            except Exception as e:
                logger.error(f"Error reading MIDI: {e}")
                self.inport = None
                # Mark as disconnected
                if self.is_connected:
                    self.is_connected = False
                    if self.on_midi_disconnected:
                        self.on_midi_disconnected()
                time.sleep(self.reconnect_interval)

        # Cleanup
        self.disconnect()
        logger.info("MIDI monitor stopped")

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False

    def _process_message(self, msg: mido.Message):
        """
        Process a MIDI message and call appropriate callback.

        Args:
            msg: MIDI message to process
        """
        try:
            if msg.type == 'note_on':
                if msg.velocity > 0:
                    # Actual note on
                    if self.on_note_on:
                        self.on_note_on(msg.note, msg.velocity, msg.channel)
                else:
                    # Note on with velocity 0 = note off
                    if self.on_note_off:
                        self.on_note_off(msg.note, msg.channel)

            elif msg.type == 'note_off':
                if self.on_note_off:
                    self.on_note_off(msg.note, msg.channel)

            elif msg.type == 'control_change':
                if self.on_control_change:
                    self.on_control_change(msg.control, msg.value)

        except Exception as e:
            logger.error(f"Error processing MIDI message: {e}")
