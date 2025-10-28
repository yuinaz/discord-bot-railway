# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class LoreEntry:
    category: str
    content: str
    timestamp: float
    importance: int = 1
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "tags": self.tags or []
        }

class LeinaLoreDB:
    def __init__(self, db_path: str = "data/leina/lore.sqlite3"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lore (
                    id INTEGER PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    importance INTEGER DEFAULT 1,
                    tags TEXT,
                    UNIQUE(category, content)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON lore(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON lore(importance)")

    async def add_lore(self, entry: LoreEntry) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO lore (category, content, timestamp, importance, tags) VALUES (?, ?, ?, ?, ?)",
                    (entry.category, entry.content, entry.timestamp, entry.importance, json.dumps(entry.tags or []))
                )
            return True
        except Exception as e:
            log.error(f"Error adding lore: {e}")
            return False

    async def get_lore(self, category: str, limit: int = 5) -> List[LoreEntry]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT category, content, timestamp, importance, tags FROM lore WHERE category = ? ORDER BY importance DESC, timestamp DESC LIMIT ?",
                    (category, limit)
                )
                return [
                    LoreEntry(
                        category=row[0],
                        content=row[1],
                        timestamp=row[2],
                        importance=row[3],
                        tags=json.loads(row[4]) if row[4] else []
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            log.error(f"Error getting lore: {e}")
            return []

    CATEGORIES = [
        "master_interactions",    # Interaksi dengan Master
        "community_moments",      # Momen-momen special dengan komunitas
        "character_growth",       # Perkembangan karakter Leina
        "stream_memories",        # Kenangan dari stream
        "learned_behaviors",      # Perilaku yang dipelajari
    ]