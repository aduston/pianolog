"""
Practice Tracker - Main entry point
"""
import logging
import signal
import sys
import threading
import time
from pathlib import Path
import mido

from database import PracticeDatabase
from practice_detector import PracticeDetector
from midi_monitor import MidiMonitor
from user_selector import PianoUserSelector
from web_server import PianologWebServer
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('practice_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class PracticeTracker:
    """Main practice tracking application."""

    def __init__(self, prompt_on_session_start=False, enable_web_server=True, web_port=None):
        """Initialize practice tracker components.

        Args:
            prompt_on_session_start: If True, prompt for user at each session start
            enable_web_server: If True, start the web server
            web_port: Port for the web server (defaults to config.WEB_PORT)
        """
        self.db = PracticeDatabase()

        # Migrate users from config to database if needed
        self.db.migrate_users_from_config(config.USERS)

        self.detector = PracticeDetector(
            activity_threshold=config.ACTIVITY_THRESHOLD,
            activity_window=config.ACTIVITY_WINDOW,
            min_practice_duration=config.MIN_PRACTICE_DURATION,
            session_timeout=config.SESSION_TIMEOUT
        )
        self.midi_monitor = MidiMonitor(device_keyword=config.MIDI_DEVICE_KEYWORD)

        # Current user
        self.current_user = "unknown"
        self.prompt_on_session_start = prompt_on_session_start
        self.waiting_for_user = False

        # User selection mapping - load from database
        self._load_user_notes()

        # Web server
        self.web_server = None
        if enable_web_server:
            port = web_port if web_port is not None else config.WEB_PORT
            self.web_server = PianologWebServer(self, port=port)

        # Setup callbacks
        self.detector.on_session_start = self._on_session_start
        self.detector.on_session_end = self._on_session_end
        self.detector.on_session_reset = self._on_session_reset
        self.midi_monitor.on_note_on = self._on_note_on
        self.midi_monitor.on_midi_connected = self._on_midi_connected
        self.midi_monitor.on_midi_disconnected = self._on_midi_disconnected

        # Timeout checker thread
        self.timeout_thread = None
        self.running = False

    def _load_user_notes(self):
        """Load user->note mapping from database."""
        users = self.db.get_users()
        self.user_notes = {user['trigger_note']: user['name'] for user in users}
        logger.info(f"Loaded {len(self.user_notes)} users from database")

    def set_user(self, user_id: str):
        """
        Set the current user who is practicing.

        Args:
            user_id: User identifier (e.g., "parent", "daughter")
        """
        self.current_user = user_id
        logger.info(f"Current user set to: {user_id}")

    def _play_prompt(self):
        """Play prompt melody to ask for user selection."""
        try:
            logger.info("Attempting to play prompt melody...")
            output_name = None
            for port in mido.get_output_names():
                if 'USB func for MIDI' in port:
                    output_name = port
                    break

            if not output_name:
                logger.warning("No MIDI output port found for prompt")
                return

            logger.info(f"Opening MIDI output: {output_name}")
            with mido.open_output(output_name) as outport:
                # Play C E G ascending
                prompt_notes = [60, 64, 67]
                for note in prompt_notes:
                    outport.send(mido.Message('note_on', note=note, velocity=50))
                    time.sleep(0.2)
                    outport.send(mido.Message('note_off', note=note))
                    time.sleep(0.05)
                logger.info("Prompt melody played successfully")
        except Exception as e:
            logger.error(f"Error playing prompt: {e}", exc_info=True)

    def _play_confirmation(self):
        """Play confirmation chord when user is selected."""
        try:
            logger.info("Attempting to play confirmation chord...")
            output_name = None
            for port in mido.get_output_names():
                if 'USB func for MIDI' in port:
                    output_name = port
                    break

            if not output_name:
                logger.warning("No MIDI output port found for confirmation")
                return

            logger.info(f"Opening MIDI output: {output_name}")
            with mido.open_output(output_name) as outport:
                # Play C major chord
                chord_notes = [60, 64, 67]

                for note in chord_notes:
                    outport.send(mido.Message('note_on', note=note, velocity=60))

                time.sleep(0.4)

                for note in chord_notes:
                    outport.send(mido.Message('note_off', note=note))
                logger.info("Confirmation chord played successfully")
        except Exception as e:
            logger.error(f"Error playing confirmation: {e}", exc_info=True)

    def _on_note_on(self, note: int, velocity: int, channel: int):
        """Handle MIDI note on event."""
        # If waiting for user selection, check if this is a selection key
        if self.waiting_for_user:
            if note in self.user_notes:
                selected_user = self.user_notes[note]
                logger.info(f"User selected via piano: {selected_user}")
                print(f"\n*** {selected_user.upper()} selected! ***\n")

                # Play confirmation chord
                self._play_confirmation()

                self.waiting_for_user = False

                # Set the user (this will notify web server)
                self.set_user(selected_user)

                # Force start the session immediately
                self.detector.force_start_session()

                # Process this note as part of the session
                self.detector.process_note_on(note, velocity)
            # Ignore other notes while waiting for selection
            return

        # In prompt-on-session mode, prompt IMMEDIATELY on first note
        if self.prompt_on_session_start and not self.detector.practice_session_active and self.current_user == "unknown":
            # First note detected - prompt for user
            logger.info("First activity detected, prompting for user...")
            print("\n" + "=" * 60)
            print("WHO'S PRACTICING?")
            print("=" * 60)
            print("Press C (middle C) for parent")
            print("Press D for daughter")
            print("=" * 60 + "\n")

            # Play prompt melody
            self._play_prompt()

            # Set flag to wait for user selection
            self.waiting_for_user = True
            return

        # Normal session detection
        self.detector.process_note_on(note, velocity)

        # Notify web server of activity
        if self.web_server and self.detector.practice_session_active:
            self.web_server.notify_session_activity()

    def _on_session_start(self):
        """Handle practice session start."""
        # Only announce if we already have a user
        if not self.waiting_for_user and self.current_user != "unknown":
            logger.info(f"Session started for user: {self.current_user}")
            print(f"\n*** Practice session started for {self.current_user} ***\n")

            # Notify web server
            if self.web_server:
                self.web_server.notify_session_start()

    def _on_session_end(self, start_time: float, end_time: float, note_count: int):
        """Handle practice session end."""
        duration_minutes = (end_time - start_time) / 60
        logger.info(f"Session ended: {duration_minutes:.1f} minutes, {note_count} notes")
        print(f"\n*** Practice session ended ***")
        print(f"Duration: {duration_minutes:.1f} minutes")
        print(f"Notes played: {note_count}\n")

        # Save to database
        self.db.save_session(self.current_user, start_time, end_time, note_count)

        # Notify web server
        if self.web_server:
            self.web_server.notify_session_end(start_time, end_time, note_count)

        # Reset user for next session in always-on mode
        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session ended, ready for next user")

    def _on_session_reset(self):
        """Handle session reset (called for ALL session ends, even short ones)."""
        # Notify web server that session ended (even if it was too short to save)
        if self.web_server:
            # For short sessions, use zeros for start/end/count since they won't be saved
            self.web_server.socketio.emit('session_ended', {
                'user': self.current_user,
                'timestamp': time.time()
            })

        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session reset, ready for next user")

    def _on_midi_connected(self, device_name: str):
        """Handle MIDI device connection."""
        logger.info(f"MIDI device connected: {device_name}")
        print(f"\n*** MIDI device connected: {device_name} ***\n")

        # Notify web server
        if self.web_server:
            self.web_server.notify_midi_connected(device_name)

    def _on_midi_disconnected(self):
        """Handle MIDI device disconnection."""
        logger.warning("MIDI device disconnected")
        print(f"\n*** MIDI device disconnected - attempting to reconnect... ***\n")

        # Notify web server
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

        # Start web server if enabled
        if self.web_server:
            self.web_server.start()
            logger.info(f"Web interface available at http://localhost:{self.web_server.port}")

        # Start timeout checker thread
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
            # Start MIDI monitoring (this blocks)
            self.midi_monitor.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop()

    def stop(self):
        """Stop the practice tracker."""
        logger.info("Practice Tracker stopping...")
        self.running = False

        # End any active session
        self.detector.force_end_session()

        # Stop MIDI monitoring
        self.midi_monitor.stop()

        # Stop web server
        if self.web_server:
            self.web_server.stop()

        # Close database
        self.db.close()

        print("\nPractice Tracker stopped. Goodbye!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Piano Practice Tracker')
    parser.add_argument('--user', type=str, default=None,
                       help='User ID (e.g., "parent", "daughter"). If not provided, will prompt via piano.')
    parser.add_argument('--prompt-each-session', action='store_true',
                       help='Prompt for user at the start of each session (for always-on mode)')
    parser.add_argument('--show-sessions', action='store_true',
                       help='Show recent sessions and exit')
    parser.add_argument('--show-summary', action='store_true',
                       help='Show daily summary and exit')
    parser.add_argument('--clear-database', action='store_true',
                       help='Clear all practice sessions from database')

    args = parser.parse_args()

    # Handle database clearing
    if args.clear_database:
        db = PracticeDatabase()

        # Get count of sessions for confirmation
        sessions = db.get_recent_sessions(limit=999999)
        count = len(sessions)

        if count == 0:
            print("\nDatabase is already empty.")
            db.close()
            return

        print(f"\n⚠️  WARNING: This will delete all {count} practice session(s) from the database!")
        print("This action cannot be undone.\n")
        response = input("Type 'yes' to confirm: ")

        if response.lower() == 'yes':
            cursor = db.conn.cursor()
            cursor.execute('DELETE FROM practice_sessions')
            db.conn.commit()
            print(f"\n✓ Successfully deleted {count} session(s) from database.\n")
        else:
            print("\nCancelled. No data was deleted.\n")

        db.close()
        return

    # Handle report commands
    if args.show_sessions:
        db = PracticeDatabase()
        sessions = db.get_recent_sessions(limit=20)
        print("\nRecent Practice Sessions:")
        print("=" * 80)
        for session in sessions:
            start = time.strftime('%Y-%m-%d %H:%M:%S',
                                time.localtime(session['start_timestamp']))
            duration_min = session['duration_seconds'] / 60
            print(f"{start} | {session['user_id']:12s} | "
                  f"{duration_min:6.1f} min | {session['note_count']:5d} notes")
        db.close()
        return

    if args.show_summary:
        db = PracticeDatabase()
        summary = db.get_daily_summary(days=7)
        print("\nDaily Practice Summary (Last 7 Days):")
        print("=" * 80)
        for day in summary:
            total_min = day['total_seconds'] / 60
            print(f"{day['session_date']} | {day['user_id']:12s} | "
                  f"{day['session_count']:2d} sessions | {total_min:6.1f} min total")
        db.close()
        return

    # Determine mode
    if args.prompt_each_session:
        # Always-on mode: prompt at each session start
        tracker = PracticeTracker(prompt_on_session_start=True)
        print("\n" + "=" * 60)
        print("Piano Practice Tracker - Always-On Mode")
        print("=" * 60)
        print("System will prompt for user when practice is detected.")
        print("Monitoring piano activity...\n")
    else:
        # Determine user once
        if args.user:
            # User specified via command line
            selected_user = args.user
        else:
            # Interactive piano selection
            print("\n" + "=" * 60)
            print("Piano Practice Tracker - User Selection")
            print("=" * 60)
            print("The piano will play a prompt melody...")
            print()

            selector = PianoUserSelector(config.USERS)
            selected_user = selector.select_user(timeout=30.0)

            if selected_user == "unknown":
                print("No user selected. Exiting.")
                return

        # Start practice tracker with pre-selected user
        tracker = PracticeTracker(prompt_on_session_start=False)
        tracker.set_user(selected_user)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        tracker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    tracker.start()


if __name__ == "__main__":
    main()
