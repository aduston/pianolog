import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { endSession, getMidiStatus, getStatus, getWeeklyStats, reconnectMidi } from './lib/api';
import { PracticeScreen } from './components/PracticeScreen';
import { StatsScreen } from './components/StatsScreen';
import { usePianologSocket } from './hooks/usePianologSocket';

export function App() {
  const queryClient = useQueryClient();
  const [wsConnected, setWsConnected] = useState(false);

  const statusQuery = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
    refetchInterval: 1_000
  });

  const weeklyStatsQuery = useQuery({
    queryKey: ['weekly-stats'],
    queryFn: getWeeklyStats,
    refetchInterval: 5 * 60_000
  });

  const midiStatusQuery = useQuery({
    queryKey: ['midi-status'],
    queryFn: getMidiStatus,
    refetchInterval: 10_000
  });

  usePianologSocket(
    useMemo(
      () => ({
        onConnect: () => {
          setWsConnected(true);
        },
        onDisconnect: () => {
          setWsConnected(false);
        },
        onSessionStarted: () => {
          queryClient.invalidateQueries({ queryKey: ['status'] });
          queryClient.invalidateQueries({ queryKey: ['weekly-stats'] });
        },
        onSessionEnded: () => {
          queryClient.invalidateQueries({ queryKey: ['status'] });
          queryClient.invalidateQueries({ queryKey: ['weekly-stats'] });
        },
        onSessionActivity: () => {
          queryClient.invalidateQueries({ queryKey: ['status'] });
        },
        onMidiStatusChanged: () => {
          queryClient.invalidateQueries({ queryKey: ['midi-status'] });
        }
      }),
      [queryClient]
    )
  );

  const endSessionMutation = useMutation({
    mutationFn: endSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-stats'] });
    }
  });

  const reconnectMidiMutation = useMutation({
    mutationFn: reconnectMidi,
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['midi-status'] });
    }
  });

  const session = statusQuery.data;

  return (
    <main className="app-shell">
      <div className={`connection-status ${wsConnected ? 'connected' : 'disconnected'}`}>
        {wsConnected ? 'WebSocket Connected' : 'Disconnected'}
      </div>

      <header className="header">
        <h1>🎹 Pianolog</h1>
        <p>Piano Practice Tracker</p>
      </header>

      <section className={`midi-widget ${midiStatusQuery.data?.connected ? 'connected' : 'disconnected'}`}>
        <div className="midi-title">
          {midiStatusQuery.data?.connected ? 'USB Piano Connected' : 'USB is disconnected'}
        </div>
        <div className="midi-subtitle">
          {midiStatusQuery.data?.connected
            ? midiStatusQuery.data.device ?? 'Connected'
            : 'Waiting for piano...'}
        </div>
        {!midiStatusQuery.data?.connected ? (
          <div className="midi-actions">
            <button
              onClick={() => reconnectMidiMutation.mutate()}
              disabled={reconnectMidiMutation.isPending}
            >
              {reconnectMidiMutation.isPending ? 'Power cycling USB...' : 'Retry Connection'}
            </button>
          </div>
        ) : null}
      </section>

      {statusQuery.isLoading ? (
        <section className="panel">Loading current session...</section>
      ) : statusQuery.isError ? (
        <section className="panel">Failed to load current session status.</section>
      ) : session?.active ? (
        <PracticeScreen
          session={session}
          onEndSession={() => endSessionMutation.mutate()}
          ending={endSessionMutation.isPending}
        />
      ) : (
        <StatsScreen
          weeklyStats={weeklyStatsQuery.data ?? {}}
          loading={weeklyStatsQuery.isLoading}
        />
      )}
    </main>
  );
}
