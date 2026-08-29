import os
import sqlite3
from pathlib import Path

class MemoryStore:
    def __init__(self):
        path = Path(os.getenv("BERON_DB_PATH", "data/beron.db"))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add(self, role, content):
        self.conn.execute(
            "INSERT INTO messages(role, content) VALUES (?, ?)",
            (role, content)
        )
        self.conn.commit()

    def recent(self, limit=12):
        rows = self.conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        rows.reverse()
        return [{"role": r, "content": c} for r, c in rows]
