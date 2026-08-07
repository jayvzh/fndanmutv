import copy
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from app import database
from app.danmu_generator import (
    DanmuAPI,
    StrmProcessor,
    SubtitleProcessor,
    danmu_generator as generator,
)
from app.models import AppConfig, ManualMatchRequest
from app.services import scan_service
from app.services.media_parser import parse_media

logger = logging.getLogger("danmutv.service")


class DanmuService:
    MIN_DANMU_COUNT = 100
    MAX_RETRY_TIMES = 10
    RETRY_BACKOFF_MINUTES = [5, 30, 60, 120, 240, 480]

    def __init__(self):
        self._config: dict = AppConfig.default_config()
        self._retry_tasks: dict[str, dict] = {}
        self._manual_matches: dict[str, dict] = {}
        self._manual_file_matches: dict[str, dict] = {}
        self._manual_match_misses: set = set()
        self._directory_records: dict[str, dict] = {}
        self._global_history: list[dict] = []

        self._retry_lock = threading.Lock()
        self._inflight_lock = threading.Lock()
        self._scrape_lock = threading.Lock()
        self._history_lock = threading.Lock()
        self._directory_lock = threading.Lock()
        self._manual_lock = threading.Lock()
        self._danmu_cache_lock = threading.Lock()

        self._inflight_files: set = set()
        self._scrape_aborted = False
        self._force_regenerate = False
        self._scrape_progress: dict[str, Any] = {
            "running": False,
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "current_file": None,
            "started_at": None,
            "duration": 0,
        }
        self._danmu_count_cache: dict[str, tuple] = {}

        self._scheduler = None
        self._load_all()

    # ---------- lifecycle ----------
    def set_scheduler(self, scheduler) -> None:
        self._scheduler = scheduler

    def _load_all(self) -> None:
        db_cfg = database.load_config_json()
        self._config = self._merge_config(db_cfg or {})
        self._apply_runtime_config(self._config)

        self._retry_tasks = self._load_retry_tasks_from_db()
        stored_manual = database.load_manual_matches()
        self._manual_matches = stored_manual.get("directory", {})
        self._manual_file_matches = stored_manual.get("file", {})
        self._directory_records = database.load_directory_records()
        self._global_history = database.load_global_history()
        self._validate_and_clean_records()

    def _apply_runtime_config(self, cfg: dict) -> None:
        api_url = cfg.get("danmu_api_url") or "http://danmu-api:9321"
        try:
            DanmuAPI.set_api_url(api_url)
        except Exception as e:
            logger.warning(f"设置 DanmuAPI 地址失败: {e}")

    def reload(self) -> None:
        db_cfg = database.load_config_json()
        self._config = self._merge_config(db_cfg or {})
        self._apply_runtime_config(self._config)

    def _merge_config(self, db_cfg: dict) -> dict:
        merged = {**AppConfig.default_config(), **(db_cfg or {})}
        for key in self.DEPRECATED_KEYS:
            merged.pop(key, None)
        return merged

    # ---------- helpers ----------
    @staticmethod
    def _normalize_path(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        return os.path.normpath(path)

    def _is_supported_file(self, file_path: str) -> bool:
        return scan_service.is_supported_file(file_path, self._config.get("enable_strm", True))

    def _configured_paths(self) -> list[str]:
        path_cfg = self._config.get("path") or ""
        return [p.strip() for p in path_cfg.split("\n") if p.strip()]

    # ---------- config ----------
    def get_config(self) -> dict:
        return dict(self._config)

    # 已废弃的 MoviePilot 时代配置键，加载/保存时剔除
    DEPRECATED_KEYS = ("enabled",)

    def save_config(self, cfg: dict) -> None:
        if not isinstance(cfg, dict):
            raise ValueError("config 必须是 dict")
        merged = {**AppConfig.default_config(), **self._config, **cfg}
        for key in self.DEPRECATED_KEYS:
            merged.pop(key, None)
        # 类型修正
        try:
            merged["multi_layer_count"] = int(merged.get("multi_layer_count", 2))
        except (TypeError, ValueError):
            merged["multi_layer_count"] = 2
        try:
            merged["width_scale"] = float(merged.get("width_scale", 1.0))
        except (TypeError, ValueError):
            merged["width_scale"] = 1.0
        try:
            merged["alpha"] = float(merged.get("alpha", 0.7))
        except (TypeError, ValueError):
            merged["alpha"] = 0.7

        self._config = merged
        # 兼容旧配置：enabled 已废弃（工具默认启用），仅用于把旧的 auto_scrape=true 迁移
        database.save_config_json(merged)
        self._apply_runtime_config(merged)
        if self._scheduler is not None:
            try:
                self._scheduler.reschedule(merged)
            except Exception as e:
                logger.warning(f"重调度失败: {e}")
        logger.info(
            f"配置已保存，auto_scrape={merged.get('auto_scrape')} "
            f"mode={merged.get('auto_scrape_mode')}"
        )

    # ---------- danmu count ----------
    def count_danmu_lines_cached(self, ass_file: str,
                                 stat_result: Optional[os.stat_result] = None) -> int:
        try:
            st = stat_result or os.stat(ass_file)
        except OSError:
            return 0
        with self._danmu_cache_lock:
            cached = self._danmu_count_cache.get(ass_file)
            if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
                return cached[2]
        count = self._count_danmu_lines(ass_file)
        with self._danmu_cache_lock:
            self._danmu_count_cache[ass_file] = (st.st_mtime_ns, st.st_size, count)
        return count

    @staticmethod
    def _count_danmu_lines(ass_file: str) -> int:
        try:
            if not os.path.exists(ass_file):
                return 0
            count = 0
            with open(ass_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Dialogue:"):
                        count += 1
            return count
        except Exception as e:
            logger.error(f"统计弹幕数量失败: {e}")
            return 0

    # ---------- manual match ----------
    @staticmethod
    def _normalize_manual_entry(data: Any, scope: str) -> Optional[dict]:
        if not isinstance(data, dict):
            return None
        anime_id = data.get("animeId") or data.get("anime_id")
        if anime_id is None:
            return None
        try:
            anime_id = int(anime_id)
        except (TypeError, ValueError):
            return None
        payload = dict(data)
        payload["animeId"] = anime_id
        payload.pop("anime_id", None)
        payload["scope"] = scope
        offset = payload.get("episodeOffset")
        if offset is not None:
            try:
                payload["episodeOffset"] = int(offset)
            except (TypeError, ValueError):
                payload.pop("episodeOffset", None)
        payload.setdefault("updatedAt", datetime.now().isoformat(timespec="seconds"))
        return payload

    @staticmethod
    def _manual_json_path(directory: str) -> str:
        return os.path.join(directory, DanmuAPI.MANUAL_MATCH_FILE)

    def _write_manual_match_file(self, directory: str, data: dict) -> None:
        if not directory:
            return
        try:
            DanmuAPI._write_manual_mapping(directory, data)
        except AttributeError:
            os.makedirs(directory, exist_ok=True)
            payload = self._normalize_manual_entry(data, "directory")
            if not payload:
                return
            with open(self._manual_json_path(directory), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    def get_manual_match(self, directory: str, check_legacy: bool = True) -> Optional[dict]:
        if not directory:
            return None
        norm = self._normalize_path(directory)
        with self._manual_lock:
            cached = self._manual_matches.get(norm)
            if cached:
                return copy.deepcopy(cached)
            if norm in self._manual_match_misses:
                return None
        if not os.path.isdir(directory):
            return None
        manual_path = self._manual_json_path(directory)
        if os.path.exists(manual_path):
            try:
                with open(manual_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                payload = self._normalize_manual_entry(data, "directory")
                if payload:
                    with self._manual_lock:
                        self._manual_matches[norm] = payload
                        self._manual_match_misses.discard(norm)
                    database.upsert_manual_match("directory", norm, payload)
                    return copy.deepcopy(payload)
            except Exception as e:
                logger.warning(f"读取手动匹配文件失败: {e}")
        if check_legacy:
            legacy = self._convert_legacy_id_file(directory)
            if legacy:
                with self._manual_lock:
                    self._manual_matches[norm] = legacy
                database.upsert_manual_match("directory", norm, legacy)
                return copy.deepcopy(legacy)
        with self._manual_lock:
            self._manual_match_misses.add(norm)
        return None

    def get_manual_file_match(self, file_path: str) -> Optional[dict]:
        norm = self._normalize_path(file_path)
        if not norm:
            return None
        with self._manual_lock:
            cached = self._manual_file_matches.get(norm)
            if cached:
                return copy.deepcopy(cached)
        # 文件级匹配也可能由同目录下的 .dandan.anime.json 的 scope=file 记录提供
        # 但原实现仅使用内存缓存，保持一致
        return None

    def _convert_legacy_id_file(self, directory: str) -> Optional[dict]:
        try:
            for entry in os.listdir(directory):
                if not entry.endswith(".id"):
                    continue
                legacy_path = os.path.join(directory, entry)
                try:
                    anime_id = int(os.path.splitext(entry)[0])
                except (TypeError, ValueError):
                    continue
                match_info = {
                    "animeId": anime_id,
                    "source": "legacy-id-file",
                    "updatedAt": datetime.now().isoformat(timespec="seconds"),
                }
                self._write_manual_match_file(directory, match_info)
                try:
                    os.remove(legacy_path)
                except OSError:
                    pass
                return match_info
        except OSError:
            return None
        return None

    def _persist_manual(self, scope: str, path: str, data: Optional[dict]) -> None:
        norm = self._normalize_path(path)
        if not norm:
            return
        with self._manual_lock:
            target = self._manual_file_matches if scope == "file" else self._manual_matches
            if data:
                target[norm] = data
            else:
                target.pop(norm, None)
            self._manual_match_misses.discard(norm)
        if data:
            database.upsert_manual_match(scope, norm, data)
        else:
            database.delete_manual_match(scope, norm)

    def set_manual_match(self, req: ManualMatchRequest) -> dict:
        file_path = req.file_path
        directory_path = req.directory
        scope = (req.scope or "").lower()
        if scope not in {"file", "directory"}:
            scope = "directory" if directory_path else "file"

        if scope == "file" and not file_path:
            raise ValueError("缺少文件路径")
        manual_dir = directory_path
        if scope == "directory":
            if not manual_dir and file_path:
                manual_dir = os.path.dirname(file_path)
            if not manual_dir or not os.path.isdir(manual_dir):
                raise ValueError("匹配目录不存在")

        anime = req.anime.model_dump(exclude_none=True) if req.anime else {}
        anime_id = anime.get("animeId") or anime.get("anime_id")
        if anime_id is None:
            raise ValueError("缺少 animeId")
        try:
            anime_id = int(anime_id)
        except (TypeError, ValueError):
            raise ValueError("animeId 格式无效")

        episode_offset = req.episodeOffset
        if episode_offset is None:
            episode_offset = 0
        try:
            episode_offset = int(episode_offset)
        except (TypeError, ValueError):
            raise ValueError("集数偏移必须为整数")

        manual_info = {
            "animeId": anime_id,
            "animeTitle": anime.get("animeTitle"),
            "imageUrl": anime.get("imageUrl"),
            "type": anime.get("type"),
            "typeDescription": anime.get("typeDescription"),
            "episodeCount": anime.get("episodeCount"),
            "rating": anime.get("rating"),
            "startDate": anime.get("startDate"),
            "source": "manual_file" if scope == "file" else "manual",
            "updatedAt": datetime.now().isoformat(timespec="seconds"),
            "scope": scope,
        }
        if episode_offset:
            manual_info["episodeOffset"] = episode_offset

        if scope == "file":
            self._persist_manual("file", file_path, manual_info)
            target_dir = os.path.dirname(file_path)
            logger.info(f"单文件手动匹配已保存: {file_path} -> {anime_id}")
        else:
            self._write_manual_match_file(manual_dir, manual_info)
            self._persist_manual("directory", manual_dir, manual_info)
            target_dir = manual_dir
            logger.info(f"目录手动匹配已保存: {manual_dir} -> {anime_id}")

        return {
            "directory": target_dir,
            "file_path": file_path if scope == "file" else None,
            "manual_match": manual_info,
        }

    def remove_manual_match(self, scope: Optional[str] = None,
                            file_path: Optional[str] = None,
                            directory: Optional[str] = None) -> dict:
        scope = (scope or "").lower()
        if scope not in {"file", "directory"}:
            scope = "file" if file_path and not directory else "directory"
        if scope == "file":
            if not file_path:
                raise ValueError("未提供有效文件路径")
            self._persist_manual("file", file_path, None)
            return {"file_path": file_path}
        manual_dir = directory
        if not manual_dir and file_path:
            manual_dir = os.path.dirname(file_path)
        if not manual_dir:
            raise ValueError("未提供有效目录")
        json_path = self._manual_json_path(manual_dir)
        try:
            if os.path.exists(json_path):
                os.remove(json_path)
        except OSError as e:
            logger.warning(f"删除手动匹配文件失败: {e}")
        self._persist_manual("directory", manual_dir, None)
        return {"directory": manual_dir}

    # ---------- directory records / history ----------
    def get_directory_record(self, directory: str) -> Optional[dict]:
        norm = self._normalize_path(directory)
        if not norm:
            return None
        with self._directory_lock:
            return copy.deepcopy(self._directory_records.get(norm))

    def update_directory_record(self, directory: str, data: dict) -> None:
        norm = self._normalize_path(directory)
        if not norm:
            return
        with self._directory_lock:
            record = self._directory_records.setdefault(
                norm,
                {
                    "scrape_status": {"total_files": 0, "scraped_files": 0},
                    "last_scrape_time": None,
                    "retry_info": {"enabled": False, "next_retry_time": None, "retry_count": 0},
                    "history": [],
                },
            )
            record.update(data)
            database.upsert_directory_record(norm, record)

    def _validate_and_clean_records(self) -> None:
        stale = []
        with self._directory_lock:
            for p in list(self._directory_records.keys()):
                if not os.path.exists(p):
                    stale.append(p)
            for p in stale:
                del self._directory_records[p]
        for p in stale:
            database.delete_directory_record(p)

    def _append_history(self, record: dict) -> None:
        record = dict(record)
        record["id"] = str(int(time.time() * 1000))
        record.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        max_summary = 100
        # 详情只在最近20条概要中保留
        with self._history_lock:
            self._global_history.insert(0, record)
            if len(self._global_history) > max_summary:
                self._global_history = self._global_history[:max_summary]
            # 落库：用新行+裁剪旧行方式，简单起见重写历史表
            database.clear_global_history()
            for item in self._global_history:
                database.insert_history_record(item)

    def get_history(self, page: int = 1, page_size: int = 20,
                    include_details: bool = False) -> dict:
        page = max(1, int(page or 1))
        page_size = max(1, min(100, int(page_size or 20)))
        start = (page - 1) * page_size
        end = start + page_size
        with self._history_lock:
            items = copy.deepcopy(self._global_history[start:end])
            total = len(self._global_history)
        if not include_details:
            for it in items:
                it.pop("details", None)
        return {
            "items": items,
            "history": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    def clear_history(self) -> None:
        with self._history_lock:
            self._global_history = []
        database.clear_global_history()

    # ---------- retry ----------
    @staticmethod
    def _serialize_task(task: dict) -> dict:
        last = task.get("last_attempt")
        next_rt = task.get("next_retry_time")
        return {
            "retry_count": task.get("retry_count", 1),
            "last_attempt": last.isoformat() if isinstance(last, datetime) else last,
            "file_path": task.get("file_path"),
            "last_danmu_count": task.get("last_danmu_count", 0),
            "error_type": task.get("error_type", "unknown"),
            "next_retry_time": next_rt.isoformat() if isinstance(next_rt, datetime) else next_rt,
        }

    def _load_retry_tasks_from_db(self) -> dict:
        stored = database.load_retry_tasks()
        parsed = {}
        for file_path, t in stored.items():
            try:
                last_attempt = t.get("last_attempt")
                last_dt = datetime.fromisoformat(last_attempt) if last_attempt else datetime.now()
                next_rt = t.get("next_retry_time")
                next_dt = datetime.fromisoformat(next_rt) if next_rt else self._calculate_next_retry_time(
                    t.get("retry_count", 1), t.get("error_type", "unknown")
                )
                parsed[file_path] = {
                    "retry_count": int(t.get("retry_count", 1)),
                    "last_attempt": last_dt,
                    "file_path": t.get("file_path", file_path),
                    "last_danmu_count": int(t.get("last_danmu_count", 0) or 0),
                    "error_type": t.get("error_type", "unknown"),
                    "next_retry_time": next_dt,
                }
            except (TypeError, ValueError) as e:
                logger.warning(f"跳过无效的重试任务 {file_path}: {e}")
        return parsed

    def _save_retry_tasks(self) -> None:
        with self._retry_lock:
            snapshot = {k: self._serialize_task(v) for k, v in self._retry_tasks.items()}
        for fp, t in snapshot.items():
            database.upsert_retry_task(fp, t)
        # 清理已删除的任务：简单做法——删库后重写
        # 为避免频繁全量删除，这里仅 upsert；删除在 remove/clear 时单独处理

    def _calculate_next_retry_time(self, retry_count: int, error_type: str = "unknown") -> datetime:
        intervals = self.RETRY_BACKOFF_MINUTES
        if retry_count <= len(intervals):
            minutes = intervals[retry_count - 1]
        else:
            minutes = intervals[-1]
        if error_type == "rate_limit":
            minutes = max(minutes, 30)
        return datetime.now() + timedelta(minutes=minutes)

    def _add_to_retry_if_needed(self, file_path: str, danmu_count: int,
                                error_type: str = "unknown") -> None:
        if not self._config.get("enable_retry_task", True):
            return
        norm = self._normalize_path(file_path) or file_path
        now = datetime.now()
        to_save = None
        to_delete = False
        with self._retry_lock:
            if norm in self._retry_tasks:
                task = self._retry_tasks[norm]
                task["retry_count"] += 1
                task["last_attempt"] = now
                task["error_type"] = error_type
                task["last_danmu_count"] = danmu_count
                if task["retry_count"] >= self.MAX_RETRY_TIMES:
                    logger.warning(
                        f"文件已达最大重试次数({self.MAX_RETRY_TIMES})，放弃: {file_path}"
                    )
                    del self._retry_tasks[norm]
                    to_delete = True
                else:
                    task["next_retry_time"] = self._calculate_next_retry_time(
                        task["retry_count"], error_type
                    )
                    to_save = (norm, task)
            else:
                if danmu_count < self.MIN_DANMU_COUNT:
                    task = {
                        "retry_count": 1,
                        "last_attempt": now,
                        "file_path": file_path,
                        "last_danmu_count": danmu_count,
                        "error_type": error_type,
                        "next_retry_time": self._calculate_next_retry_time(1, error_type),
                    }
                    self._retry_tasks[norm] = task
                    to_save = (norm, task)

        if to_delete:
            database.delete_retry_task(norm)
        elif to_save:
            fp, t = to_save
            database.upsert_retry_task(fp, self._serialize_task(t))

    def get_retry_tasks(self) -> dict:
        with self._retry_lock:
            display = {}
            for fp, t in self._retry_tasks.items():
                display[fp] = {
                    "retry_count": t["retry_count"],
                    "last_attempt": t["last_attempt"].strftime("%Y-%m-%d %H:%M:%S"),
                    "file_path": t["file_path"],
                    "last_danmu_count": t.get("last_danmu_count", 0),
                    "error_type": t.get("error_type", "unknown"),
                    "next_retry_time": t.get("next_retry_time", datetime.now()).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
        return {
            "tasks": display,
            "total": len(display),
            "min_danmu_count": self.MIN_DANMU_COUNT,
            "max_retry_times": self.MAX_RETRY_TIMES,
        }

    def process_retry_tasks(self) -> dict:
        if not self._retry_tasks:
            return {"processed": 0, "success": 0, "failed": 0, "removed": 0, "remaining": 0}
        processed = success = failed = removed = 0
        with self._retry_lock:
            items = list(self._retry_tasks.items())
        for file_path, t in items:
            if not os.path.exists(file_path):
                with self._retry_lock:
                    self._retry_tasks.pop(file_path, None)
                database.delete_retry_task(file_path)
                removed += 1
                continue
            if t["retry_count"] >= self.MAX_RETRY_TIMES:
                with self._retry_lock:
                    self._retry_tasks.pop(file_path, None)
                database.delete_retry_task(file_path)
                removed += 1
                continue
            nrt = t.get("next_retry_time")
            if nrt and datetime.now() < nrt:
                continue
            processed += 1
            try:
                result = self.generate_single(file_path)
                ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
                if result and os.path.exists(ass_file) and not (
                    isinstance(result, str) and result.startswith("弹幕数量为0")
                ):
                    count = self.count_danmu_lines_cached(ass_file)
                    if count >= self.MIN_DANMU_COUNT:
                        success += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"重试任务失败 {file_path}: {e}")
                failed += 1
        with self._retry_lock:
            remaining = len(self._retry_tasks)
        return {
            "processed": processed,
            "success": success,
            "failed": failed,
            "removed": removed,
            "remaining": remaining,
        }

    def clear_retry_tasks(self) -> int:
        with self._retry_lock:
            count = len(self._retry_tasks)
            self._retry_tasks = {}
        database.clear_retry_tasks()
        return count

    def remove_retry_task(self, file_path: str) -> bool:
        norm = self._normalize_path(file_path) or file_path
        with self._retry_lock:
            removed = self._retry_tasks.pop(norm, None) is not None
        if removed:
            database.delete_retry_task(norm)
        return removed

    # ---------- core generate ----------
    def generate_single(self, file_path: str) -> Optional[str]:
        if not file_path or not os.path.exists(file_path):
            return "文件不存在"
        if not self._is_supported_file(file_path):
            if file_path.lower().endswith(".strm") and not self._config.get("enable_strm", True):
                return ".strm 文件刮削未启用"
            return "不支持的文件格式"

        norm = self._normalize_path(file_path) or file_path
        with self._inflight_lock:
            if norm in self._inflight_files:
                return "文件正在刮削中，跳过重复请求"
            self._inflight_files.add(norm)
        try:
            return self._generate_danmu_impl(file_path)
        finally:
            with self._inflight_lock:
                self._inflight_files.discard(norm)

    def _generate_danmu_impl(self, file_path: str) -> Optional[str]:
        norm = self._normalize_path(file_path) or file_path
        parsed = parse_media(file_path)
        episode = parsed.episode
        tmdb_id_type = 1 if parsed.is_movie else 0

        # 文件级手动匹配
        manual_comment_id = None
        manual_file_match = self.get_manual_file_match(file_path)
        if manual_file_match:
            manual_episode = DanmuAPI._apply_episode_offset(
                episode, manual_file_match.get("episodeOffset")
            )
            manual_comment_id = DanmuAPI._compose_comment_id(
                manual_file_match.get("animeId"), manual_episode
            )

        try:
            ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
            force = getattr(self, "_force_regenerate", False)
            if os.path.exists(ass_file) and not force:
                count = self.count_danmu_lines_cached(ass_file)
                if count >= self.MIN_DANMU_COUNT:
                    logger.info(f"本地已有弹幕，跳过API: {ass_file} ({count}条)")
                    sub2 = SubtitleProcessor.find_subtitle_file(file_path)
                    if not sub2 and SubtitleProcessor.can_extract_subtitles(file_path):
                        SubtitleProcessor.try_extract_sub(file_path)
                        sub2 = SubtitleProcessor.find_subtitle_file(file_path)
                    if sub2:
                        SubtitleProcessor.combine_sub_ass(ass_file, sub2, file_path)
                    return ass_file
                logger.info(f"本地弹幕数量不足({count})，重新获取: {ass_file}")
            elif force and os.path.exists(ass_file):
                logger.info(f"全量扫描模式，强制重新获取弹幕: {ass_file}")

            result = generator(
                file_path,
                self._config.get("width", 1920),
                self._config.get("height", 1080),
                "Arial",
                self._config.get("fontsize", 48),
                self._config.get("alpha", 0.7),
                self._config.get("duration", 14),
                False,
                False,  # use_tmdb_id 固定 False
                None,   # tmdb_id
                episode,
                None,   # cache_ttl
                self._config.get("screen_area", "quarter"),
                manual_comment_id=manual_comment_id,
                tmdb_id_type=tmdb_id_type,
                enable_multi_layer=self._config.get("enable_multi_layer", False),
                random_top_bottom=self._config.get("random_top_bottom", False),
                top_ratio=self._config.get("top_ratio", 0),
                bottom_ratio=self._config.get("bottom_ratio", 0),
                density=self._config.get("density", 100),
                width_scale=self._config.get("width_scale", 1.0),
                multi_layer_count=self._config.get("multi_layer_count", 2),
            )

            ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
            if isinstance(result, str) and result.startswith("error:"):
                parts = result.split(":", 2)
                error_type = parts[1] if len(parts) >= 2 else "unknown"
                logger.warning(result)
                self._add_to_retry_if_needed(file_path, 0, error_type)
                return result[7:] if error_type == "rate_limit" else result

            if isinstance(result, str) and result.startswith("弹幕数量为0"):
                self._add_to_retry_if_needed(file_path, 0)
                return result

            if os.path.exists(ass_file):
                count = self.count_danmu_lines_cached(ass_file)
                if count < self.MIN_DANMU_COUNT:
                    self._add_to_retry_if_needed(file_path, count)
                else:
                    with self._retry_lock:
                        existed = self._retry_tasks.pop(norm, None)
                    if existed:
                        database.delete_retry_task(norm)
            else:
                self._add_to_retry_if_needed(file_path, 0)
            return result
        except Exception as e:
            logger.error(f"生成弹幕失败: {e}")
            self._add_to_retry_if_needed(file_path, 0)
            return f"生成弹幕失败: {e}"

    # ---------- batch scrape ----------
    def _collect_media_files(self, path: str) -> list[str]:
        collected = []
        if os.path.isfile(path):
            if self._is_supported_file(path):
                collected.append(path)
            return collected
        for root, _, files in os.walk(path):
            for name in files:
                full = os.path.join(root, name)
                if self._is_supported_file(full):
                    collected.append(full)
        return collected

    def _collect_files_shallowest(self, directory_path: str, max_depth: int = 6) -> list[str]:
        result: list[str] = []

        def _scan(d: str, depth: int):
            if depth > max_depth:
                return
            local_media = []
            subdirs = []
            try:
                for entry in os.scandir(d):
                    if entry.is_file() and self._is_supported_file(entry.path):
                        local_media.append(entry.path)
                    elif entry.is_dir() and not entry.name.startswith("."):
                        subdirs.append(entry.path)
            except OSError:
                return
            if local_media:
                result.extend(local_media)
            else:
                for sd in subdirs:
                    _scan(sd, depth + 1)

        _scan(directory_path, 0)
        return result

    def _has_valid_danmu(self, file_path: str) -> bool:
        ass = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
        if not os.path.exists(ass):
            return False
        return self.count_danmu_lines_cached(ass) >= self.MIN_DANMU_COUNT

    def _filter_unscraped(self, files: list[str]) -> tuple[list[str], int]:
        kept = []
        skipped = 0
        for f in files:
            if self._has_valid_danmu(f):
                skipped += 1
            else:
                kept.append(f)
        return kept, skipped

    def scrape_directory(self, directory_path: str, recursive: bool = False,
                         force: bool = False) -> dict:
        if not directory_path:
            raise ValueError("缺少目录路径")
        if not os.path.isdir(directory_path):
            raise ValueError("目录不存在")

        if recursive:
            files = self._collect_files_shallowest(directory_path, max_depth=6)
        else:
            files = []
            for name in os.listdir(directory_path):
                full = os.path.join(directory_path, name)
                if os.path.isfile(full) and self._is_supported_file(full):
                    files.append(full)
        if not files:
            raise ValueError("目录下没有支持的媒体文件")
        total_before = len(files)
        skipped = 0
        if not force:
            files, skipped = self._filter_unscraped(files)
            if not files:
                raise ValueError(f"所有 {total_before} 个文件已有有效弹幕，无需刮削")
        label = f"目录 {directory_path}" + ("（递归）" if recursive else "")
        if force:
            label += "（全量）"

        if not self._start_scrape_batch(files, label, force=force):
            raise ValueError("已有刮削任务进行中，请稍后再试")

        return {"total": len(files), "skipped": skipped, "force": force}

    def _start_scrape_batch(self, files: list[str], label: str, force: bool = False) -> bool:
        with self._scrape_lock:
            if self._scrape_progress.get("running"):
                return False
            self._scrape_progress = {
                "running": True,
                "total": len(files),
                "processed": 0,
                "success": 0,
                "failed": 0,
                "current_file": None,
                "started_at": time.time(),
                "duration": 0,
            }
            self._scrape_aborted = False
            self._force_regenerate = force
        t = threading.Thread(target=self._run_scrape_batch, args=(files, label), daemon=True)
        t.start()
        return True

    def _run_scrape_batch(self, files: list[str], label: str) -> None:
        logger.info(f"开始批量刮削（{label}），共 {len(files)} 个文件")
        details = []
        try:
            for fp in files:
                if self._scrape_aborted:
                    break
                with self._scrape_lock:
                    self._scrape_progress["current_file"] = os.path.basename(fp)
                ok = False
                count = 0
                try:
                    result = self.generate_single(fp)
                    ok = isinstance(result, str) and result.endswith(".danmu.chs.ass")
                    if ok and os.path.exists(result):
                        count = self.count_danmu_lines_cached(result)
                except Exception as e:
                    logger.error(f"刮削文件失败 {fp}: {e}")
                with self._scrape_lock:
                    self._scrape_progress["processed"] += 1
                    if ok:
                        self._scrape_progress["success"] += 1
                    else:
                        self._scrape_progress["failed"] += 1
                if self._config.get("enable_history_details"):
                    details.append({
                        "file": os.path.basename(fp),
                        "result": "success" if ok else "failed",
                        "danmu_count": count,
                    })
                time.sleep(0.5)
        finally:
            self._force_regenerate = False
            with self._scrape_lock:
                started = self._scrape_progress.get("started_at")
                if started:
                    self._scrape_progress["duration"] = int(time.time() - started)
                self._scrape_progress["running"] = False
                self._scrape_progress["current_file"] = None
                summary = dict(self._scrape_progress)
            aborted = self._scrape_aborted
            self._scrape_aborted = False

            record = {
                "type": "batch",
                "path": label,
                "processed": summary["total"],
                "success": summary["success"],
                "failed": summary["failed"],
                "duration": summary["duration"],
                "aborted": aborted,
            }
            if self._config.get("enable_history_details") and details:
                record["details"] = details
            self._append_history(record)

            if files:
                directory = (
                    os.path.dirname(files[0])
                    if len(files) == 1
                    else os.path.dirname(os.path.commonprefix(files))
                )
                if directory:
                    self.update_directory_record(
                        directory,
                        {
                            "scrape_status": {
                                "total_files": summary["total"],
                                "scraped_files": summary["success"],
                            },
                            "last_scrape_time": datetime.now().isoformat(timespec="seconds"),
                        },
                    )
            logger.info(
                f"批量刮削完成（{label}）：成功 {summary['success']}，失败 {summary['failed']}"
            )

    def abort_scrape(self) -> bool:
        with self._scrape_lock:
            if not self._scrape_progress.get("running"):
                return False
            self._scrape_aborted = True
        return True

    def get_status(self) -> dict:
        with self._scrape_lock:
            progress = dict(self._scrape_progress)
        if progress.get("running") and progress.get("started_at"):
            progress["duration"] = int(time.time() - progress["started_at"])
        progress.pop("started_at", None)
        return {"auto_scrape": self._config.get("auto_scrape", False), **progress}

    def get_full_status(self) -> dict:
        with self._scrape_lock:
            progress = dict(self._scrape_progress)
        if progress.get("running") and progress.get("started_at"):
            progress["duration"] = int(time.time() - progress["started_at"])
        progress.pop("started_at", None)

        stats = {
            "total_files": 0,
            "success_count": 0,
            "failed_count": 0,
            "retry_tasks_count": 0,
        }
        with self._directory_lock:
            for rec in self._directory_records.values():
                ss = rec.get("scrape_status", {})
                stats["total_files"] += ss.get("total_files", 0)
                stats["success_count"] += ss.get("scraped_files", 0)
        with self._history_lock:
            for rec in self._global_history:
                stats["failed_count"] += rec.get("failed", 0)
            last_run = self._global_history[0] if self._global_history else None

        with self._retry_lock:
            stats["retry_tasks_count"] = len(self._retry_tasks)
            next_retry_time = None
            for t in self._retry_tasks.values():
                nrt = t.get("next_retry_time")
                if nrt and (next_retry_time is None or nrt < next_retry_time):
                    next_retry_time = nrt

        api_status = self.check_api_status()
        media_paths = self._configured_paths()
        media_library_accessible = all(os.path.exists(p) for p in media_paths) if media_paths else False

        return {
            "auto_scrape": self._config.get("auto_scrape", False),
            "auto_scrape_mode": self._config.get("auto_scrape_mode", "incremental"),
            "api_connected": api_status.get("reachable", False),
            "api_message": api_status.get("message", ""),
            "media_library_accessible": media_library_accessible,
            "media_library_count": len(media_paths),
            "stats": stats,
            "next_retry_time": next_retry_time.strftime("%Y-%m-%d %H:%M:%S")
            if next_retry_time
            else None,
            "last_run": last_run,
            **progress,
        }

    # ---------- API/search ----------
    def check_api_status(self, api_url: Optional[str] = None) -> dict:
        target = (api_url or self._config.get("danmu_api_url") or "http://danmu-api:9321").rstrip("/")
        try:
            resp = requests.get(f"{target}/api/logs", headers=DanmuAPI.HEADERS, timeout=5)
            if resp.status_code == 200:
                return {"reachable": True, "message": f"API可访问 ({target})", "url": target}
            if resp.status_code == 401:
                return {
                    "reachable": True,
                    "message": "API返回401，需要在地址中配置Token",
                    "url": target,
                }
            return {
                "reachable": False,
                "message": f"API返回异常 HTTP {resp.status_code}",
                "url": target,
            }
        except Exception as e:
            return {"reachable": False, "message": f"API检测失败: {e}", "url": target}

    def search_danmu(self, keyword: Optional[str] = None, media_type: Optional[str] = None) -> dict:
        keyword = (keyword or "").strip()
        if not keyword:
            raise ValueError("搜索关键字不能为空")
        params = {"keyword": keyword}
        if media_type and media_type != "all":
            params["type"] = media_type
        resp = requests.get(
            f"{DanmuAPI.get_api_url()}/api/v2/search/anime",
            params=params,
            headers=DanmuAPI.HEADERS,
            timeout=(5, 15),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"搜索失败: HTTP {resp.status_code}")
        data = resp.json()
        if not data.get("success", False):
            raise RuntimeError(data.get("errorMessage") or "搜索失败")
        return data

    # ---------- auto scrape ----------
    def auto_scrape_configured_paths(self, mode: str = "incremental") -> dict:
        paths = self._configured_paths()
        if not paths:
            return {"started": False, "message": "未配置刮削路径"}
        force = mode == "full"
        total = 0
        started_any = False
        messages = []
        for p in paths:
            if not os.path.exists(p):
                messages.append(f"路径不存在: {p}")
                continue
            try:
                res = self.scrape_directory(p, recursive=True, force=force)
                total += res.get("total", 0)
                started_any = True
            except ValueError as e:
                messages.append(f"{p}: {e}")
        return {
            "started": started_any,
            "total": total,
            "mode": mode,
            "message": "; ".join(messages) if messages else f"已开始刮削 {total} 个文件",
        }

    def update_path(self, path: Optional[str] = None) -> dict:
        if path is not None:
            self._config["path"] = path
        else:
            self.reload()
        return {"path": self._config.get("path", "")}

    # ---------- scan delegation ----------
    def scan_path(self, path: Optional[str] = None, current_dir: Optional[str] = None):
        return scan_service.scan_path(
            self,
            path=path,
            current_dir=current_dir,
            configured_path=self._config.get("path", ""),
            min_danmu_count=self.MIN_DANMU_COUNT,
            enable_strm=self._config.get("enable_strm", True),
        )

    def scan_subfolder(self, subfolder_path: str):
        return scan_service.scan_subfolder(
            self,
            subfolder_path,
            configured_path=self._config.get("path", ""),
            min_danmu_count=self.MIN_DANMU_COUNT,
            enable_strm=self._config.get("enable_strm", True),
        )

    def scan_directory_stats(self, directory_path: str):
        return scan_service.scan_directory_stats(
            self,
            directory_path,
            min_danmu_count=self.MIN_DANMU_COUNT,
            enable_strm=self._config.get("enable_strm", True),
        )

    def scan_orphan_subtitles(self, path: Optional[str] = None):
        return scan_service.scan_orphan_subtitles(
            path=path, configured_path=self._config.get("path", "")
        )
