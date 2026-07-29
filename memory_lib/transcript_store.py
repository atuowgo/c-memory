"""SQLite 存储的会话总结游标：非阻塞并发认领 + 孤儿 session 补漏扫描，模式与 observation_store.py 一致。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from memory_lib.storage import MEMORY_DIR

DB_FILE = MEMORY_DIR / ".transcript_progress.sqlite3"

STALE_PROCESSING_SECONDS = 600


def _connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS session_progress ("
        "session_id TEXT PRIMARY KEY,"
        "transcript_path TEXT NOT NULL,"
        "last_processed_uuid TEXT,"
        "status TEXT NOT NULL DEFAULT 'idle',"
        "updated_at TEXT NOT NULL)"
    )
    return conn


def try_claim_session(
    session_id: str, transcript_path: str, stale_after_seconds: int = STALE_PROCESSING_SECONDS
) -> tuple[bool, str | None]:
    """尝试拿到该 session 的总结处理权，不阻塞等待。

    返回 (claimed, cursor)：
    - claimed=True：拿到处理权（新 session，或已有 session 处于 idle/stale-processing）。
      cursor 是"上次处理到的 last_processed_uuid"，新 session 或从未处理过时为 None，
      调用方应把 None 传给 parse_new_turns 表示"从头解析"。
    - claimed=False：另一次处理仍在进行且未超过 stale_after_seconds，cursor 恒为 None，
      调用方应直接跳过本次处理，不做任何事。

    （早期版本只返回 str | None，导致"新 session（合法拿到游标，只是游标本来就是
    None）"和"锁被占用（应该跳过）"这两种语义完全不同的场景在返回值上无法区分——
    调用方拿到 None 时不知道该继续处理还是该跳过。改成显式的 (claimed, cursor) 元组
    从根上消除这个歧义，不再需要调用方自己复刻一遍内部判断逻辑去猜。）
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT last_processed_uuid, status, updated_at FROM session_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if row is not None:
            last_processed_uuid, status, updated_at = row
            if status == "processing":
                age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds()
                if age_seconds < stale_after_seconds:
                    return False, None  # 有其他处理在跑且未超时，本次跳过
            conn.execute(
                "UPDATE session_progress SET status = 'processing', updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        else:
            last_processed_uuid = None
            conn.execute(
                "INSERT INTO session_progress (session_id, transcript_path, last_processed_uuid, status, updated_at) "
                "VALUES (?, ?, NULL, 'processing', ?)",
                (session_id, transcript_path, now),
            )
        conn.commit()
        return True, last_processed_uuid
    finally:
        conn.close()


def release_session(session_id: str, last_processed_uuid: str) -> None:
    """处理结束后释放：推进游标到 last_processed_uuid，status 改回 idle。"""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        conn.execute(
            "UPDATE session_progress SET status = 'idle', last_processed_uuid = ?, updated_at = ? "
            "WHERE session_id = ?",
            (last_processed_uuid, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def find_orphan_sessions(
    exclude_session_id: str, stale_after_seconds: int = STALE_PROCESSING_SECONDS
) -> list[dict]:
    """找出卡在 processing 超过 stale_after_seconds、且不是当前 session 的旧 session。

    这类 session 是"曾经在处理、但从未等到 release 就结束了的旧 session"（crash/kill
    等异常退出），供 SessionStart 时扫描后台补总结。
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT session_id, transcript_path, last_processed_uuid, status, updated_at "
            "FROM session_progress WHERE status = 'processing' AND session_id != ?",
            (exclude_session_id,),
        ).fetchall()
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    orphans = []
    for session_id, transcript_path, last_processed_uuid, status, updated_at in rows:
        age_seconds = (now - datetime.fromisoformat(updated_at)).total_seconds()
        if age_seconds >= stale_after_seconds:
            orphans.append(
                {
                    "session_id": session_id,
                    "transcript_path": transcript_path,
                    "last_processed_uuid": last_processed_uuid,
                    "status": status,
                    "updated_at": updated_at,
                }
            )
    return orphans
