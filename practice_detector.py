"""
Practice session detection logic based on MIDI activity.

IMPORTANT: This module handles TWO distinct concepts:

1. SESSION: An active practice session that tracks a user's playing activity.
   - Starts when a user identifies themselves (via force_start_session)
   - Ends when they stop playing for session_timeout seconds or manually end it
   - Shown as "active session" in the web interface

2. RECORDED SESSION: A session that meets the minimum duration requirement.
   - Only sessions >= min_practice_duration get saved to the database
   - Shorter sessions are still valid sessions, just not recorded/saved
   - Example: Playing for 10 seconds is a session, but not a recorded session
"""
import time
from collections import deque
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class PracticeDetector:
    """
    Detects practice sessions based on MIDI note activity.

    This class manages the lifecycle of practice sessions, distinguishing between:
    - Active sessions: Started when user identified (via force_start_session)
    - Recorded sessions: Active sessions that meet min_practice_duration to be saved

    Callbacks:
    - on_session_start: Called when ANY session starts (active session begins)
    - on_session_end: Called ONLY for sessions >= min_practice_duration (recorded session)
    - on_session_reset: Called when ANY session ends (whether recorded or not)
    """

    def __init__(self,
                 activity_threshold: int = 3,
                 activity_window: float = 10.0,
                 min_practice_duration: float = 30.0,
                 session_timeout: float = 15.0):
        """
        Initialize practice detector.

        Args:
            activity_threshold: Minimum notes within activity_window to auto-start session
                              (typically not used; use force_start_session after user ID)
            activity_window: Time window (seconds) to check for activity threshold
            min_practice_duration: Minimum duration (seconds) for a RECORDED session.
                                 Sessions shorter than this are valid but won't be saved.
            session_timeout: Seconds of inactivity before ending any active session
        """
        self.activity_threshold = activity_threshold
        self.activity_window = activity_window
        self.min_practice_duration = min_practice_duration
        self.session_timeout = session_timeout

        # Session state
        self.practice_session_active = False
        self.session_start_time: Optional[float] = None
        self.session_note_count = 0
        self.last_note_time: Optional[float] = None

        # Activity tracking
        self.recent_notes = deque()

        # Callbacks
        self.on_session_start: Optional[Callable] = None
        self.on_session_end: Optional[Callable[[float, float, int], None]] = None
        self.on_session_reset: Optional[Callable] = None  # Called on ANY session end

    def process_note_on(self, note: int, velocity: int) -> bool:
        """
        Process a MIDI note_on event.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)

        Returns:
            True if currently in an active practice session
        """
        current_time = time.time()
        self.last_note_time = current_time

        # Track note activity
        self.recent_notes.append(current_time)
        self.session_note_count += 1

        # Remove old notes outside activity window
        while self.recent_notes and current_time - self.recent_notes[0] > self.activity_window:
            self.recent_notes.popleft()

        # Check if practice session should start
        if not self.practice_session_active and len(self.recent_notes) >= self.activity_threshold:
            self._start_session()

        return self.practice_session_active

    def check_timeout(self) -> bool:
        """
        Check if current session has timed out due to inactivity.

        Should be called periodically (e.g., every second) to detect session end.

        Returns:
            True if still in active session, False if session ended
        """
        if not self.practice_session_active:
            return False

        current_time = time.time()

        # Check if session has timed out
        if self.last_note_time and current_time - self.last_note_time > self.session_timeout:
            self._end_session()
            return False

        return True

    def force_end_session(self):
        """Force end the current session (e.g., when shutting down)."""
        if self.practice_session_active:
            self._end_session()

    def force_start_session(self):
        """Force start a session (e.g., after user selection in prompt mode)."""
        if not self.practice_session_active:
            self._start_session()

    def _start_session(self):
        """Start a new practice session."""
        self.practice_session_active = True
        self.session_start_time = time.time()
        self.session_note_count = 0

        logger.info(f"Practice session started at {time.strftime('%H:%M:%S', time.localtime(self.session_start_time))}")

        if self.on_session_start:
            self.on_session_start()

    def _end_session(self):
        """End the current practice session."""
        if not self.practice_session_active or not self.session_start_time:
            return

        end_time = time.time()
        duration = end_time - self.session_start_time

        # Only save sessions that meet minimum duration
        if duration >= self.min_practice_duration:
            logger.info(f"Practice session ended: {duration/60:.1f} minutes, "
                       f"{self.session_note_count} notes")

            if self.on_session_end:
                self.on_session_end(self.session_start_time, end_time, self.session_note_count)
        else:
            logger.info(f"Session too short ({duration:.1f}s), not saving")

        # Reset session state
        self.practice_session_active = False
        self.session_start_time = None
        self.session_note_count = 0
        self.recent_notes.clear()

        # Call reset callback for ANY session end (even short ones)
        if self.on_session_reset:
            self.on_session_reset()

    def get_session_info(self) -> Optional[dict]:
        """
        Get information about current session.

        Returns:
            Dict with session info if active, None otherwise
        """
        if not self.practice_session_active or not self.session_start_time:
            return None

        current_time = time.time()
        return {
            'start_time': self.session_start_time,
            'duration': current_time - self.session_start_time,
            'note_count': self.session_note_count,
            'last_activity': self.last_note_time
        }
