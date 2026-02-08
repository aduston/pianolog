#!/usr/bin/env python3
"""
Simple MIDI test that writes to a file.
"""
import mido
import sys
import time

# Force unbuffered output
sys.stdout = sys.stdout
sys.stderr = sys.stderr

print("Available MIDI inputs:", flush=True)
input_names = mido.get_input_names()
for name in input_names:
    print(f"  - {name}", flush=True)

if len(input_names) < 2:
    print("ERROR: Piano not detected!", flush=True)
    sys.exit(1)

# Use the second device (first is Midi Through)
piano_device = input_names[1]
print(f"\nListening to: {piano_device}", flush=True)
print("Play some notes! (Will capture 10 messages then stop)", flush=True)

count = 0
with mido.open_input(piano_device) as inport:
    for msg in inport:
        count += 1
        print(f"{count}. {msg}", flush=True)
        if count >= 10:
            break

print("\nDone! Test successful.", flush=True)
