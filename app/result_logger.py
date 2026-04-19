from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class ResultLogger:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inspection_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    recipe_name TEXT NOT NULL,
                    final_result INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def log_result(self, result_payload: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO inspection_results(ts, recipe_name, final_result, payload) VALUES (?, ?, ?, ?)",
                (
                    result_payload["timestamp"],
                    result_payload["recipe_name"],
                    1 if result_payload["final_result"] else 0,
                    str(result_payload),
                ),
            )

    def get_latest(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT ts, recipe_name, final_result, payload FROM inspection_results ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [
                {
                    "timestamp": row[0],
                    "recipe_name": row[1],
                    "final_result": bool(row[2]),
                    "payload": row[3],
                }
                for row in cursor.fetchall()
            ]
