import { useEffect } from 'react';
import { io } from 'socket.io-client';
import { getBasePath } from '../lib/basePath';
export function usePianologSocket(callbacks) {
    useEffect(() => {
        const basePath = getBasePath();
        const socket = io({
            path: `${basePath}/socket.io`
        });
        socket.on('session_started', () => {
            callbacks.onSessionStarted?.();
        });
        socket.on('session_ended', () => {
            callbacks.onSessionEnded?.();
        });
        socket.on('session_activity', () => {
            callbacks.onSessionActivity?.();
        });
        socket.on('midi_connected', () => {
            callbacks.onMidiStatusChanged?.();
        });
        socket.on('midi_disconnected', () => {
            callbacks.onMidiStatusChanged?.();
        });
        return () => {
            socket.removeAllListeners();
            socket.disconnect();
        };
    }, [callbacks]);
}
