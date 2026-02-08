import { useEffect } from 'react';
import { io, type Socket } from 'socket.io-client';
import { getBasePath } from '../lib/basePath';

type SocketCallbacks = {
  onSessionStarted?: () => void;
  onSessionEnded?: () => void;
  onSessionActivity?: () => void;
  onMidiStatusChanged?: () => void;
};

export function usePianologSocket(callbacks: SocketCallbacks): void {
  useEffect(() => {
    const basePath = getBasePath();
    const socket: Socket = io({
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
