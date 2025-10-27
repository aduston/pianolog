"""
Configuration for Piano Practice Tracker
"""

# User configuration
# Maps MIDI note numbers to user display names
USERS = {
    60: "Dad",    # Middle C
    62: "Alex"    # D
}

# Default MIDI device keyword
MIDI_DEVICE_KEYWORD = 'USB func for MIDI'

# Practice detection thresholds
ACTIVITY_THRESHOLD = 3  # Minimum notes per window to be considered active
ACTIVITY_WINDOW = 10.0  # Time window in seconds for activity detection
MIN_PRACTICE_DURATION = 30.0  # Minimum session duration in seconds to save
SESSION_TIMEOUT = 15.0  # Seconds of inactivity before ending session

# Web server configuration
WEB_PORT = 5000
