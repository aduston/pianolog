"""
MIDI monitoring with automatic reconnection support.
"""
import mido
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class MidiMonitor:
    """
    Monitors MIDI input with automatic device detection and reconnection.
    """

    def __init__(self, device_keyword: str = 'USB func for MIDI', reconnect_interval: float = 5.0):
        """
        Initialize MIDI monitor.

        Args:
            device_keyword: Keyword to match in device name (empty for first device)
            reconnect_interval: Seconds to wait between reconnection attempts
        """
        self.device_keyword = device_keyword
        self.reconnect_interval = reconnect_interval
        self.inport: Optional[mido.ports.BaseInput] = None
        self.running = False

        # Callbacks
        self.on_note_on: Optional[Callable[[int, int, int], None]] = None
        self.on_note_off: Optional[Callable[[int, int], None]] = None
        self.on_control_change: Optional[Callable[[int, int], None]] = None

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
                return False

            # Close existing connection if any
            if self.inport:
                try:
                    self.inport.close()
                except:
                    pass

            self.inport = mido.open_input(port_name)
            logger.info(f"Connected to MIDI device: {port_name}")
            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.inport = None
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

    def start(self):
        """
        Start monitoring MIDI input.

        This method blocks and runs the monitoring loop. Call from a separate thread
        if you need non-blocking operation.
        """
        self.running = True
        logger.info("MIDI monitor started")

        while self.running:
            # Ensure connected
            if not self.inport:
                logger.info("Attempting to connect to MIDI device...")
                if not self.connect():
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
