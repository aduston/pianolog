"""
Database module for storing practice sessions.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class PracticeDatabase:
    """Manages SQLite database for practice session tracking."""

    def __init__(self, db_path: str = "practice_sessions.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self):
        """Initialize database connection and create tables if needed."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Create practice sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                start_timestamp INTEGER NOT NULL,
                end_timestamp INTEGER NOT NULL,
                duration_seconds INTEGER NOT NULL,
                note_count INTEGER NOT NULL,
                session_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create user targets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_targets (
                user_id TEXT PRIMARY KEY,
                daily_target_minutes INTEGER NOT NULL DEFAULT 15,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                trigger_note INTEGER NOT NULL UNIQUE,
                tombstoned INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for common queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_date
            ON practice_sessions(user_id, session_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_start_time
            ON practice_sessions(start_timestamp)
        ''')

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def save_session(self, user_id: str, start_time: float, end_time: float,
                     note_count: int) -> int:
        """
        Save a practice session to the database.

        Args:
            user_id: Identifier for the user (e.g., "parent", "daughter")
            start_time: Unix timestamp of session start
            end_time: Unix timestamp of session end
            note_count: Number of notes played during session

        Returns:
            Session ID of the inserted record
        """
        duration_seconds = int(end_time - start_time)
        session_date = datetime.fromtimestamp(start_time).date()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO practice_sessions
            (user_id, start_timestamp, end_timestamp, duration_seconds,
             note_count, session_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, int(start_time), int(end_time), duration_seconds,
              note_count, session_date))

        self.conn.commit()
        session_id = cursor.lastrowid

        logger.info(f"Saved session {session_id}: {user_id}, "
                   f"{duration_seconds}s, {note_count} notes")

        return session_id

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get recent practice sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM practice_sessions
            ORDER BY start_timestamp DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_daily_summary(self, user_id: Optional[str] = None,
                          days: int = 7) -> List[Dict]:
        """
        Get daily practice summary for the past N days.

        Args:
            user_id: Filter by user (None for all users)
            days: Number of days to include

        Returns:
            List of daily summary dictionaries
        """
        cursor = self.conn.cursor()

        if user_id:
            query = '''
                SELECT
                    session_date,
                    user_id,
                    COUNT(*) as session_count,
                    SUM(duration_seconds) as total_seconds,
                    SUM(note_count) as total_notes
                FROM practice_sessions
                WHERE user_id = ?
                  AND session_date >= date('now', '-' || ? || ' days')
                GROUP BY session_date, user_id
                ORDER BY session_date DESC
            '''
            cursor.execute(query, (user_id, days))
        else:
            query = '''
                SELECT
                    session_date,
                    user_id,
                    COUNT(*) as session_count,
                    SUM(duration_seconds) as total_seconds,
                    SUM(note_count) as total_notes
                FROM practice_sessions
                WHERE session_date >= date('now', '-' || ? || ' days')
                GROUP BY session_date, user_id
                ORDER BY session_date DESC, user_id
            '''
            cursor.execute(query, (days,))

        return [dict(row) for row in cursor.fetchall()]

    def get_user_target(self, user_id: str) -> int:
        """
        Get daily practice target for a user in minutes.

        Args:
            user_id: User identifier

        Returns:
            Target in minutes (defaults to 15 if not set)
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT daily_target_minutes FROM user_targets
            WHERE user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        return result['daily_target_minutes'] if result else 15

    def set_user_target(self, user_id: str, target_minutes: int):
        """
        Set daily practice target for a user.

        Args:
            user_id: User identifier
            target_minutes: Target in minutes
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO user_targets (user_id, daily_target_minutes)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                daily_target_minutes = ?,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, target_minutes, target_minutes))

        self.conn.commit()
        logger.info(f"Set target for {user_id}: {target_minutes} minutes")

    def get_weekly_stats(self, user_id: str) -> List[Dict]:
        """
        Get weekly practice stats for a user with target information.

        Args:
            user_id: User identifier

        Returns:
            List of daily stats for the last 7 days including target
        """
        from datetime import datetime, timedelta

        # Get the target for this user
        target_minutes = self.get_user_target(user_id)

        # Get actual practice data for last 7 days
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                session_date,
                SUM(duration_seconds) as total_seconds
            FROM practice_sessions
            WHERE user_id = ?
              AND session_date >= date('now', '-6 days')
            GROUP BY session_date
            ORDER BY session_date ASC
        ''', (user_id,))

        practice_by_date = {row['session_date']: row['total_seconds'] for row in cursor.fetchall()}

        # Build complete 7-day array (including days with no practice)
        stats = []
        today = datetime.now().date()

        for i in range(6, -1, -1):  # 6 days ago to today
            date = today - timedelta(days=i)
            date_str = date.isoformat()

            total_seconds = practice_by_date.get(date_str, 0)
            total_minutes = total_seconds / 60.0

            stats.append({
                'date': date_str,
                'day_name': date.strftime('%a'),  # Mon, Tue, etc.
                'minutes': round(total_minutes, 1),
                'target_minutes': target_minutes,
                'percentage': min(100, round(100 * total_minutes / target_minutes)) if target_minutes > 0 else 0,
                'met_target': total_minutes >= target_minutes
            })

        return stats

    def get_users(self, include_tombstoned: bool = False) -> List[Dict]:
        """
        Get all users from the database.

        Args:
            include_tombstoned: Whether to include tombstoned users

        Returns:
            List of user dictionaries
        """
        cursor = self.conn.cursor()
        if include_tombstoned:
            cursor.execute('''
                SELECT id, name, trigger_note, tombstoned, created_at, updated_at
                FROM users
                ORDER BY name
            ''')
        else:
            cursor.execute('''
                SELECT id, name, trigger_note, tombstoned, created_at, updated_at
                FROM users
                WHERE tombstoned = 0
                ORDER BY name
            ''')

        return [dict(row) for row in cursor.fetchall()]

    def add_user(self, name: str, trigger_note: int) -> int:
        """
        Add a new user to the database.

        Args:
            name: User's name
            trigger_note: MIDI note number that activates this user

        Returns:
            User ID of the inserted record

        Raises:
            sqlite3.IntegrityError: If name or trigger_note already exists
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, trigger_note)
            VALUES (?, ?)
        ''', (name, trigger_note))

        self.conn.commit()
        user_id = cursor.lastrowid

        logger.info(f"Added user {user_id}: {name}, trigger_note={trigger_note}")
        return user_id

    def delete_user(self, user_id: int):
        """
        Tombstone a user (soft delete).

        Args:
            user_id: ID of the user to tombstone
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users
            SET tombstoned = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))

        self.conn.commit()
        logger.info(f"Tombstoned user {user_id}")

    def get_user_by_note(self, trigger_note: int) -> Optional[Dict]:
        """
        Get a user by their trigger note.

        Args:
            trigger_note: MIDI note number

        Returns:
            User dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, trigger_note, tombstoned, created_at, updated_at
            FROM users
            WHERE trigger_note = ? AND tombstoned = 0
        ''', (trigger_note,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def migrate_users_from_config(self, users_dict: Dict[int, str]):
        """
        Migrate users from config.USERS dict to database.
        Only adds users that don't already exist.

        Args:
            users_dict: Dictionary mapping trigger_note to name
        """
        for trigger_note, name in users_dict.items():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id FROM users WHERE name = ? OR trigger_note = ?
            ''', (name, trigger_note))

            if not cursor.fetchone():
                self.add_user(name, trigger_note)
                logger.info(f"Migrated user from config: {name} (note {trigger_note})")
            else:
                logger.info(f"User {name} already exists in database, skipping migration")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
