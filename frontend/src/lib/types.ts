export type SessionStatus = {
  active: boolean;
  user: string;
  start_time?: number;
  duration?: number;
  note_count?: number;
};

export type WeeklyStatDay = {
  date: string;
  day_name: string;
  minutes: number;
  target_minutes: number;
  percentage: number;
  met_target: boolean;
};

export type WeeklyStats = Record<string, WeeklyStatDay[]>;

export type MidiStatus = {
  connected: boolean;
  device: string | null;
  searching_for: string;
};

export type User = {
  id: number;
  note: number;
  name: string;
};
