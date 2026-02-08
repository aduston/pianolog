import type { WeeklyStats } from '../lib/types';

type StatsScreenProps = {
  weeklyStats: WeeklyStats;
  loading: boolean;
};

export function StatsScreen({ weeklyStats, loading }: StatsScreenProps) {
  if (loading) {
    return <section className="panel">Loading weekly stats...</section>;
  }

  const entries = Object.entries(weeklyStats);
  if (entries.length === 0) {
    return <section className="panel">No users configured.</section>;
  }

  return (
    <section className="stats-grid">
      {entries.map(([userName, days]) => {
        const totalMinutes = days.reduce((sum, day) => sum + day.minutes, 0);
        const metTargetDays = days.filter((day) => day.met_target).length;
        return (
          <article className="panel" key={userName}>
            <h2>{userName}</h2>
            <p>
              {Math.round(totalMinutes)} min this week, {metTargetDays}/7 days on target
            </p>
            <div className="bars" aria-label={`${userName} weekly chart`}>
              {days.map((day) => (
                <div className="bar-wrap" key={day.date}>
                  <div
                    className="bar"
                    style={{ height: `${Math.max(8, day.percentage)}%` }}
                    title={`${day.day_name}: ${day.minutes} minutes`}
                  />
                  <span>{day.day_name}</span>
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </section>
  );
}
