import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from app.config import settings
from app.models import AppConfig

logger = logging.getLogger("danmutv.database")

_write_lock = threading.Lock()
_init_lock = threading.Lock()
_initialized = False


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        settings.get_db_path(),
        check_same_thread=False,
        timeout=30.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_conn():
    """获取一个 SQLite 连接（调用方负责 commit/rollback）。"""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    global _initialized
    with _init_lock:
        if _initialized:
            return
        settings.ensure_data_dir()
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    config_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS retry_tasks (
                    file_path TEXT PRIMARY KEY,
                    retry_count INTEGER NOT NULL,
                    last_attempt TEXT,
                    last_danmu_count INTEGER DEFAULT 0,
                    error_type TEXT,
                    next_retry_time TEXT,
                    error_message TEXT DEFAULT ''
                )
                """
            )
            # 兼容旧库：补充 error_message 列
            try:
                cur.execute("ALTER TABLE retry_tasks ADD COLUMN error_message TEXT DEFAULT ''")
            except Exception:
                pass
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS manual_matches (
                    scope TEXT NOT NULL,
                    path TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (scope, path)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS directory_records (
                    path TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS global_history (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    type TEXT,
                    path TEXT,
                    processed INTEGER,
                    success INTEGER,
                    failed INTEGER,
                    duration REAL,
                    aborted INTEGER DEFAULT 0,
                    details_json TEXT
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_ts ON global_history(timestamp DESC)"
            )

            row = cur.execute("SELECT config_json FROM config WHERE id = 1").fetchone()
            if row is None:
                default_cfg = AppConfig.default_config()
                # 用环境变量注入的弹幕 API 地址覆盖代码默认值（Docker 部署）
                if settings.danmu_api_url:
                    default_cfg["danmu_api_url"] = settings.danmu_api_url
                cur.execute(
                    "INSERT INTO config (id, config_json) VALUES (1, ?)",
                    (json.dumps(default_cfg, ensure_ascii=False),),
                )
                logger.info("已写入默认配置")
        _initialized = True


def query_one(sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(sql, tuple(params)).fetchone()


def query_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(sql, tuple(params)).fetchall()


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    """串行化写入，避免 'database is locked'。"""
    with _write_lock:
        with get_conn() as conn:
            return conn.execute(sql, tuple(params))


def executemany(sql: str, seq_of_params: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
    with _write_lock:
        with get_conn() as conn:
            return conn.executemany(sql, [tuple(p) for p in seq_of_params])


# --- config ---
def load_config_json() -> dict:
    row = query_one("SELECT config_json FROM config WHERE id = 1")
    if row and row["config_json"]:
        try:
            return json.loads(row["config_json"])
        except (TypeError, ValueError):
            logger.warning("config_json 解析失败，使用默认配置")
    return AppConfig.default_config()


def save_config_json(cfg: dict) -> None:
    execute(
        "UPDATE config SET config_json = ? WHERE id = 1",
        (json.dumps(cfg, ensure_ascii=False),),
    )


# --- retry_tasks ---
def load_retry_tasks() -> dict:
    rows = query_all(
        "SELECT file_path, retry_count, last_attempt, last_danmu_count, error_type, next_retry_time, error_message FROM retry_tasks"
    )
    result = {}
    for r in rows:
        result[r["file_path"]] = {
            "retry_count": r["retry_count"],
            "last_attempt": r["last_attempt"],
            "file_path": r["file_path"],
            "last_danmu_count": r["last_danmu_count"] or 0,
            "error_type": r["error_type"] or "unknown",
            "next_retry_time": r["next_retry_time"],
            "error_message": r["error_message"] if "error_message" in r.keys() else "",
        }
    return result


def upsert_retry_task(file_path: str, task: dict) -> None:
    execute(
        """
        INSERT INTO retry_tasks (file_path, retry_count, last_attempt, last_danmu_count, error_type, next_retry_time, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            retry_count=excluded.retry_count,
            last_attempt=excluded.last_attempt,
            last_danmu_count=excluded.last_danmu_count,
            error_type=excluded.error_type,
            next_retry_time=excluded.next_retry_time,
            error_message=excluded.error_message
        """,
        (
            file_path,
            task.get("retry_count", 1),
            task.get("last_attempt"),
            task.get("last_danmu_count", 0),
            task.get("error_type", "unknown"),
            task.get("next_retry_time"),
            task.get("error_message", ""),
        ),
    )


def delete_retry_task(file_path: str) -> None:
    execute("DELETE FROM retry_tasks WHERE file_path = ?", (file_path,))


def clear_retry_tasks() -> None:
    execute("DELETE FROM retry_tasks")


# --- manual_matches ---
def load_manual_matches() -> dict:
    rows = query_all("SELECT scope, path, data_json FROM manual_matches")
    by_scope: dict[str, dict] = {}
    for r in rows:
        scope = r["scope"]
        try:
            data = json.loads(r["data_json"])
        except (TypeError, ValueError):
            continue
        by_scope.setdefault(scope, {})[r["path"]] = data
    return by_scope


def upsert_manual_match(scope: str, path: str, data: dict) -> None:
    execute(
        """
        INSERT INTO manual_matches (scope, path, data_json)
        VALUES (?, ?, ?)
        ON CONFLICT(scope, path) DO UPDATE SET data_json=excluded.data_json
        """,
        (scope, path, json.dumps(data, ensure_ascii=False)),
    )


def delete_manual_match(scope: str, path: str) -> None:
    execute("DELETE FROM manual_matches WHERE scope = ? AND path = ?", (scope, path))


# --- directory_records ---
def load_directory_records() -> dict:
    rows = query_all("SELECT path, data_json FROM directory_records")
    result = {}
    for r in rows:
        try:
            result[r["path"]] = json.loads(r["data_json"])
        except (TypeError, ValueError):
            continue
    return result


def upsert_directory_record(path: str, data: dict) -> None:
    execute(
        """
        INSERT INTO directory_records (path, data_json) VALUES (?, ?)
        ON CONFLICT(path) DO UPDATE SET data_json=excluded.data_json
        """,
        (path, json.dumps(data, ensure_ascii=False)),
    )


def delete_directory_record(path: str) -> None:
    execute("DELETE FROM directory_records WHERE path = ?", (path,))


# --- global_history ---
def load_global_history() -> list:
    rows = query_all(
        "SELECT id, timestamp, type, path, processed, success, failed, duration, aborted, details_json FROM global_history ORDER BY timestamp DESC LIMIT 100"
    )
    result = []
    for r in rows:
        item = {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "type": r["type"],
            "path": r["path"],
            "processed": r["processed"],
            "success": r["success"],
            "failed": r["failed"],
            "duration": r["duration"],
            "aborted": bool(r["aborted"]),
        }
        if r["details_json"]:
            try:
                item["details"] = json.loads(r["details_json"])
            except (TypeError, ValueError):
                pass
        result.append(item)
    return result


def insert_history_record(record: dict) -> None:
    execute(
        """
        INSERT INTO global_history
            (id, timestamp, type, path, processed, success, failed, duration, aborted, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(record.get("id")),
            record.get("timestamp"),
            record.get("type"),
            record.get("path"),
            record.get("processed"),
            record.get("success"),
            record.get("failed"),
            record.get("duration"),
            1 if record.get("aborted") else 0,
            json.dumps(record.get("details"), ensure_ascii=False)
            if record.get("details") is not None
            else None,
        ),
    )


def clear_global_history() -> None:
    execute("DELETE FROM global_history")
