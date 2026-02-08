import { apiUrl } from './basePath';
import type { MidiStatus, SessionStatus, WeeklyStats } from './types';

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
