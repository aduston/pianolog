import { apiUrl } from './basePath';
async function fetchJson(path, init) {
    const response = await fetch(apiUrl(path), init);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
}
export function getStatus() {
    return fetchJson('/api/status');
}
export function getWeeklyStats() {
    return fetchJson('/api/stats/weekly');
}
export function getMidiStatus() {
    return fetchJson('/api/midi/status');
}
export function endSession() {
    return fetchJson('/api/session/end', { method: 'POST' });
}
