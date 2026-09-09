"""Persistence helpers for the ICD LangGraph workflow.

Short-term memory is handled by LangGraph's SQLite checkpointer.  This module
contains the application-level, long-term memory repository.  Long-term memory
stores only manually approved coding rules/aliases; raw medical records are not
written here.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_PHI_LABEL_PATTERN = re.compile(
    r"(病案标识(?:号)?|住院号|患者姓名|姓名[：:]|身份证|手机号|电话号码|家庭住址|床号[：:])"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_memory_directory() -> Path:
    configured = os.getenv("LANGGRAPH_MEMORY_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
    else:
        project_root = Path(__file__).resolve().parents[2]
        path = project_root / "data" / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


class LongTermMemoryRepository:
    """SQLite-backed repository for reviewed ICD coding knowledge.

    The repository deliberately does not expose a method that accepts an entire
    medical record.  Only short, approved rules and optional search keywords can
    be saved, which reduces the risk of patient data leaking across cases.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or (get_memory_directory() / "long_term_memory.sqlite3")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.database_path), check_same_thread=False, timeout=30
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS icd_coding_memories (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL DEFAULT 'manual_review',
                    approved INTEGER NOT NULL DEFAULT 1,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_icd_memory_tenant_active "
                "ON icd_coding_memories(tenant_id, active, updated_at)"
            )
            self._conn.commit()

    @staticmethod
    def _validate_text(content: str) -> str:
        normalized = " ".join(str(content).split()).strip()
        if not normalized:
            raise ValueError("记忆内容不能为空")
        if len(normalized) > 2000:
            raise ValueError("单条长期记忆不能超过 2000 个字符")
        if _PHI_LABEL_PATTERN.search(normalized):
            raise ValueError("长期记忆疑似包含患者标识信息，请先脱敏")
        return normalized

    @staticmethod
    def _normalize_keywords(keywords: list[str] | None) -> list[str]:
        result: list[str] = []
        for keyword in keywords or []:
            value = " ".join(str(keyword).split()).strip()
            if value and value not in result:
                result.append(value[:100])
        return result[:30]

    def add(
        self,
        *,
        tenant_id: str,
        content: str,
        keywords: list[str] | None = None,
        source: str = "manual_review",
        approved: bool = False,
    ) -> dict[str, Any]:
        if not approved:
            raise ValueError("长期记忆必须经过人工审核，approved 必须为 true")
        tenant = str(tenant_id or "default").strip()[:100] or "default"
        clean_content = self._validate_text(content)
        clean_keywords = self._normalize_keywords(keywords)
        memory_id = str(uuid.uuid4())
        now = utc_now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO icd_coding_memories
                    (id, tenant_id, content, keywords, source, approved, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    memory_id,
                    tenant,
                    clean_content,
                    json.dumps(clean_keywords, ensure_ascii=False),
                    str(source or "manual_review")[:100],
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return self.get(memory_id, tenant_id=tenant) or {}

    def get(self, memory_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM icd_coding_memories
                WHERE id = ? AND tenant_id = ?
                """,
                (memory_id, tenant_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, *, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM icd_coding_memories
                WHERE tenant_id IN (?, 'global') AND active = 1 AND approved = 1
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (tenant_id, safe_limit),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def search(self, *, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return keyword-matched rules without persisting ``query``."""

        query_lower = str(query).lower()
        candidates = self.list(tenant_id=tenant_id, limit=500)
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in candidates:
            keywords = item.get("keywords", [])
            if not keywords:
                # Keyword-free memories are institution-wide rules.
                score = 0.1
            else:
                score = sum(2.0 for keyword in keywords if keyword.lower() in query_lower)
                if score == 0:
                    continue
            scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], pair[1]["updated_at"]), reverse=True)
        return [item for _, item in scored[: max(1, min(int(limit), 20))]]

    def deactivate(self, memory_id: str, *, tenant_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE icd_coding_memories
                SET active = 0, updated_at = ?
                WHERE id = ? AND tenant_id = ?
                """,
                (utc_now(), memory_id, tenant_id),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close the repository connection (primarily for tests and shutdown)."""
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        try:
            data["keywords"] = json.loads(data.get("keywords") or "[]")
        except json.JSONDecodeError:
            data["keywords"] = []
        data["approved"] = bool(data.get("approved"))
        data["active"] = bool(data.get("active"))
        return data


_repository: LongTermMemoryRepository | None = None
_repository_lock = threading.Lock()


def get_long_term_memory_repository() -> LongTermMemoryRepository:
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = LongTermMemoryRepository()
    return _repository
