"""
Interactive user selection via piano keyboard.
"""
import mido
import time
import logging

logger = logging.getLogger(__name__)


class PianoUserSelector:
    """
    Interactive user selection using the piano keyboard.

    Plays a prompt and waits for user to press a key to identify themselves.
    """

    def __init__(self, users: dict):
        """
        Initialize user selector.

        Args:
            users: Dict mapping MIDI note numbers to user IDs
                   e.g., {60: "parent", 62: "daughter"}  (C=parent, D=daughter)
        """
        self.users = users
        self.output_port = None
        self.input_port = None

    def _find_piano_ports(self):
        """Find piano MIDI input and output ports."""
        outputs = mido.get_output_names()
        inputs = mido.get_input_names()

        # Find piano (skip Midi Through)
        piano_out = None
        piano_in = None

        for port in outputs:
            if 'USB func for MIDI' in port:
                piano_out = port
                break

        for port in inputs:
            if 'USB func for MIDI' in port:
                piano_in = port
                break

        return piano_in, piano_out

    def _play_prompt_melody(self):
        """Play a short melody to prompt user selection."""
        # Play a simple ascending pattern (C E G)
        prompt_notes = [60, 64, 67]

        for note in prompt_notes:
            self.output_port.send(mido.Message('note_on', note=note, velocity=50))
            time.sleep(0.2)
            self.output_port.send(mido.Message('note_off', note=note))
            time.sleep(0.05)

    def _play_confirmation(self, user_id: str):
        """Play confirmation sound when user is selected."""
        # Play a quick chord (C major chord: C E G played together)
        chord_notes = [60, 64, 67]

        # Play chord
        for note in chord_notes:
            self.output_port.send(mido.Message('note_on', note=note, velocity=60))

        time.sleep(0.4)

        # Release chord
        for note in chord_notes:
            self.output_port.send(mido.Message('note_off', note=note))

    def select_user(self, timeout: float = 30.0) -> str:
        """
        Prompt user to select themselves by pressing a key.

        Args:
            timeout: Maximum seconds to wait for selection

        Returns:
            Selected user ID, or "unknown" if timeout/error
        """
        input_name, output_name = self._find_piano_ports()

        if not input_name or not output_name:
            logger.error("Piano not found")
            return "unknown"

        try:
            self.input_port = mido.open_input(input_name)
            self.output_port = mido.open_output(output_name)

            # Display instructions
            print("\n" + "=" * 60)
            print("WHO'S PRACTICING?")
            print("=" * 60)
            for note, user in self.users.items():
                note_name = self._note_name(note)
                print(f"  Press {note_name} for {user}")
            print("=" * 60)

            # Play prompt melody
            time.sleep(0.5)
            self._play_prompt_melody()

            # Wait for user to press a key
            start_time = time.time()

            while time.time() - start_time < timeout:
                for msg in self.input_port.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        if msg.note in self.users:
                            selected_user = self.users[msg.note]
                            print(f"\n✓ {selected_user} selected!\n")

                            # Play confirmation
                            self._play_confirmation(selected_user)

                            return selected_user

                time.sleep(0.01)

            print("\nNo selection made, defaulting to 'unknown'")
            return "unknown"

        except Exception as e:
            logger.error(f"Error during user selection: {e}")
            return "unknown"

        finally:
            if self.input_port:
                self.input_port.close()
            if self.output_port:
                self.output_port.close()

    @staticmethod
    def _note_name(note_number: int) -> str:
        """Convert MIDI note number to note name."""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_number // 12) - 1
        note = note_names[note_number % 12]
        return f"{note}{octave}"


def demo():
    """Demo the user selector."""
    # Define users and their selection keys
    # Middle C (60) = parent, D (62) = daughter
    users = {
        60: "parent",   # Middle C
        62: "daughter"  # D
    }

    selector = PianoUserSelector(users)
    selected = selector.select_user(timeout=30.0)
    print(f"Selected user: {selected}")


if __name__ == "__main__":
    demo()
