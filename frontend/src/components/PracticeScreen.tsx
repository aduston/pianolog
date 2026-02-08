import type { SessionStatus } from '../lib/types';

type PracticeScreenProps = {
  session: SessionStatus;
  onEndSession: () => void;
  ending: boolean;
};

export function PracticeScreen({ session, onEndSession, ending }: PracticeScreenProps) {
  const duration = session.duration ?? 0;
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60)
    .toString()
    .padStart(2, '0');

  return (
    <section className="panel">
      <h2>{session.user} is practicing</h2>
      <p>Duration: {minutes}:{seconds}</p>
      <p>Notes: {session.note_count ?? 0}</p>
      <button onClick={onEndSession} disabled={ending}>
        {ending ? 'Ending...' : 'End Session'}
      </button>
    </section>
  );
}
