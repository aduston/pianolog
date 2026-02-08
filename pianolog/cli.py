"""
CLI entrypoint for pianolog.

`/main.py` delegates to `pianolog.cli.main()` to keep service scripts stable.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from typing import List, Optional

from pianolog.database import PracticeDatabase
from pianolog.tracker import PracticeTracker
from pianolog.user_selector import PianoUserSelector
import pianolog.config as config


def _configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("practice_tracker.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main(argv: Optional[List[str]] = None):
    """Main entry point."""
    _configure_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Piano Practice Tracker")
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help='User ID (e.g., "parent", "daughter"). If not provided, will prompt via piano.',
    )
    parser.add_argument(
        "--prompt-each-session",
        action="store_true",
        help="Prompt for user at the start of each session (for always-on mode)",
    )
    parser.add_argument("--show-sessions", action="store_true", help="Show recent sessions and exit")
    parser.add_argument("--show-summary", action="store_true", help="Show daily summary and exit")
    parser.add_argument("--clear-database", action="store_true", help="Clear all practice sessions from database")

    args = parser.parse_args(argv)

    if args.clear_database:
        db = PracticeDatabase()
        sessions = db.get_recent_sessions(limit=999999)
        count = len(sessions)

        if count == 0:
            print("\nDatabase is already empty.")
            db.close()
            return

        print(f"\n⚠️  WARNING: This will delete all {count} practice session(s) from the database!")
        print("This action cannot be undone.\n")
        response = input("Type 'yes' to confirm: ")

        if response.lower() == "yes":
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM practice_sessions")
            db.conn.commit()
            print(f"\n✓ Successfully deleted {count} session(s) from database.\n")
        else:
            print("\nCancelled. No data was deleted.\n")

        db.close()
        return

    if args.show_sessions:
        db = PracticeDatabase()
        sessions = db.get_recent_sessions(limit=20)
        print("\nRecent Practice Sessions:")
        print("=" * 80)
        for session in sessions:
            start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session["start_timestamp"]))
            duration_min = session["duration_seconds"] / 60
            print(
                f"{start} | {session['user_id']:12s} | {duration_min:6.1f} min | {session['note_count']:5d} notes"
            )
        db.close()
        return

    if args.show_summary:
        db = PracticeDatabase()
        summary = db.get_daily_summary(days=7)
        print("\nDaily Practice Summary (Last 7 Days):")
        print("=" * 80)
        for day in summary:
            total_min = day["total_seconds"] / 60
            print(
                f"{day['session_date']} | {day['user_id']:12s} | {day['session_count']:2d} sessions | {total_min:6.1f} min total"
            )
        db.close()
        return

    if args.prompt_each_session:
        tracker = PracticeTracker(prompt_on_session_start=True)
        print("\n" + "=" * 60)
        print("Piano Practice Tracker - Always-On Mode")
        print("=" * 60)
        print("System will prompt for user when practice is detected.")
        print("Monitoring piano activity...\n")
    else:
        if args.user:
            selected_user = args.user
        else:
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

        tracker = PracticeTracker(prompt_on_session_start=False)
        tracker.set_user(selected_user)

    def signal_handler(signum, frame):
        logger.info("Received signal %s", signum)
        tracker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    tracker.start()


if __name__ == "__main__":
    main()
