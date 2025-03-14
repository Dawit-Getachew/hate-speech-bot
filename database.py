# database.py
import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name="hate_speech.db"):
        # Use check_same_thread=False for simplicity in multi‑threaded environments
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                violation_count INTEGER DEFAULT 0,
                last_violation_date TEXT
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                admin_id TEXT,
                group_id TEXT,
                username TEXT,
                PRIMARY KEY (admin_id, group_id)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS message_stats (
                group_id TEXT PRIMARY KEY,
                total_messages INTEGER DEFAULT 0,
                hate_speech_messages INTEGER DEFAULT 0
            )
        """
        )
        self.conn.commit()

    def add_violation(self, user_id, username):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT violation_count FROM users WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        now = datetime.now().isoformat()
        if row:
            count = row[0] + 1
            cursor.execute(
                "UPDATE users SET violation_count = ?, last_violation_date = ? WHERE user_id = ?",
                (count, now, user_id),
            )
        else:
            count = 1
            cursor.execute(
                "INSERT INTO users (user_id, username, violation_count, last_violation_date) VALUES (?, ?, ?, ?)",
                (user_id, username, count, now),
            )
        self.conn.commit()
        return count

    def get_violation_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT violation_count FROM users WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_group_admins(self, group_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT DISTINCT admin_id FROM admins WHERE group_id = ?", (group_id,)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Database error getting admins: {e}")
            return []

    def add_admin(self, admin_id, group_id, username):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO admins (admin_id, group_id, username) 
                VALUES (?, ?, ?)
                """,
                (admin_id, group_id, username),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Database error adding admin: {e}")
            self.conn.rollback()
            return False

    def remove_admin(self, admin_id, group_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM admins WHERE admin_id = ? AND group_id = ?",
            (admin_id, group_id),
        )
        self.conn.commit()

    def increment_message_stats(self, group_id, is_hate_speech=False):
        try:
            cursor = self.conn.cursor()
            # First, ensure the group exists in stats
            cursor.execute(
                """
                INSERT OR IGNORE INTO message_stats (group_id, total_messages, hate_speech_messages)
                VALUES (?, 0, 0)
            """,
                (group_id,),
            )

            # Then update the counters
            cursor.execute(
                """
                UPDATE message_stats 
                SET total_messages = total_messages + 1,
                    hate_speech_messages = hate_speech_messages + ?
                WHERE group_id = ?
            """,
                (1 if is_hate_speech else 0, group_id),
            )

            self.conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing message stats: {e}")
            self.conn.rollback()

    def get_stats(self, group_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT total_messages, hate_speech_messages 
                FROM message_stats 
                WHERE group_id = ?
            """,
                (group_id,),
            )
            row = cursor.fetchone()
            return row if row else (0, 0)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return (0, 0)
