#!/usr/bin/env python3
"""
Quick test to detect MIDI devices and monitor incoming messages.
"""
import mido

print("Checking for MIDI devices...")
print("=" * 50)

# List available MIDI input ports
input_names = mido.get_input_names()
print(f"Available MIDI inputs: {len(input_names)}")
for i, name in enumerate(input_names):
    print(f"  [{i}] {name}")

if not input_names:
    print("\nNo MIDI devices found!")
    print("Make sure your piano is:")
    print("  1. Powered on")
    print("  2. Connected via USB")
    print("  3. Has Bluetooth MIDI disabled")
    exit(1)

print("\n" + "=" * 50)
print("Opening first MIDI device for monitoring...")
print("Play some notes on the piano!")
print("Press Ctrl+C to stop.")
print("=" * 50 + "\n")

try:
    with mido.open_input(input_names[0]) as inport:
        for msg in inport:
            if msg.type == 'note_on' and msg.velocity > 0:
                print(f"Note ON:  {msg.note:3d} (velocity: {msg.velocity:3d})")
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                print(f"Note OFF: {msg.note:3d}")
            elif msg.type == 'control_change':
                print(f"Control Change: CC{msg.control} = {msg.value}")
            else:
                print(f"Other: {msg}")
except KeyboardInterrupt:
    print("\n\nStopping MIDI monitor. Goodbye!")
