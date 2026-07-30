"""SQLite 存储的观测记录：PostToolUse 高频追加、Stop 按 session_id 查询、按时间保留。

observations 不需要 git 追踪（纯行为信号，只供 extract.py 在会话内临时读取，没有
任何代码读取过之前 jsonl 版本归档出去的月度文件），用 SQLite 换掉原来的
jsonl + 手写轮转逻辑：追加/删除天然有事务保证，保留策略退化成一条按时间戳的
DELETE，不再需要"整档案 + 无时间戳记录兜底保留"那套复杂处理——这里 ts 由
observe.py 每次调用时写入，恒不为空，不存在无时间戳记录。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from memory_lib.storage import MEMORY_DIR

DB_FILE = MEMORY_DIR / ".observations.sqlite3"
RETENTION_DAYS = 30


STALE_PROCESSING_SECONDS = 600


def _connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS observations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id TEXT,"
        "ts TEXT NOT NULL,"
        "tool_name TEXT,"
        "tool_input_json TEXT NOT NULL,"
        "tool_response_summary TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_session ON observations(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_ts ON observations(ts)")
    try:
        conn.execute("ALTER TABLE observations ADD COLUMN tool_response_summary TEXT")
    except sqlite3.OperationalError:
        pass  # 列已存在（老库升级场景），CREATE TABLE IF NOT EXISTS 不会补列
    conn.execute(
        "CREATE TABLE IF NOT EXISTS session_progress ("
        "session_id TEXT PRIMARY KEY,"
        "last_processed_id INTEGER NOT NULL DEFAULT 0,"
        "status TEXT NOT NULL DEFAULT 'idle',"
        "updated_at TEXT NOT NULL)"
    )
    return conn


def append_observation(record: dict) -> None:
    """写入一条观测记录，顺带清理超过 RETENTION_DAYS 的旧记录。"""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO observations (session_id, ts, tool_name, tool_input_json, tool_response_summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                record.get("session_id"),
                record.get("ts") or datetime.now(timezone.utc).isoformat(),
                record.get("tool_name"),
                json.dumps(record.get("tool_input") or {}, ensure_ascii=False),
                record.get("tool_response_summary"),
            ),
        )
        cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
        conn.execute("DELETE FROM observations WHERE ts < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


def list_new_session_observations(session_id: str, after_id: int) -> list[dict]:
    """取该 session 里 id > after_id 的观测记录（增量），带上 id 供调用方推进游标。"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, session_id, ts, tool_name, tool_input_json, tool_response_summary FROM observations "
            "WHERE session_id = ? AND id > ? ORDER BY id",
            (session_id, after_id),
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row_id, row_session_id, ts, tool_name, tool_input_json, tool_response_summary in rows:
        try:
            tool_input = json.loads(tool_input_json)
        except json.JSONDecodeError:
            tool_input = {}
        results.append(
            {
                "id": row_id,
                "session_id": row_session_id,
                "ts": ts,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_response_summary": tool_response_summary,
            }
        )
    return results


def list_session_observations_in_range(session_id: str, ts_start: str, ts_end: str | None) -> list[dict]:
    """按时间区间取该 session 的观测记录，供 procedure mining 按用户轮次的时间区间挖掘工具调用序列，按 id ASC 保序返回。"""
    conn = _connect()
    try:
        if ts_end is not None:
            rows = conn.execute(
                "SELECT id, session_id, ts, tool_name, tool_input_json, tool_response_summary FROM observations "
                "WHERE session_id = ? AND ts >= ? AND ts < ? ORDER BY id ASC",
                (session_id, ts_start, ts_end),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, session_id, ts, tool_name, tool_input_json, tool_response_summary FROM observations "
                "WHERE session_id = ? AND ts >= ? ORDER BY id ASC",
                (session_id, ts_start),
            ).fetchall()
    finally:
        conn.close()

    results = []
    for row_id, row_session_id, ts, tool_name, tool_input_json, tool_response_summary in rows:
        try:
            tool_input = json.loads(tool_input_json)
        except json.JSONDecodeError:
            tool_input = {}
        results.append(
            {
                "id": row_id,
                "session_id": row_session_id,
                "ts": ts,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_response_summary": tool_response_summary,
            }
        )
    return results


def try_claim_session(session_id: str, stale_after_seconds: int = STALE_PROCESSING_SECONDS) -> int | None:
    """尝试拿到该 session 的增量处理权，不阻塞等待。

    返回值是"上次处理到的 last_processed_id"（调用方应该只处理 id 更大的记录）；
    拿不到锁（另一次处理仍在进行且未超过 stale_after_seconds）返回 None，调用方
    应直接跳过本次处理——宁可丢这一次触发，也不同步等待，反正沉淀下来的模式
    会反复触发，不差这一次。
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT last_processed_id, status, updated_at FROM session_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if row is not None:
            last_processed_id, status, updated_at = row
            if status == "processing":
                age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds()
                if age_seconds < stale_after_seconds:
                    return None  # 有其他处理在跑且未超时，本次跳过
            conn.execute(
                "UPDATE session_progress SET status = 'processing', updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        else:
            last_processed_id = 0
            conn.execute(
                "INSERT INTO session_progress (session_id, last_processed_id, status, updated_at) "
                "VALUES (?, 0, 'processing', ?)",
                (session_id, now),
            )
        conn.commit()
        return last_processed_id
    finally:
        conn.close()


def release_session(session_id: str, last_processed_id: int) -> None:
    """处理结束后释放：无论处理是否成功都推进游标+回到 idle（允许漏处理，不重试）。"""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        conn.execute(
            "UPDATE session_progress SET status = 'idle', last_processed_id = ?, updated_at = ? "
            "WHERE session_id = ?",
            (last_processed_id, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()
