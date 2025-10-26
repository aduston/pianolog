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

    def __init__(self, prompt_on_session_start=False):
        """Initialize practice tracker components.

        Args:
            prompt_on_session_start: If True, prompt for user at each session start
        """
        self.db = PracticeDatabase()
        self.detector = PracticeDetector(
            activity_threshold=3,
            activity_window=10.0,
            min_practice_duration=30.0,
            session_timeout=15.0
        )
        self.midi_monitor = MidiMonitor(device_keyword='USB func for MIDI')

        # Current user
        self.current_user = "unknown"
        self.prompt_on_session_start = prompt_on_session_start
        self.waiting_for_user = False

        # User selection mapping
        self.user_notes = {
            60: "parent",    # Middle C
            62: "daughter"   # D
        }

        # Setup callbacks
        self.detector.on_session_start = self._on_session_start
        self.detector.on_session_end = self._on_session_end
        self.detector.on_session_reset = self._on_session_reset
        self.midi_monitor.on_note_on = self._on_note_on

        # Timeout checker thread
        self.timeout_thread = None
        self.running = False

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
                self.current_user = self.user_notes[note]
                logger.info(f"User selected via piano: {self.current_user}")
                print(f"\n*** {self.current_user.upper()} selected! ***\n")

                # Play confirmation chord
                self._play_confirmation()

                self.waiting_for_user = False

                # Now start detecting this session
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

    def _on_session_start(self):
        """Handle practice session start."""
        # Only announce if we already have a user
        if not self.waiting_for_user and self.current_user != "unknown":
            logger.info(f"Session started for user: {self.current_user}")
            print(f"\n*** Practice session started for {self.current_user} ***\n")

    def _on_session_end(self, start_time: float, end_time: float, note_count: int):
        """Handle practice session end."""
        duration_minutes = (end_time - start_time) / 60
        logger.info(f"Session ended: {duration_minutes:.1f} minutes, {note_count} notes")
        print(f"\n*** Practice session ended ***")
        print(f"Duration: {duration_minutes:.1f} minutes")
        print(f"Notes played: {note_count}\n")

        # Save to database
        self.db.save_session(self.current_user, start_time, end_time, note_count)

        # Reset user for next session in always-on mode
        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session ended, ready for next user")

    def _on_session_reset(self):
        """Handle session reset (called for ALL session ends, even short ones)."""
        if self.prompt_on_session_start:
            self.current_user = "unknown"
            logger.info("Session reset, ready for next user")

    def _timeout_checker(self):
        """Background thread to check for session timeouts."""
        while self.running:
            self.detector.check_timeout()
            time.sleep(1)

    def start(self):
        """Start the practice tracker."""
        self.running = True

        # Start timeout checker thread
        self.timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        self.timeout_thread.start()

        logger.info("Practice Tracker starting...")
        print("=" * 60)
        print("Piano Practice Tracker")
        print("=" * 60)
        print(f"Current user: {self.current_user}")
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

    args = parser.parse_args()

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

            users = {
                60: "parent",    # Middle C
                62: "daughter"   # D
            }

            selector = PianoUserSelector(users)
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
