"""
Practice tracking core (MIDI monitoring + session detection + persistence + web updates).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import mido

from pianolog.database import PracticeDatabase
from pianolog.midi_monitor import MidiMonitor
from pianolog.practice_detector import PracticeDetector
from pianolog.web_server import PianologWebServer
import pianolog.config as config

logger = logging.getLogger(__name__)


class PracticeTracker:
    """Main practice tracking application."""

    def __init__(self, prompt_on_session_start: bool = False, enable_web_server: bool = True, web_port: Optional[int] = None):
        """Initialize practice tracker components."""
        self.db = PracticeDatabase()

        # Migrate users from config to database if needed
        self.db.migrate_users_from_config(config.USERS)

        self.detector = PracticeDetector(
            activity_threshold=config.ACTIVITY_THRESHOLD,
            activity_window=config.ACTIVITY_WINDOW,
            min_practice_duration=config.MIN_PRACTICE_DURATION,
            session_timeout=config.SESSION_TIMEOUT,
        )
        self.midi_monitor = MidiMonitor(device_keyword=config.MIDI_DEVICE_KEYWORD)

        self.current_user = "unknown"
        self.prompt_on_session_start = prompt_on_session_start
        self.waiting_for_user = False

        self._load_user_notes()

        self.web_server: Optional[PianologWebServer] = None
        if enable_web_server:
            port = web_port if web_port is not None else config.WEB_PORT
            self.web_server = PianologWebServer(self, port=port)

        self.detector.on_session_start = self._on_session_start
        self.detector.on_session_end = self._on_session_end
        self.detector.on_session_reset = self._on_session_reset
        self.midi_monitor.on_note_on = self._on_note_on
        self.midi_monitor.on_midi_connected = self._on_midi_connected
        self.midi_monitor.on_midi_disconnected = self._on_midi_disconnected

        self.timeout_thread: Optional[threading.Thread] = None
        self.running = False

    def _load_user_notes(self):
        """Load user->note mapping from database."""
        users = self.db.get_users()
        self.user_notes = {user["trigger_note"]: user["name"] for user in users}
        logger.info("Loaded %s users from database", len(self.user_notes))

    def set_user(self, user_id: str):
        """Set the current user who is practicing."""
        self.current_user = user_id
        logger.info("Current user set to: %s", user_id)

    def _play_prompt(self):
        """Play prompt melody to ask for user selection."""
        try:
            logger.info("Attempting to play prompt melody...")
            output_name = None
            for port in mido.get_output_names():
                if "USB func for MIDI" in port:
                    output_name = port
                    break

            if not output_name:
                logger.warning("No MIDI output port found for prompt")
                return

            logger.info("Opening MIDI output: %s", output_name)
            with mido.open_output(output_name) as outport:
                prompt_notes = [60, 64, 67]
                for note in prompt_notes:
                    outport.send(mido.Message("note_on", note=note, velocity=50))
                    time.sleep(0.2)
                    outport.send(mido.Message("note_off", note=note))
                    time.sleep(0.05)
                logger.info("Prompt melody played successfully")
        except Exception as e:
            logger.error("Error playing prompt: %s", e, exc_info=True)

    def _play_confirmation(self):
        """Play confirmation chord when user is selected."""
        try:
            logger.info("Attempting to play confirmation chord...")
            output_name = None
            for port in mido.get_output_names():
                if "USB func for MIDI" in port:
                    output_name = port
                    break

            if not output_name:
                logger.warning("No MIDI output port found for confirmation")
                return

            logger.info("Opening MIDI output: %s", output_name)
            with mido.open_output(output_name) as outport:
                chord_notes = [60, 64, 67]

                for note in chord_notes:
                    outport.send(mido.Message("note_on", note=note, velocity=60))

                time.sleep(0.4)

                for note in chord_notes:
                    outport.send(mido.Message("note_off", note=note))
                logger.info("Confirmation chord played successfully")
        except Exception as e:
            logger.error("Error playing confirmation: %s", e, exc_info=True)

    def _on_note_on(self, note: int, velocity: int, channel: int):
        """Handle MIDI note on event."""
        if self.waiting_for_user:
            if note in self.user_notes:
                selected_user = self.user_notes[note]
                logger.info("User selected via piano: %s", selected_user)
                print(f"\n*** {selected_user.upper()} selected! ***\n")

                self._play_confirmation()
                self.waiting_for_user = False
                self.set_user(selected_user)
                self.detector.force_start_session()
                self.detector.process_note_on(note, velocity)
            return

        if self.prompt_on_session_start and not self.detector.practice_session_active and self.current_user == "unknown":
            logger.info("First activity detected, prompting for user...")
            print("\n" + "=" * 60)
            print("WHO'S PRACTICING?")
            print("=" * 60)
            print("Press C (middle C) for parent")
            print("Press D for daughter")
            print("=" * 60 + "\n")

            self._play_prompt()

            if self.web_server:
                self.web_server.notify_user_selection_prompt()

            self.waiting_for_user = True
            return

        self.detector.process_note_on(note, velocity)

        if self.web_server and self.detector.practice_session_active:
            self.web_server.notify_session_activity()

    def _on_session_start(self):
        """Handle practice session start."""
        if not self.waiting_for_user and self.current_user != "unknown":
            logger.info("Session started for user: %s", self.current_user)
            print(f"\n*** Practice session started for {self.current_user} ***\n")

            if self.web_server:
                self.web_server.notify_session_start()

    def _on_session_end(self, start_time: float, end_time: float, note_count: int):
        """Handle practice session end."""
        duration_minutes = (end_time - start_time) / 60
        logger.info("Session ended: %.1f minutes, %s notes", duration_minutes, note_count)
        print("\n*** Practice session ended ***")
        print(f"Duration: {duration_minutes:.1f} minutes")
        print(f"Notes played: {note_count}\n")

        self.db.save_session(self.current_user, start_time, end_time, note_count)

        if self.web_server:
            self.web_server.notify_session_end(start_time, end_time, note_count)

        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session ended, ready for next user")

    def _on_session_reset(self):
        """Handle session reset (called for ALL session ends, even short ones)."""
        if self.web_server:
            self.web_server.socketio.emit(
                "session_ended",
                {
                    "user": self.current_user,
                    "timestamp": time.time(),
                },
            )

        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session reset, ready for next user")

    def _on_midi_connected(self, device_name: str):
        """Handle MIDI device connection."""
        logger.info("MIDI device connected: %s", device_name)
        print(f"\n*** MIDI device connected: {device_name} ***\n")

        if self.web_server:
            self.web_server.notify_midi_connected(device_name)

    def _on_midi_disconnected(self):
        """Handle MIDI device disconnection."""
        logger.warning("MIDI device disconnected")
        print("\n*** MIDI device disconnected - attempting to reconnect... ***\n")

        if self.web_server:
            self.web_server.notify_midi_disconnected()

    def _timeout_checker(self):
        """Background thread to check for session timeouts."""
        while self.running:
            self.detector.check_timeout()
            time.sleep(1)

    def start(self):
        """Start the practice tracker."""
        self.running = True

        if self.web_server:
            self.web_server.start()
            logger.info("Web interface available at http://localhost:%s", self.web_server.port)

        self.timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        self.timeout_thread.start()

        logger.info("Practice Tracker starting...")
        print("=" * 60)
        print("Piano Practice Tracker")
        print("=" * 60)
        print(f"Current user: {self.current_user}")
        if self.web_server:
            print(f"Web interface: http://localhost:{self.web_server.port}")
        print("\nTo change user, press Ctrl+C and restart with --user flag")
        print("Monitoring piano activity...\n")

        try:
            self.midi_monitor.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop()

    def stop(self):
        """Stop the practice tracker."""
        logger.info("Practice Tracker stopping...")
        self.running = False

        self.detector.force_end_session()
        self.midi_monitor.stop()

        if self.web_server:
            self.web_server.stop()

        self.db.close()

        print("\nPractice Tracker stopped. Goodbye!")
