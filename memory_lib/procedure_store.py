"""procedure（多步骤操作流程）的 frontmatter 文件读写，以及独立的 episode 处理游标，模式分别与 storage.py / transcript_store.py 一致。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from memory_lib.storage import MEMORY_DIR

PROCEDURES_DIR = MEMORY_DIR / "procedures"

DB_FILE = MEMORY_DIR / ".procedure_progress.sqlite3"

STALE_PROCESSING_SECONDS = 600


def _procedure_path(procedure_id: str) -> Path:
    return PROCEDURES_DIR / f"{procedure_id}.md"


def read_procedure(procedure_id: str) -> dict | None:
    path = _procedure_path(procedure_id)
    if not path.exists():
        return None
    post = frontmatter.load(path)
    data = dict(post.metadata)
    data.setdefault("id", procedure_id)
    data["body"] = post.content
    return data


def write_procedure(procedure_id: str, frontmatter_dict: dict, body: str) -> None:
    PROCEDURES_DIR.mkdir(parents=True, exist_ok=True)
    metadata = dict(frontmatter_dict)
    metadata.setdefault("id", procedure_id)
    post = frontmatter.Post(body, **metadata)
    with open(_procedure_path(procedure_id), "w", encoding="utf-8") as f:
        frontmatter.dump(post, f)


def list_procedures() -> list[dict]:
    PROCEDURES_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for path in sorted(PROCEDURES_DIR.glob("*.md")):
        post = frontmatter.load(path)
        data = dict(post.metadata)
        data.setdefault("id", path.stem)
        data["body"] = post.content
        results.append(data)
    return results


def _connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS procedure_progress ("
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
    """尝试拿到该 session 的 procedure 挖掘处理权，不阻塞等待。

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
            "SELECT last_processed_uuid, status, updated_at FROM procedure_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if row is not None:
            last_processed_uuid, status, updated_at = row
            if status == "processing":
                age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds()
                if age_seconds < stale_after_seconds:
                    return False, None  # 有其他处理在跑且未超时，本次跳过
            conn.execute(
                "UPDATE procedure_progress SET status = 'processing', updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        else:
            last_processed_uuid = None
            conn.execute(
                "INSERT INTO procedure_progress (session_id, transcript_path, last_processed_uuid, status, updated_at) "
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
            "UPDATE procedure_progress SET status = 'idle', last_processed_uuid = ?, updated_at = ? "
            "WHERE session_id = ?",
            (last_processed_uuid, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_pending_skill_prompts() -> list[dict]:
    """已晋升（status == "promoted"）但还没问过用户是否转成 skill 的 procedure 列表。"""
    return [
        proc
        for proc in list_procedures()
        if proc.get("status") == "promoted" and proc.get("skill_asked") is not True
    ]


def mark_skill_asked(procedure_id: str) -> None:
    """把 skill_asked 标记为 True 写回；procedure 不存在时静默返回。"""
    proc = read_procedure(procedure_id)
    if proc is None:
        return
    frontmatter_dict = dict(proc)
    body = frontmatter_dict.pop("body", None) or ""
    frontmatter_dict.pop("id", None)
    frontmatter_dict["skill_asked"] = True
    write_procedure(procedure_id, frontmatter_dict, body)
