import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addUser, deleteUser } from '../lib/api';
import type { User } from '../lib/types';

type UserManagementScreenProps = {
  users: User[];
  loading: boolean;
  onBack: () => void;
};

function midiNoteToName(noteNumber: number): string {
  const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const octave = Math.floor(noteNumber / 12) - 1;
  const note = noteNames[noteNumber % 12];
  return `${note}${octave}`;
}

export function UserManagementScreen({ users, loading, onBack }: UserManagementScreenProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [note, setNote] = useState('');

  const addUserMutation = useMutation({
    mutationFn: addUser,
    onSuccess: () => {
      setName('');
      setNote('');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-stats'] });
    }
  });

  const deleteUserMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-stats'] });
    }
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsedNote = Number.parseInt(note, 10);
    if (!name.trim() || Number.isNaN(parsedNote) || parsedNote < 0 || parsedNote > 127) {
      return;
    }
    addUserMutation.mutate({ name: name.trim(), trigger_note: parsedNote });
  };

  return (
    <section className="panel">
      <div className="user-mgmt-header">
        <h2>Manage Users</h2>
        <button onClick={onBack}>Back to Stats</button>
      </div>

      <h3>Current Users</h3>
      {loading ? (
        <p>Loading users...</p>
      ) : users.length === 0 ? (
        <p>No users configured.</p>
      ) : (
        <ul className="user-list">
          {users.map((user) => (
            <li className="user-item" key={user.id}>
              <div>
                <div className="user-name">{user.name}</div>
                <div className="user-note">
                  MIDI Note: {user.note} ({midiNoteToName(user.note)})
                </div>
              </div>
              <button
                onClick={() => {
                  if (window.confirm(`Delete user \"${user.name}\"? Practice data remains.`)) {
                    deleteUserMutation.mutate(user.id);
                  }
                }}
                disabled={deleteUserMutation.isPending}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}

      <h3>Add New User</h3>
      <form className="add-user-form" onSubmit={handleSubmit}>
        <label>
          Name
          <input
            type="text"
            className="kioskboard-input"
            data-kioskboard-type="keyboard"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            inputMode="text"
          />
        </label>
        <label>
          MIDI Note (0-127)
          <input
            type="number"
            className="kioskboard-input"
            data-kioskboard-type="numpad"
            min={0}
            max={127}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            required
            inputMode="numeric"
          />
        </label>
        <button type="submit" disabled={addUserMutation.isPending}>
          {addUserMutation.isPending ? 'Adding...' : 'Add User'}
        </button>
      </form>
    </section>
  );
}
