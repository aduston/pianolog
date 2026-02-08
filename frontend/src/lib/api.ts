import { apiUrl } from './basePath';
import type { MidiStatus, SessionStatus, User, WeeklyStats } from './types';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function getStatus(): Promise<SessionStatus> {
  return fetchJson('/api/status');
}

export function getWeeklyStats(): Promise<WeeklyStats> {
  return fetchJson('/api/stats/weekly');
}

export function getMidiStatus(): Promise<MidiStatus> {
  return fetchJson('/api/midi/status');
}

export function endSession(): Promise<{ success: boolean; message: string }> {
  return fetchJson('/api/session/end', { method: 'POST' });
}

export function reconnectMidi(): Promise<{ success: boolean; connected: boolean; device: string | null }> {
  return fetchJson('/api/midi/reconnect', { method: 'POST' });
}

export function getUsers(): Promise<User[]> {
  return fetchJson('/api/users');
}

export function addUser(payload: { name: string; trigger_note: number }): Promise<{ success: boolean }> {
  return fetchJson('/api/users/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export function deleteUser(userId: number): Promise<{ success: boolean }> {
  return fetchJson(`/api/users/${userId}`, { method: 'DELETE' });
}
