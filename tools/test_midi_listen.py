#!/usr/bin/env python3
"""
Test MIDI input - listen for notes and print them
"""
import mido
import sys

print("Looking for MIDI input device...")
inputs = mido.get_input_names()
print(f"Available inputs: {inputs}")

# Find the USB MIDI device
device = None
for name in inputs:
    if 'USB func for MIDI' in name:
        device = name
        break

if not device:
    print("ERROR: No USB MIDI device found!")
    sys.exit(1)

print(f"\nOpening: {device}")
print("Play some notes on your piano...")
print("Press Ctrl+C to stop\n")

try:
    with mido.open_input(device) as inport:
        for msg in inport:
            if msg.type == 'note_on' and msg.velocity > 0:
                print(f"NOTE ON: note={msg.note}, velocity={msg.velocity}, channel={msg.channel}")
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                print(f"NOTE OFF: note={msg.note}")
except KeyboardInterrupt:
    print("\nStopped")
