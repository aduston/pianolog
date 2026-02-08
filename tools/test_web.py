#!/usr/bin/env python3
"""
Simple test script for the web server without requiring MIDI device.
"""
import time
from pianolog.tracker import PracticeTracker

if __name__ == "__main__":
    print("Starting pianolog with web server (test mode)...")
    print("Note: This will fail if the MIDI device is not connected.")
    print("      To test without MIDI, we need to mock the MidiMonitor.")
    print()

    try:
        # Create tracker with web server enabled
        tracker = PracticeTracker(
            prompt_on_session_start=False,
            enable_web_server=True,
            web_port=5000
        )
        tracker.set_user("parent")

        # Start the tracker
        tracker.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo test the web interface without MIDI, access:")
        print("  http://localhost:5000")
        print("\nThe interface will work but show 'No active session'")
        print("until piano notes are detected.")
