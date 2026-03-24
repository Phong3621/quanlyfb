import sqlite3
import os

class Database:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        query = '''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT,
                name TEXT,
                cookie TEXT,
                email TEXT,
                encrypted_password TEXT,
                note TEXT,
                is_live INTEGER,
                last_checked TEXT,
                created_at TEXT,
                proxy_id INTEGER,
                session_file TEXT
            )
        '''
        self.execute_update(query)

    def execute_query(self, query, params=()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, query, params=()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

db = Database()