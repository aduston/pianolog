import { useEffect, useState } from 'react';
import type { WeeklyStats } from '../lib/types';

type StatsScreenProps = {
  weeklyStats: WeeklyStats;
  loading: boolean;
  onManageUsers: () => void;
};

export function StatsScreen({ weeklyStats, loading, onManageUsers }: StatsScreenProps) {
  const [page, setPage] = useState(0);
  const [isLandscapeWide, setIsLandscapeWide] = useState(
    window.matchMedia('(min-width: 768px) and (orientation: landscape)').matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 768px) and (orientation: landscape)');
    const onChange = () => setIsLandscapeWide(mediaQuery.matches);
    onChange();
    mediaQuery.addEventListener('change', onChange);
    return () => mediaQuery.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    setPage(0);
  }, [weeklyStats]);

  if (loading) {
    return <section className="panel">Loading weekly stats...</section>;
  }

  const entries = Object.entries(weeklyStats);
  if (entries.length === 0) {
    return <section className="panel">No users configured.</section>;
  }

  const renderUserCard = (userName: string, days: (typeof entries)[number][1]) => {
    const totalMinutes = days.reduce((sum, day) => sum + day.minutes, 0);
    const metTargetDays = days.filter((day) => day.met_target).length;
    const avgMinutes = (totalMinutes / days.length).toFixed(1);
    return (
      <article className="panel" key={userName}>
        <h2>{userName}</h2>
        <p>
          Goal: {days[0]?.target_minutes ?? 15} min/day • {metTargetDays}/7 days on track
        </p>
        <div className="bars" aria-label={`${userName} weekly chart`}>
          {days.map((day) => {
            const height = day.minutes === 0 ? 4 : Math.max(8, (Math.min(100, day.percentage) / 100) * 140);
            const className = day.minutes === 0 ? 'bar empty' : day.met_target ? 'bar met-target' : 'bar partial';
            return (
              <div className="bar-wrap" key={day.date}>
                <div
                  className={className}
                  style={{ height: `${height}px` }}
                  title={`${day.day_name}: ${day.minutes} minutes`}
                >
                  <span className="bar-value">{day.minutes}m</span>
                </div>
                <span>{day.day_name}</span>
              </div>
            );
          })}
        </div>
        <p>{Math.round(totalMinutes)}m this week • {avgMinutes}m/day average</p>
      </article>
    );
  };

  if (!isLandscapeWide || entries.length <= 2) {
    return (
      <section>
        <div className="screen-actions">
          <button onClick={onManageUsers}>Manage Users</button>
        </div>
        <div className="stats-grid">{entries.map(([userName, days]) => renderUserCard(userName, days))}</div>
      </section>
    );
  }

  const pages = Math.ceil(entries.length / 2);
  const currentPage = Math.min(page, pages - 1);
  const pageEntries = entries.slice(currentPage * 2, currentPage * 2 + 2);

  return (
    <section>
      <div className="screen-actions">
        <button onClick={onManageUsers}>Manage Users</button>
      </div>
      <div className="stats-grid">{pageEntries.map(([userName, days]) => renderUserCard(userName, days))}</div>
      <div className="carousel-nav">
        <button disabled={currentPage === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
          ← Previous
        </button>
        <button disabled={currentPage >= pages - 1} onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}>
          Next →
        </button>
      </div>
    </section>
  );
}
