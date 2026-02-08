import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { endSession, getMidiStatus, getStatus, getWeeklyStats } from './lib/api';
import { PracticeScreen } from './components/PracticeScreen';
import { StatsScreen } from './components/StatsScreen';
import { usePianologSocket } from './hooks/usePianologSocket';

export function App() {
  const queryClient = useQueryClient();

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

  const session = statusQuery.data;

  return (
    <main className="app-shell">
      <header className="header">
        <h1>Pianolog (React Pilot)</h1>
        <p>
          MIDI:{' '}
          {midiStatusQuery.data?.connected
            ? `Connected (${midiStatusQuery.data.device ?? 'Unknown device'})`
            : 'Disconnected'}
        </p>
      </header>

      {statusQuery.isLoading ? (
        <section className="panel">Loading current session...</section>
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
