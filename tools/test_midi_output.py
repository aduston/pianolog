#!/usr/bin/env python3
"""
Test playing notes on the piano via MIDI output.
"""
import mido
import time

# Find the piano output
outputs = mido.get_output_names()
print("Available MIDI outputs:")
for name in outputs:
    print(f"  - {name}")

# Use the piano (second device, skipping Midi Through)
piano_output = outputs[1]
print(f"\nUsing: {piano_output}")

with mido.open_output(piano_output) as outport:
    print("\nPlaying a C major scale...")

    # C major scale: C D E F G A B C
    notes = [60, 62, 64, 65, 67, 69, 71, 72]  # MIDI note numbers

    for note in notes:
        # Note on with velocity 64 (medium volume)
        outport.send(mido.Message('note_on', note=note, velocity=64))
        time.sleep(0.3)  # Hold for 300ms

        # Note off
        outport.send(mido.Message('note_off', note=note))
        time.sleep(0.1)  # Small gap between notes

    print("Done!")
