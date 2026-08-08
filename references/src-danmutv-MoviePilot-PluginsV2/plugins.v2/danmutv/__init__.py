# MoviePilot library
from app.log import logger
from app.plugins import _PluginBase
from app.core.event import eventmanager
from app.schemas.types import EventType
from app.utils.system import SystemUtils
from app.chain.media import MediaChain
from app.core.metainfo import MetaInfo
from app.core.config import settings
from app import schemas
from app.schemas.types import MediaType, EventType, SystemConfigKey
from datetime import datetime, timedelta

from typing import Any, List, Dict, Tuple, Optional
import subprocess
import os
import threading
import time
import json
import copy
import requests
from app.plugins.danmutv import danmu_generator as generator
   

class DanmuTV(_PluginBase):
    # 插件名称
    plugin_name = "弹幕刮削(影视版)"
    # 插件描述
    plugin_desc = "使用弹幕API后端生成影视弹幕字幕文件，支持电视剧、电影、动漫等多种媒体类型。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/jayvzh/MoviePilot-PluginsV2/main/icons/danmu.png"
    # 主题色
    plugin_color = "#3B5E8E"
    # 插件版本
    plugin_version = "1.7"
    # 插件作者
    plugin_author = "jayvzh"
    # 作者主页
    author_url = "https://github.com/jayvzh"
    # 插件配置项ID前缀
    plugin_config_prefix = "danmutv_"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _width = 1920
    _height = 1080
    _fontsize = 48
    _alpha = 0.7
    _duration = 14
    _path = ''
    _max_threads = 2
    _useTmdbID = True
    _auto_scrape = True
    _screen_area = 'quarter'
    _enable_strm = True
    _danmu_api_url = "http://localhost:9321"
    _DEFAULT_DANMU_API_URL = "http://localhost:9321"
    _min_danmu_count = 100
    _max_retry_times = 10
    _enable_retry_task = True
    _enable_history_details = False
    _enable_multi_layer = False
    _multi_layer_count = 2
    _random_top_bottom = False
    _top_ratio = 0
    _bottom_ratio = 0
    _density = 100
    _width_scale = 1.0
    
    # 重试任务列表 - 存储格式: {file_path: {"retry_count": int, "last_attempt": datetime, "file_path": str}}
    _retry_tasks = {}
    # 重试任务并发保护；批量刮削期间将逐文件的配置保存合并为最后一次
    _retry_lock = threading.Lock()
    _retry_save_deferred = False
    _retry_save_pending = False
    # 正在刮削中的文件集合，防止同一文件被并发刮削写坏弹幕文件
    _inflight_lock = threading.Lock()
    _inflight_files: set = set()
    # 批量刮削进度状态（含全局定时刮削与目录刮削）
    _scrape_lock = threading.Lock()
    _scrape_aborted = False
    _scrape_progress: Dict[str, Any] = {
        "running": False,
        "total": 0,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "current_file": None,
        "started_at": None,
        "duration": 0
    }
    _manual_matches: Dict[str, Dict[str, Any]] = {}
    _manual_file_matches: Dict[str, Dict[str, Any]] = {}
    # Negative cache: directories confirmed to have no manual match (avoids repeated disk checks while browsing)
    _manual_match_misses: set = set()
    # Danmu line-count cache: {ass_path: (mtime_ns, size, count)} — skip re-reading unchanged files
    _danmu_count_cache: Dict[str, Tuple[int, int, int]] = {}
    _manual_match_storage_key = "manual_matches"
    
    # 统一目录记录模型存储键
    _directory_records_key = "danmutv_directory_records"
    _global_history_key = "danmutv_global_history"

    # 弹幕参数预设存储键
    _danmu_presets_key = "danmu_presets"
    # 默认预设方案
    _DEFAULT_DANMU_PRESET = {
        "默认方案": {
            "fontsize": 48,
            "screen_area": "quarter",
            "alpha": 0.6,
            "duration": 14,
            "enable_multi_layer": True,
            "multi_layer_count": 2,
            "random_top_bottom": False,
            "top_ratio": 0,
            "bottom_ratio": 0,
            "density": 50,
            "width_scale": 1.2
        }
    }
    _danmu_presets: Dict[str, Dict[str, Any]] = {}
    
    # 目录记录缓存
    _directory_records: Dict[str, Dict[str, Any]] = {}
    # 全局历史记录缓存
    _global_history: List[Dict[str, Any]] = []

    media_chain = MediaChain()

    @property
    def _manual_match_filename(self) -> str:
        return generator.DanmuAPI.MANUAL_MATCH_FILE

    def _normalize_path(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        return os.path.normpath(path)

    def _manual_json_path(self, directory: str) -> str:
        return os.path.join(directory, self._manual_match_filename)

    def _save_manual_state(self):
        try:
            payload = {
                "directories": self._manual_matches,
                "files": self._manual_file_matches
            }
            self.save_data(self._manual_match_storage_key, payload)
        except Exception as e:
            logger.warning(f"保存手动匹配状态失败: {e}")

    def _load_manual_matches(self):
        stored = self.get_data(self._manual_match_storage_key)
        if not isinstance(stored, dict):
            stored = {}

        # 兼容旧版本仅存储目录映射的结构
        if "directories" in stored or "files" in stored:
            dir_data = stored.get("directories", {})
            file_data = stored.get("files", {})
        else:
            dir_data = stored
            file_data = {}

        self._manual_matches = {}
        self._manual_file_matches = {}
        self._manual_match_misses = set()

        for raw_path, info in dir_data.items():
            norm = self._normalize_path(raw_path)
            if not norm:
                continue
            payload = self._normalize_manual_entry(info, scope="directory")
            if payload:
                self._manual_matches[norm] = payload

        for raw_path, info in file_data.items():
            norm = self._normalize_path(raw_path)
            if not norm:
                continue
            payload = self._normalize_manual_entry(info, scope="file")
            if payload:
                self._manual_file_matches[norm] = payload

    def _load_danmu_presets(self):
        """加载弹幕参数预设，首次加载时写入默认方案"""
        stored = self.get_data(self._danmu_presets_key)
        if isinstance(stored, dict) and len(stored) > 0:
            self._danmu_presets = stored
        else:
            self._danmu_presets = dict(self._DEFAULT_DANMU_PRESET)
            self._save_danmu_presets()

    def _save_danmu_presets(self):
        """保存弹幕参数预设"""
        try:
            self.save_data(self._danmu_presets_key, self._danmu_presets)
        except Exception as e:
            logger.error(f"保存弹幕参数预设失败: {e}")

    def _get_danmu_presets(self) -> schemas.Response:
        """获取所有弹幕参数预设"""
        return schemas.Response(success=True, data=self._danmu_presets)

    def _save_danmu_preset(self, data: Dict[str, Any]) -> schemas.Response:
        """保存弹幕参数预设"""
        try:
            name = (data.get("name") or "").strip()
            if not name:
                return schemas.Response(success=False, message="方案名称不能为空")
            params = data.get("params", {})
            self._danmu_presets[name] = params
            self._save_danmu_presets()
            return schemas.Response(success=True, message=f"方案 '{name}' 已保存", data=self._danmu_presets)
        except Exception as e:
            logger.error(f"保存弹幕参数预设失败: {e}")
            return schemas.Response(success=False, message=f"保存失败: {str(e)}")

    def _delete_danmu_preset(self, data: Dict[str, Any]) -> schemas.Response:
        """删除弹幕参数预设"""
        try:
            name = (data.get("name") or "").strip()
            if not name:
                return schemas.Response(success=False, message="方案名称不能为空")
            if name not in self._danmu_presets:
                return schemas.Response(success=False, message=f"方案 '{name}' 不存在")
            del self._danmu_presets[name]
            self._save_danmu_presets()
            return schemas.Response(success=True, message=f"方案 '{name}' 已删除", data=self._danmu_presets)
        except Exception as e:
            logger.error(f"删除弹幕参数预设失败: {e}")
            return schemas.Response(success=False, message=f"删除失败: {str(e)}")

    def _load_directory_records(self):
        stored = self.get_data(self._directory_records_key)
        if isinstance(stored, dict):
            self._directory_records = stored
        else:
            self._directory_records = {}
        
        stored_history = self.get_data(self._global_history_key)
        if isinstance(stored_history, list):
            self._global_history = stored_history
        else:
            self._global_history = []

    def _save_directory_records(self):
        try:
            self.save_data(self._directory_records_key, self._directory_records)
            self.save_data(self._global_history_key, self._global_history)
            logger.debug("目录记录和历史记录已保存")
        except Exception as e:
            logger.error(f"保存目录记录失败: {e}")

    def _update_directory_record(self, directory: str, data: Dict[str, Any]):
        norm = self._normalize_path(directory)
        if not norm:
            return
        if norm not in self._directory_records:
            self._directory_records[norm] = {
                "scrape_status": {"total_files": 0, "scraped_files": 0},
                "last_scrape_time": None,
                "retry_info": {"enabled": False, "next_retry_time": None, "retry_count": 0},
                "history": []
            }
        self._directory_records[norm].update(data)
        self._save_directory_records()

    def _get_directory_record(self, directory: str) -> Optional[Dict[str, Any]]:
        norm = self._normalize_path(directory)
        if not norm:
            return None
        return self._directory_records.get(norm)

    def _remove_directory_record(self, directory: str):
        norm = self._normalize_path(directory)
        if norm in self._directory_records:
            del self._directory_records[norm]
            self._save_directory_records()

    def _validate_and_clean_records(self):
        stale_paths = []
        for path in list(self._directory_records.keys()):
            if not os.path.exists(path):
                stale_paths.append(path)
        for path in stale_paths:
            logger.info(f"清理过期的目录记录: {path}")
            del self._directory_records[path]
        if stale_paths:
            self._save_directory_records()

    def _add_history_record(self, record: Dict[str, Any]):
        record["id"] = int(time.time() * 1000)
        record["timestamp"] = datetime.now().isoformat(timespec="seconds")
        
        max_summary = 100
        max_details = 20
        
        self._global_history.insert(0, record)
        
        if len(self._global_history) > max_summary:
            self._global_history = self._global_history[:max_summary]
        
        self._save_directory_records()

    @staticmethod
    def _normalize_manual_entry(data: Any, scope: str) -> Optional[Dict[str, Any]]:
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
    def _clone_manual_match(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        return copy.deepcopy(data)

    def _convert_legacy_id_file(self, directory: str) -> Optional[Dict[str, Any]]:
        try:
            for entry in os.listdir(directory):
                if not entry.endswith('.id'):
                    continue
                legacy_path = os.path.join(directory, entry)
                try:
                    anime_id = int(os.path.splitext(entry)[0])
                except (TypeError, ValueError):
                    logger.warning(f"忽略无法解析的ID文件: {legacy_path}")
                    continue
                match_info = {
                    "animeId": int(anime_id),
                    "source": "legacy-id-file",
                    "updatedAt": datetime.now().isoformat(timespec="seconds")
                }
                self._write_manual_match_file(directory, match_info)
                try:
                    os.remove(legacy_path)
                    logger.info(f"已转换旧的ID文件并删除: {legacy_path}")
                except Exception as e:
                    logger.warning(f"删除旧ID文件失败: {e}")
                return match_info
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"转换旧ID文件失败: {e}")
        return None

    def _write_manual_match_file(self, directory: str, data: Dict[str, Any]):
        if not directory:
            return
        try:
            generator.DanmuAPI._write_manual_mapping(directory, data)
        except AttributeError:
            # 回退写入逻辑
            try:
                os.makedirs(directory, exist_ok=True)
                anime_id = data.get("animeId") or data.get("anime_id")
                if anime_id is None:
                    return
                payload = dict(data)
                payload["animeId"] = int(anime_id)
                payload.pop("anime_id", None)
                payload["scope"] = "directory"
                payload.setdefault("updatedAt", datetime.now().isoformat(timespec="seconds"))
                with open(self._manual_json_path(directory), 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"写入手动匹配文件失败: {e}")

    def _update_manual_match_cache(self, directory: str, data: Optional[Dict[str, Any]]):
        norm = self._normalize_path(directory)
        if not norm:
            return
        if data:
            payload = self._normalize_manual_entry(data, scope="directory")
            if not payload:
                return
            self._manual_matches[norm] = payload
        else:
            self._manual_matches.pop(norm, None)
        self._manual_match_misses.discard(norm)
        self._save_manual_state()

    def _update_manual_file_match_cache(self, file_path: str, data: Optional[Dict[str, Any]]):
        norm = self._normalize_path(file_path)
        if not norm:
            return
        if data:
            payload = self._normalize_manual_entry(data, scope="file")
            if not payload:
                return
            self._manual_file_matches[norm] = payload
        else:
            self._manual_file_matches.pop(norm, None)
        self._save_manual_state()

    def _get_manual_match(self, directory: str, check_legacy: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取目录的手动匹配信息
        :param directory: 目录路径
        :param check_legacy: 是否检查旧版.id文件（需要列目录，浏览场景应关闭）
        """
        if not directory:
            return None
        norm = self._normalize_path(directory)
        cached = self._manual_matches.get(norm)
        if cached:
            return self._clone_manual_match(cached)
        if norm in self._manual_match_misses:
            return None
        if not os.path.isdir(directory):
            return None

        manual_path = self._manual_json_path(directory)
        if os.path.exists(manual_path):
            try:
                with open(manual_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._update_manual_match_cache(directory, data)
                return self._clone_manual_match(self._manual_matches.get(norm))
            except Exception as e:
                logger.warning(f"读取手动匹配文件失败: {e}")

        if check_legacy:
            legacy = self._convert_legacy_id_file(directory)
            if legacy:
                self._update_manual_match_cache(directory, legacy)
                return self._clone_manual_match(self._manual_matches.get(norm))

        self._manual_match_misses.add(norm)
        return None

    def _get_manual_file_match(self, file_path: str) -> Optional[Dict[str, Any]]:
        norm = self._normalize_path(file_path)
        if not norm:
            return None
        cached = self._manual_file_matches.get(norm)
        if cached:
            return self._clone_manual_match(cached)
        return None

    def _resolve_manual_directory(self, file_path: Optional[str] = None, directory_path: Optional[str] = None) -> Optional[str]:
        if directory_path:
            return self._normalize_path(directory_path)
        if file_path:
            return self._normalize_path(os.path.dirname(file_path))
        return None
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持处理"""
        if file_path.endswith(('.mp4', '.mkv')):
            return True
        elif file_path.endswith('.strm'):
            return self._enable_strm
        return False
    
    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            self._width = config.get("width", 1920)
            self._height = config.get("height", 1080)
            self._fontsize = config.get("fontsize", 50)
            self._alpha = config.get("alpha", 0.9)
            self._duration = config.get("duration", 15)
            self._path = config.get("path", "")
            self._useTmdbID = config.get("useTmdbID", True)
            self._auto_scrape = config.get("auto_scrape", False)
            self._enable_retry_task = config.get("enable_retry_task", True)
            self._enable_history_details = config.get("enable_history_details", False)
            self._screen_area = config.get("screen_area", "full")
            self._enable_strm = config.get("enable_strm", True)
            self._danmu_api_url = config.get("danmu_api_url", self._DEFAULT_DANMU_API_URL)
            self._enable_multi_layer = config.get("enable_multi_layer", False)
            self._multi_layer_count = int(config.get("multi_layer_count", 2))
            self._random_top_bottom = config.get("random_top_bottom", False)
            self._top_ratio = config.get("top_ratio", 0)
            self._bottom_ratio = config.get("bottom_ratio", 0)
            self._density = config.get("density", 100)
            self._width_scale = float(config.get("width_scale", 1.0))
            generator.DanmuAPI.set_api_url(self._danmu_api_url)
            # 从独立存储加载重试任务（不再放在插件配置中，避免被标准保存流程覆盖）
            self._load_retry_tasks()
        # 加载手动匹配缓存
        self._load_manual_matches()
        # 加载弹幕参数预设
        self._load_danmu_presets()
        # 加载目录记录和历史记录
        self._load_directory_records()
        # 惰性验证清理过期记录
        self._validate_and_clean_records()
        if self._enabled:
            logger.info("弹幕加载插件已启用")

    def get_state(self) -> bool:
        return self._enabled
    
    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._enable_retry_task:
            return [{
                "id": "DanmuRetryTask",
                "name": "弹幕重试任务",
                "trigger": "cron",
                "func": self.auto_process_retry_tasks,
                "kwargs": {
                    "minute": "*/5",  # 每5分钟执行一次
                    "hour": "*",
                    "day": "*",
                    "month": "*",
                    "day_of_week": "*"
                }
            }]
        return []
        
    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        [{
            "path": "/xx",
            "endpoint": self.xxx,
            "methods": ["GET", "POST"],
            "summary": "API说明"
        }]
        """
        logger.info("获取插件API")
        return [{
            "path": "/generate_danmu_with_path",
            "endpoint": self.generate_danmu_global,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "刮削弹幕",
            "description": "根据设定的路径刮削弹幕" 
        },{
            "path": "/update_path",
            "endpoint": self.update_path,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "更新路径",
            "description": "更新刮削路径"
        },
        {
            "path": "/config",
            "endpoint": self._get_config,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取配置",
            "description": "获取插件配置"
        },
        {
            "path": "/config",
            "endpoint": self._save_config,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "保存配置",
            "description": "保存插件配置"
        },
        {
            "path": "/status",
            "endpoint": self._get_status,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取状态",
            "description": "获取当前刮削状态"
        },
        {
            "path": "/scan_path",
            "endpoint": self.scan_path,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "扫描路径",
            "description": "扫描路径下的媒体文件和弹幕信息，支持current_dir参数进行点击式导航"
        },
        {
            "path": "/scan_subfolder",
            "endpoint": self.scan_subfolder,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "扫描子文件夹",
            "description": "扫描指定子文件夹的内容"
        },
        {
            "path": "/generate_danmu",
            "endpoint": self.generate_danmu_single,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "生成单个文件弹幕",
            "description": "为指定文件生成弹幕"
        },
        {
            "path": "/scrape_directory",
            "endpoint": self.scrape_directory,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "刮削整个目录",
            "description": "后台批量刮削指定目录下所有媒体文件，需要directory_path参数"
        },
        {
            "path": "/abort_scrape",
            "endpoint": self.abort_scrape,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "中止刮削",
            "description": "中止正在进行的批量刮削任务"
        },
        {
            "path": "/retry_tasks",
            "endpoint": self.get_retry_tasks,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取重试任务列表",
            "description": "获取当前待重试的弹幕文件列表"
        },
        {
            "path": "/process_retry_tasks",
            "endpoint": self.process_retry_tasks,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "处理重试任务",
            "description": "对重试任务列表中的文件进行弹幕刮削"
        },
        {
            "path": "/clear_retry_tasks",
            "endpoint": self.clear_retry_tasks,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "清空重试任务",
            "description": "清空所有重试任务"
        },
        {
            "path": "/remove_retry_task",
            "endpoint": self.remove_retry_task,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "移除重试任务",
            "description": "移除指定的重试任务，需要file_path参数"
        },
        {
            "path": "/clean_subtitles",
            "endpoint": self.clean_subtitles,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "清理字幕文件",
            "description": "清理指定文件或目录下的弹幕和合并字幕文件，支持file_path和directory_path参数"
        },
        {
            "path": "/search_danmu",
            "endpoint": self.search_danmu,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "搜索弹幕资源",
            "description": "根据关键字搜索影视弹幕资源"
        },
        {
            "path": "/manual_match",
            "endpoint": self.set_manual_match,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "保存手动匹配",
            "description": "为目录保存手动匹配的弹弹作品"
        },
        {
            "path": "/remove_manual_match",
            "endpoint": self.remove_manual_match,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "移除手动匹配",
            "description": "移除指定目录的手动匹配"
        },
        {
            "path": "/api_status",
            "endpoint": self.check_api_status,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "检测弹幕API连通性",
            "description": "测试当前配置的弹幕API后端是否可访问"
        },
        {
            "path": "/full_status",
            "endpoint": self._get_full_status,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取完整状态信息",
            "description": "获取插件状态、统计信息、计划任务和最近一次运行详情"
        },
        {
            "path": "/history",
            "endpoint": self.get_history,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取历史记录",
            "description": "获取刮削历史记录，支持分页和详情级别控制"
        },
        {
            "path": "/scan_orphan_subtitles",
            "endpoint": self.scan_orphan_subtitles,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "扫描残留弹幕字幕文件",
            "description": "扫描媒体路径下没有对应媒体文件的字幕文件"
        },
        {
            "path": "/clean_orphan_subtitles",
            "endpoint": self.clean_orphan_subtitles,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "清理残留弹幕字幕文件",
            "description": "清理指定的残留弹幕字幕文件"
        },
        {
            "path": "/scan_directory_stats",
            "endpoint": self.scan_directory_stats,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "扫描目录统计",
            "description": "扫描指定目录及其子目录的媒体文件数量统计"
        },
        {
            "path": "/clear_history",
            "endpoint": self.clear_history,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "清空历史记录",
            "description": "清空所有刮削历史记录"
        },
        {
            "path": "/danmu_presets",
            "endpoint": self._get_danmu_presets,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "获取弹幕参数预设",
            "description": "获取所有已保存的弹幕参数预设方案"
        },
        {
            "path": "/save_danmu_preset",
            "endpoint": self._save_danmu_preset,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "保存弹幕参数预设",
            "description": "保存当前弹幕参数为预设方案"
        },
        {
            "path": "/delete_danmu_preset",
            "endpoint": self._delete_danmu_preset,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "删除弹幕参数预设",
            "description": "删除指定的弹幕参数预设方案"
        }
        ]
     
    # 插件配置页面
    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return None, self._get_config()
    
    def _get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            "enabled": self._enabled,
            "width": self._width,
            "height": self._height,
            "fontsize": self._fontsize,
            "alpha": self._alpha,
            "duration": self._duration,
            "path": self._path,
            "useTmdbID": self._useTmdbID,
            "auto_scrape": self._auto_scrape,
            "enable_retry_task": self._enable_retry_task,
            "enable_history_details": self._enable_history_details,
            "screen_area": self._screen_area,
            "enable_strm": self._enable_strm,
            "danmu_api_url": self._danmu_api_url,
            "enable_multi_layer": self._enable_multi_layer,
            "multi_layer_count": self._multi_layer_count,
            "random_top_bottom": self._random_top_bottom,
            "top_ratio": self._top_ratio,
            "bottom_ratio": self._bottom_ratio,
            "density": self._density,
            "width_scale": self._width_scale
        }
        
    def _save_config(self, config: dict):
        """保存配置"""
        try:
            self._enabled = config.get("enabled", False)
            self._width = config.get("width", 1920)
            self._height = config.get("height", 1080)
            self._fontsize = config.get("fontsize", 50)
            self._alpha = config.get("alpha", 0.9)
            self._duration = config.get("duration", 15)
            self._path = config.get("path", "")
            self._useTmdbID = config.get("useTmdbID", True)
            self._auto_scrape = config.get("auto_scrape", False)
            self._enable_retry_task = config.get("enable_retry_task", True)
            self._enable_history_details = config.get("enable_history_details", False)
            self._screen_area = config.get("screen_area", "full")
            self._enable_strm = config.get("enable_strm", True)
            self._danmu_api_url = config.get("danmu_api_url", self._DEFAULT_DANMU_API_URL)
            self._enable_multi_layer = config.get("enable_multi_layer", False)
            self._multi_layer_count = int(config.get("multi_layer_count", 2))
            self._random_top_bottom = config.get("random_top_bottom", False)
            self._top_ratio = config.get("top_ratio", 0)
            self._bottom_ratio = config.get("bottom_ratio", 0)
            self._density = config.get("density", 100)
            self._width_scale = float(config.get("width_scale", 1.0))
            generator.DanmuAPI.set_api_url(self._danmu_api_url)
            
            self.update_config({
                "enabled": self._enabled,
                "width": self._width,
                "height": self._height,
                "fontsize": self._fontsize,
                "alpha": self._alpha,
                "duration": self._duration,
                "path": self._path,
                "useTmdbID": self._useTmdbID,
                "auto_scrape": self._auto_scrape,
                "enable_retry_task": self._enable_retry_task,
                "screen_area": self._screen_area,
                "enable_strm": self._enable_strm,
                "danmu_api_url": self._danmu_api_url,
                "enable_multi_layer": self._enable_multi_layer,
                "multi_layer_count": self._multi_layer_count,
                "random_top_bottom": self._random_top_bottom,
                "top_ratio": self._top_ratio,
                "bottom_ratio": self._bottom_ratio,
                "density": self._density,
                "width_scale": self._width_scale
            })

            logger.info(f"{self.plugin_name}: 配置已保存。当前内存状态: enabled={self._enabled}")

            return schemas.Response(success=True, message="配置已保存", data=self._get_config())
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return schemas.Response(success=False, message=f"保存配置失败: {str(e)}")
    
    def get_page(self) -> List[dict]:
        """Vue mode doesn't use Vuetify page definitions."""
        return None
    
    # --- V2 Vue Interface Method ---
    @staticmethod
    def get_render_mode() -> Tuple[str, Optional[str]]:
        """Declare Vue rendering mode and assets path."""
        return "vue", "dist/assets"
    
    def _get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self._scrape_lock:
            progress = dict(self._scrape_progress)
        if progress.get("running") and progress.get("started_at"):
            progress["duration"] = int(time.time() - progress["started_at"])
        progress.pop("started_at", None)
        return {
            "enabled": self._enabled,
            **progress
        }

    def generate_danmu(self, file_path: str) -> Optional[str]:
        """
        生成弹幕文件（同一文件同时只允许一个刮削，防止并发写坏弹幕文件）
        :param file_path: 视频文件路径
        :return: 生成的弹幕文件路径，如果失败则返回None或失败原因字符串
        """
        norm = self._normalize_path(file_path) or file_path
        with self._inflight_lock:
            if norm in self._inflight_files:
                logger.info(f"文件正在刮削中，跳过重复请求: {file_path}")
                return "文件正在刮削中，跳过重复请求"
            self._inflight_files.add(norm)
        try:
            return self._generate_danmu_impl(file_path)
        finally:
            with self._inflight_lock:
                self._inflight_files.discard(norm)

    def _generate_danmu_impl(self, file_path: str) -> Optional[str]:
        norm = self._normalize_path(file_path) or file_path
        meta = MetaInfo(file_path)
        tmdb_id = None
        episode = None
        tmdb_id_type = 0
        release_date = None
        use_short_cache_ttl = False
        if self._useTmdbID:
            media_info = self.media_chain.recognize_media(meta=meta)
            if media_info:
                tmdb_id = media_info.tmdb_id
                # Matches dandanplay upstream tmdbIdType: 0 = TV series, 1 = movie
                if media_info.type == MediaType.MOVIE:
                    tmdb_id_type = 1
                    logger.info(f"识别为电影，使用电影类型TMDB匹配: {tmdb_id}")
                if meta.episode:
                    try:
                        episode_str = meta.episode.split('E')[-1]
                        episode = int(episode_str) if episode_str.isdigit() else None
                    except Exception:
                        episode = None
                release_date = media_info.release_date
                if release_date:
                    try:
                        release_datetime = datetime.strptime(release_date, '%Y-%m-%d')
                        is_recent = (datetime.now() - release_datetime).days < 90
                        if is_recent:
                            logger.info(f"媒体 {tmdb_id} 是最近90天内发布的内容,使用短缓存")
                            use_short_cache_ttl = True
                    except ValueError:
                        logger.warning(f"无效的发布日期格式: {release_date},使用默认缓存时间")
    
        manual_comment_id = None
        manual_file_match = self._get_manual_file_match(file_path)
        if manual_file_match:
            manual_episode = generator.DanmuAPI._apply_episode_offset(
                episode, manual_file_match.get("episodeOffset")
            )
            manual_comment_id = generator.DanmuAPI._compose_comment_id(
                manual_file_match.get("animeId"),
                manual_episode
            )
            if manual_comment_id:
                logger.info(f"使用单文件手动匹配ID: {manual_comment_id}")
            else:
                logger.warning(f"单文件手动匹配生成弹幕ID失败: {manual_file_match}")

        try:
            ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
            # 检查本地是否已有弹幕文件，有则跳过API请求，直接复用
            if os.path.exists(ass_file):
                danmu_count = self._count_danmu_lines_cached(ass_file)
                if danmu_count >= self._min_danmu_count:
                    logger.info(f"本地已有弹幕文件，跳过API请求: {ass_file} ({danmu_count}条)")
                    # 直接进行字幕合并（如果有原字幕的话）
                    sub2 = generator.SubtitleProcessor.find_subtitle_file(file_path)
                    if not sub2 and generator.SubtitleProcessor.can_extract_subtitles(file_path):
                        generator.SubtitleProcessor.try_extract_sub(file_path)
                        sub2 = generator.SubtitleProcessor.find_subtitle_file(file_path)
                    if sub2:
                        generator.SubtitleProcessor.combine_sub_ass(ass_file, sub2, file_path)
                    return ass_file
                else:
                    logger.info(f"本地弹幕文件数量不足，重新获取: {ass_file} ({danmu_count}条 < {self._min_danmu_count})")
            
            result = generator.danmu_generator(
                file_path,
                self._width,
                self._height,
                'Arial',
                self._fontsize,
                self._alpha,
                self._duration,
                False,
                self._useTmdbID,
                tmdb_id,
                episode,
                60 if use_short_cache_ttl else None,
                self._screen_area,
                manual_comment_id=manual_comment_id,
                tmdb_id_type=tmdb_id_type,
                enable_multi_layer=self._enable_multi_layer,
                random_top_bottom=self._random_top_bottom,
                top_ratio=self._top_ratio,
                bottom_ratio=self._bottom_ratio,
                density=self._density,
                width_scale=self._width_scale,
                multi_layer_count=self._multi_layer_count
            )
            
            # 检查弹幕生成结果
            ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
            danmu_count = 0
            
            error_type = "unknown"
            error_message = ""
            if isinstance(result, str) and result.startswith('error:'):
                parts = result.split(':', 2)
                if len(parts) >= 2:
                    error_type = parts[1]
                if len(parts) >= 3:
                    error_message = parts[2]
                logger.warning(result)
                self._add_to_retry_if_needed(file_path, 0, error_type, error_message)
                return result
            
            # 如果返回字符串且不是弹幕文件路径，说明是失败原因
            if isinstance(result, str) and not result.endswith('.danmu.chs.ass'):
                error_message = result
                logger.info(result)
                # 检查是否需要添加到重试任务
                self._add_to_retry_if_needed(file_path, 0, "unknown", error_message)
                return result
            
            # 检查生成的弹幕文件
            if os.path.exists(ass_file):
                danmu_count = self._count_danmu_lines_cached(ass_file)
                logger.info(f"弹幕生成完成，弹幕数量: {danmu_count}")
                
                # 检查弹幕数量是否满足要求
                if danmu_count < self._min_danmu_count:
                    logger.warning(f"弹幕数量 ({danmu_count}) 少于最小要求 ({self._min_danmu_count})，添加到重试任务")
                    self._add_to_retry_if_needed(file_path, danmu_count, "no_data", f"弹幕数量不足: {danmu_count}/{self._min_danmu_count}")
                else:
                    # 弹幕数量满足要求，如果之前在重试列表中则移除
                    with self._retry_lock:
                        removed = self._retry_tasks.pop(norm, None)
                    if removed:
                        logger.info(f"弹幕数量满足要求，从重试任务中移除: {file_path}")
                        self._save_retry_tasks()
            else:
                logger.warning(f"弹幕文件不存在: {ass_file}")
                # 没有生成弹幕文件，添加到重试任务
                self._add_to_retry_if_needed(file_path, 0, "unknown", "弹幕文件未生成")
                
            return result
        except Exception as e:
            logger.error(f"生成弹幕失败: {e}")
            # 生成失败，添加到重试任务
            self._add_to_retry_if_needed(file_path, 0, "network", f"生成弹幕失败: {str(e)}")
            return f"生成弹幕失败: {str(e)}"

    def _add_to_retry_if_needed(self, file_path: str, danmu_count: int, error_type: str = "unknown", error_message: str = ""):
        """
        根据弹幕数量判断是否需要添加到重试任务
        :param file_path: 文件路径
        :param danmu_count: 弹幕数量
        :param error_type: 错误类型 (rate_limit/no_data/no_match/network/unknown)
        :param error_message: 错误详细信息
        """
        if not self._enable_retry_task:
            return

        norm = self._normalize_path(file_path) or file_path

        with self._retry_lock:
            now = datetime.now()
            if norm in self._retry_tasks:
                self._retry_tasks[norm]["retry_count"] += 1
                self._retry_tasks[norm]["last_attempt"] = now
                self._retry_tasks[norm]["error_type"] = error_type
                self._retry_tasks[norm]["error_message"] = error_message
                self._retry_tasks[norm]["last_danmu_count"] = danmu_count

                if self._retry_tasks[norm]["retry_count"] >= self._max_retry_times:
                    logger.warning(
                        f"⚠️ 文件已达最大重试次数 ({self._max_retry_times})，放弃自动重试: {file_path} "
                        f"| 最后弹幕数量: {danmu_count} | 错误类型: {error_type} | 请检查手动匹配或弹幕源"
                    )
                    del self._retry_tasks[norm]
                else:
                    retry_count = self._retry_tasks[norm]["retry_count"]
                    next_time = self._calculate_next_retry_time(retry_count, error_type)
                    self._retry_tasks[norm]["next_retry_time"] = next_time
                    logger.info(f"更新重试任务: {file_path}，重试次数: {retry_count}，弹幕数量: {danmu_count}，错误: {error_type}，下次重试: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                if danmu_count < self._min_danmu_count:
                    next_time = self._calculate_next_retry_time(1, error_type)
                    self._retry_tasks[norm] = {
                        "retry_count": 1,
                        "last_attempt": now,
                        "file_path": file_path,
                        "last_danmu_count": danmu_count,
                        "error_type": error_type,
                        "error_message": error_message,
                        "next_retry_time": next_time
                    }
                    logger.info(f"添加新的重试任务: {file_path}，当前弹幕数量: {danmu_count}，错误: {error_type}，下次重试: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")

        self._save_retry_tasks()

    def _calculate_next_retry_time(self, retry_count: int, error_type: str = "unknown") -> datetime:
        """
        计算下次重试时间（指数退避）
        :param retry_count: 当前重试次数
        :param error_type: 错误类型
        :return: 下次重试时间
        """
        base_intervals = [5, 30, 60, 120, 240, 480]
        if retry_count <= len(base_intervals):
            base_minutes = base_intervals[retry_count - 1]
        else:
            base_minutes = 480

        if error_type == "rate_limit":
            base_minutes = max(base_minutes, 30)
        elif error_type == "no_match":
            # 未匹配到作品，重试间隔更长（可能需要手动匹配）
            base_minutes = max(base_minutes, 60)
        elif error_type == "no_data":
            # 无弹幕数据，适当延长重试间隔
            base_minutes = max(base_minutes, 15)

        return datetime.now() + timedelta(minutes=base_minutes)

    def _load_retry_tasks(self):
        """从独立存储加载重试任务（兼容旧版从配置迁移）"""
        # 批量刮削进行中时不重新加载，避免覆盖内存中尚未落盘的重试任务
        with self._retry_lock:
            if self._retry_save_deferred:
                logger.debug("批量刮削进行中，跳过重试任务重新加载")
                return
        try:
            stored = self.get_data("retry_tasks")
            # 兼容旧版：如果独立存储没有，尝试从配置迁移
            if stored is None:
                old_config = self.get_config() or {}
                retry_tasks_str = old_config.get("retry_tasks", "")
                if retry_tasks_str:
                    stored = json.loads(retry_tasks_str)
                    # 迁移到独立存储后，从配置中移除
                    self.save_data("retry_tasks", stored)
                    old_config.pop("retry_tasks", None)
                    self.update_config(old_config)
                    logger.info("重试任务已从插件配置迁移到独立存储")
                else:
                    stored = {}
            if not isinstance(stored, dict):
                stored = {}

            parsed_tasks = {}
            for file_path, task_info in stored.items():
                try:
                    retry_count = task_info.get("retry_count", 1)
                    last_attempt = datetime.fromisoformat(task_info.get("last_attempt", datetime.now().isoformat()))

                    if "next_retry_time" in task_info:
                        next_retry_time = datetime.fromisoformat(task_info["next_retry_time"])
                    else:
                        next_retry_time = self._calculate_next_retry_time(retry_count, task_info.get("error_type", "unknown"))

                    parsed_tasks[file_path] = {
                        "retry_count": retry_count,
                        "last_attempt": last_attempt,
                        "file_path": task_info.get("file_path", file_path),
                        "last_danmu_count": task_info.get("last_danmu_count", 0),
                        "error_type": task_info.get("error_type", "unknown"),
                        "error_message": task_info.get("error_message", ""),
                        "next_retry_time": next_retry_time
                    }
                except (ValueError, TypeError) as e:
                    logger.warning(f"跳过无效的重试任务 {file_path}: {e}")
                    continue
            with self._retry_lock:
                self._retry_tasks = parsed_tasks
            logger.info(f"加载了 {len(parsed_tasks)} 个重试任务")
        except Exception as e:
            logger.warning(f"加载重试任务失败，使用空列表: {e}")
            with self._retry_lock:
                self._retry_tasks = {}

    def _save_retry_tasks(self):
        """
        保存重试任务列表到独立存储（批量刮削期间只标记待保存，结束时统一落盘一次）
        """
        try:
            with self._retry_lock:
                if self._retry_save_deferred:
                    self._retry_save_pending = True
                    return
                # 将datetime对象转换为字符串以便JSON序列化
                retry_tasks_for_save = {}
                for file_path, task_info in self._retry_tasks.items():
                    retry_tasks_for_save[file_path] = {
                        "retry_count": task_info["retry_count"],
                        "last_attempt": task_info["last_attempt"].isoformat(),
                        "file_path": task_info["file_path"],
                        "last_danmu_count": task_info.get("last_danmu_count", 0),
                        "error_type": task_info.get("error_type", "unknown"),
                        "error_message": task_info.get("error_message", ""),
                        "next_retry_time": task_info.get("next_retry_time", datetime.now()).isoformat()
                    }

            self.save_data("retry_tasks", retry_tasks_for_save)
            logger.debug("重试任务列表已保存到独立存储")
        except Exception as e:
            logger.error(f"保存重试任务失败: {e}")

    def update_path(self, path: str):
        """
        更新路径
        """
        self._path = path
        logger.info(f"更新路径: {self._path}")
        
    def _collect_media_files(self, path: str) -> List[str]:
        """
        收集路径下所有支持的媒体文件（目录则递归）
        """
        collected = []
        if os.path.isfile(path):
            if self._is_supported_file(path):
                collected.append(path)
            return collected
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if self._is_supported_file(file_path):
                    collected.append(file_path)
        return collected

    def _has_valid_danmu(self, file_path: str) -> bool:
        """
        检查媒体文件是否已有有效的弹幕字幕（.danmu.chs.ass 存在且弹幕数量达标）
        """
        ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
        if not os.path.exists(ass_file):
            return False
        danmu_count = self._count_danmu_lines_cached(ass_file)
        return danmu_count >= self._min_danmu_count

    def _filter_unscraped_files(self, files: List[str]) -> List[str]:
        """
        过滤掉已有有效弹幕字幕的文件，只保留需要刮削的文件
        """
        unscraped = []
        skipped = 0
        for file_path in files:
            if self._has_valid_danmu(file_path):
                skipped += 1
            else:
                unscraped.append(file_path)
        if skipped > 0:
            logger.info(f"跳过 {skipped} 个已有有效弹幕的文件")
        return unscraped

    def _collect_files_shallowest(self, directory_path: str, max_depth: int = 6) -> List[str]:
        """
        收集目录下媒体文件（每条分支取最浅层含媒体文件的目录，不继续深入）
        :param directory_path: 起始目录
        :param max_depth: 最大递归深度
        :return: 媒体文件列表
        """
        result = []

        def _scan_dir(dir_path: str, depth: int):
            if depth > max_depth:
                return
            local_media = []
            subdirs = []
            try:
                for entry in os.scandir(dir_path):
                    if entry.is_file() and self._is_supported_file(entry.path):
                        local_media.append(entry.path)
                    elif entry.is_dir() and not entry.name.startswith('.'):
                        subdirs.append(entry.path)
            except OSError:
                return

            if local_media:
                # 当前目录有媒体文件，收集并不再深入该分支
                result.extend(local_media)
            else:
                # 当前目录无媒体文件，递归子目录
                for subdir in subdirs:
                    _scan_dir(subdir, depth + 1)

        _scan_dir(directory_path, 0)
        return result

    def _start_scrape_batch(self, files: List[str], label: str) -> bool:
        """
        启动后台批量刮削，已有任务运行时返回False
        """
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
                "duration": 0
            }
        thread = threading.Thread(
            target=self._run_scrape_batch,
            args=(files, label),
            daemon=True
        )
        thread.start()
        return True

    def _run_scrape_batch(self, files: List[str], label: str):
        logger.info(f"开始批量刮削（{label}），共 {len(files)} 个文件")
        # 批量期间不逐文件回写配置，结束后统一保存一次重试任务
        with self._retry_lock:
            self._retry_save_deferred = True
            self._retry_save_pending = False
        
        details = []
        
        # 批量刮削串行执行，避免并发请求触发API限流(429)
        try:
            for file_path in files:
                if self._scrape_aborted:
                    logger.info(f"批量刮削已中止（{label}），停止处理剩余文件")
                    break
                
                with self._scrape_lock:
                    self._scrape_progress["current_file"] = os.path.basename(file_path)
                
                # 始终记录详情（含失败原因），便于排查问题
                result = None
                danmu_count = 0
                error_reason = ""
                try:
                    result = self.generate_danmu(file_path)
                    ok = isinstance(result, str) and result.endswith('.danmu.chs.ass')
                    if ok and os.path.exists(result):
                        danmu_count = self._count_danmu_lines_cached(result)
                except Exception as e:
                    logger.error(f"刮削文件失败: {file_path}: {e}")
                    ok = False
                    error_reason = f"生成弹幕失败: {str(e)}"
                
                if not ok and not error_reason:
                    if isinstance(result, str) and result.startswith('error:'):
                        parts = result.split(':', 2)
                        error_reason = parts[2] if len(parts) >= 3 else result
                    elif result is None:
                        error_reason = "弹幕生成失败"
                    elif isinstance(result, str):
                        error_reason = result
                
                details.append({
                    "file": os.path.basename(file_path),
                    "result": "success" if ok else "failed",
                    "danmu_count": danmu_count,
                    "error": error_reason if not ok else ""
                })
                
                with self._scrape_lock:
                    self._scrape_progress["processed"] += 1
                    if ok:
                        self._scrape_progress["success"] += 1
                    else:
                        self._scrape_progress["failed"] += 1
                
                # 文件间短暂间隔，给API缓冲时间
                time.sleep(0.5)
        finally:
            with self._scrape_lock:
                started_at = self._scrape_progress.get("started_at")
                if started_at:
                    self._scrape_progress["duration"] = int(time.time() - started_at)
                self._scrape_progress["running"] = False
                self._scrape_progress["current_file"] = None
                summary = dict(self._scrape_progress)
            with self._retry_lock:
                self._retry_save_deferred = False
                retry_save_pending = self._retry_save_pending
                self._retry_save_pending = False
            if retry_save_pending:
                self._save_retry_tasks()
            
            history_record = {
                "type": "batch",
                "path": label,
                "processed": summary["total"],
                "success": summary["success"],
                "failed": summary["failed"],
                "duration": summary["duration"],
                "aborted": self._scrape_aborted
            }
            
            if details:
                history_record["details"] = details
            
            self._add_history_record(history_record)
            
            self._scrape_aborted = False
            
            if files:
                directory = os.path.dirname(files[0]) if len(files) == 1 else os.path.dirname(os.path.commonprefix(files))
                self._update_directory_record(directory, {
                    "scrape_status": {
                        "total_files": summary["total"],
                        "scraped_files": summary["success"]
                    },
                    "last_scrape_time": datetime.now().isoformat(timespec="seconds")
                })
        logger.info(
            f"批量刮削完成（{label}）：成功 {summary['success']}，"
            f"失败 {summary['failed']}，共 {summary['total']}"
        )

    def scrape_directory(self, directory_path: str = None, recursive: bool = False) -> schemas.Response:
        """
        刮削指定目录下所有媒体文件
        :param directory_path: 目录路径
        :param recursive: 是否递归子目录（每条分支取最浅层含媒体文件的目录，最多6层）
        """
        if not directory_path:
            return schemas.Response(success=False, message="缺少目录路径")
        if not os.path.isdir(directory_path):
            return schemas.Response(success=False, message="目录不存在")
        
        if recursive:
            files = self._collect_files_shallowest(directory_path, max_depth=6)
        else:
            files = []
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path) and self._is_supported_file(file_path):
                    files.append(file_path)
        
        if not files:
            return schemas.Response(success=False, message="目录下没有支持的媒体文件")
        
        # 过滤已有有效弹幕的文件
        total_before = len(files)
        files = self._filter_unscraped_files(files)
        if not files:
            return schemas.Response(success=False, message=f"所有 {total_before} 个文件已有有效弹幕，无需刮削")
        
        label = f"目录 {directory_path}" + ("（递归）" if recursive else "")
        if not self._start_scrape_batch(files, label):
            return schemas.Response(success=False, message="已有刮削任务进行中，请稍后再试")
        
        skipped = total_before - len(files)
        msg = f"已开始刮削，共 {len(files)} 个文件"
        if skipped > 0:
            msg += f"（跳过 {skipped} 个已有弹幕）"
        return schemas.Response(
            success=True,
            message=msg,
            data={"total": len(files), "skipped": skipped}
        )

    def abort_scrape(self) -> schemas.Response:
        """
        中止正在进行的批量刮削任务
        """
        with self._scrape_lock:
            if not self._scrape_progress.get("running", False):
                return schemas.Response(success=False, message="没有正在进行的刮削任务")
            
            self._scrape_aborted = True
            logger.info("收到中止刮削请求")
        
        return schemas.Response(
            success=True,
            message="已发送中止请求，当前文件处理完成后将停止"
        )

    def generate_danmu_global(self):
        """
        全局刮削弹幕
        """
        if not self._path:
            logger.warning("未设置刮削路径，跳过刮削")
            return schemas.Response(success=False, message="没有设定路径")

        logger.info("开始弹幕刮削")
        paths = [path.strip() for path in self._path.split('\n') if path.strip()]

        files = []
        for path in paths:
            if not os.path.exists(path):
                logger.warning(f"路径不存在: {path}")
                return schemas.Response(success=False, message=f"路径不存在: {path}")
            files.extend(self._collect_media_files(path))

        if not files:
            return schemas.Response(success=False, message="未找到支持的媒体文件")
        if not self._start_scrape_batch(files, "全局"):
            return schemas.Response(success=False, message="已有刮削任务进行中")
        return schemas.Response(
            success=True,
            message=f"已开始刮削，共 {len(files)} 个文件",
            data={"total": len(files)}
        )
    
    @eventmanager.register(EventType.TransferComplete)
    def generate_danmu_after_transfer(self, event):
        """
        传输完成后生成弹幕
        """
        if not self._enabled or not self._auto_scrape:
            return

        def __to_dict(_event):
            """
            递归将对象转换为字典
            """
            if isinstance(_event, dict):
                return {k: __to_dict(v) for k, v in _event.items()}
            elif isinstance(_event, list):
                return [__to_dict(item) for item in _event]
            elif isinstance(_event, tuple):
                return tuple(__to_dict(list(_event)))
            elif isinstance(_event, set):
                return set(__to_dict(list(_event)))
            elif hasattr(_event, 'to_dict'):
                return __to_dict(_event.to_dict())
            elif hasattr(_event, '__dict__'):
                return __to_dict(_event.__dict__)
            elif isinstance(_event, (int, float, str, bool, type(None))):
                return _event
            else:
                return str(_event)

        try:
            raw_data = __to_dict(event.event_data)
            target_file = raw_data.get("transferinfo", {}).get("file_list_new", [None])[0]
            
            if not target_file:
                logger.warning("未找到目标文件")
                return

            logger.info(f"开始生成弹幕文件：{target_file}")
            thread = threading.Thread(
                target=self.generate_danmu,
                args=(target_file,)
            )
            thread.start()
        except Exception as e:
            logger.error(f"处理传输完成事件失败: {e}")

    def stop_service(self):
        """
        退出插件
        """
        pass

    def _count_danmu_lines_cached(self, ass_file: str, stat_result: Optional[os.stat_result] = None) -> int:
        """
        带缓存的弹幕数量统计，文件未变化时直接返回缓存值，避免重复整文件读取
        :param ass_file: 弹幕文件路径
        :param stat_result: 已有的stat结果（来自os.scandir时避免重复stat）
        :return: 弹幕数量
        """
        try:
            st = stat_result or os.stat(ass_file)
        except OSError:
            return 0
        cached = self._danmu_count_cache.get(ass_file)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]
        count = self.count_danmu_lines(ass_file)
        self._danmu_count_cache[ass_file] = (st.st_mtime_ns, st.st_size, count)
        return count

    def count_danmu_lines(self, ass_file: str) -> int:
        """
        计算弹幕文件中的弹幕数量
        :param ass_file: 弹幕文件路径
        :return: 弹幕数量
        """
        try:
            if not os.path.exists(ass_file):
                return 0
            count = 0
            with open(ass_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('Dialogue:'):
                        count += 1
            return count
        except Exception as e:
            logger.error(f"计算弹幕数量失败: {e}")
            return 0

    def scan_path(self, path: str = None, current_dir: str = None) -> schemas.Response:
        """
        扫描路径下的媒体文件和弹幕信息
        :param path: 配置的根路径
        :param current_dir: 当前浏览的目录（用于点击式导航）
        :return: 目录结构信息
        """
        logger.debug(f"开始扫描路径: {path if path else self._path}, 当前目录: {current_dir}")
        
        # 如果有current_dir，直接扫描该目录
        if current_dir:
            return self.scan_subfolder(current_dir)
        
        # 否则使用配置的路径
        if not path:
            path = self._path
            
        if not path:
            logger.debug("未设置扫描路径，返回错误")
            return schemas.Response(success=False, message="未配置刮削路径")
        
        # 处理多路径情况
        paths = [p.strip() for p in path.split('\n') if p.strip()]
        logger.debug(f"解析到 {len(paths)} 个有效路径")
        
        if len(paths) > 1:
            # 多路径情况，返回多个根目录
            logger.debug("处理多路径情况")
            result = {
                "name": "根目录",
                "path": "",
                "type": "root",
                "is_root": True,
                "children": []
            }
            
            for single_path in paths:
                logger.debug(f"处理子路径: {single_path}")
                if os.path.exists(single_path):
                    child_result = self._scan_current_directory(single_path)
                    result["children"].append(child_result)
                else:
                    logger.warning(f"路径不存在: {single_path}")
                    
            logger.debug(f"多路径扫描完成，共 {len(result['children'])} 个有效路径")
            return schemas.Response(success=True, data=result)
        elif len(paths) == 1:
            # 单路径情况
            single_path = paths[0]
            logger.debug(f"处理单路径: {single_path}")
            if not os.path.exists(single_path):
                logger.warning(f"路径不存在: {single_path}")
                return schemas.Response(success=False, message=f"路径不存在: {single_path}")
            
            result = self._scan_current_directory(single_path, is_root=True)
            logger.debug("单路径扫描完成")
            return schemas.Response(success=True, data=result)
        else:
            logger.debug("没有提供有效路径")
            return schemas.Response(success=False, message="未提供有效路径")

    def _scan_current_directory(self, path: str, is_root: bool = False) -> Dict[str, Any]:
        """
        扫描当前目录的直接内容（不递归）
        :param path: 要扫描的目录路径
        :param is_root: 是否为根目录
        :return: 目录结构信息
        """
        logger.debug(f"开始扫描当前目录: {path}, 是否为根目录: {is_root}")
        result = {
            "name": os.path.basename(path) or path,
            "path": path,
            "type": "directory",
            "is_root": is_root,
            "children": []
        }
        if os.path.isdir(path):
            manual_dir_match = self._get_manual_match(path, check_legacy=False)
            result["manual_match"] = manual_dir_match
            result["manual_scope"] = manual_dir_match.get("scope") if manual_dir_match else None
            result["directory_path"] = path
        else:
            manual_file_match = self._get_manual_file_match(path)
            if manual_file_match:
                result["manual_match"] = manual_file_match
                result["manual_scope"] = manual_file_match.get("scope")
            else:
                parent_manual = self._get_manual_match(os.path.dirname(path), check_legacy=False)
                result["manual_match"] = parent_manual
                result["manual_scope"] = parent_manual.get("scope") if parent_manual else None
            result["directory_path"] = os.path.dirname(path)

        try:
            # 如果是文件，直接返回文件信息
            if os.path.isfile(path):
                logger.debug(f"{path} 是文件")
                if self._is_supported_file(path):
                    logger.debug(f"{path} 是媒体文件")
                    result["type"] = "media"
                    result["manual_match"] = self._get_manual_match(os.path.dirname(path), check_legacy=False)
                    # 检查是否存在对应的弹幕文件
                    ass_file = f"{os.path.splitext(path)[0]}.danmu.chs.ass"
                    result["danmu_count"] = self._count_danmu_lines_cached(ass_file)
                return result

            # 扫描目录的直接子项
            logger.debug(f"{path} 是目录，开始扫描直接子项")

            try:
                # 单次scandir同时拿到名称和类型，避免每个条目重复stat
                with os.scandir(path) as it:
                    # 跳过隐藏文件和系统文件
                    entries = [e for e in it if not e.name.startswith('.')]
                logger.debug(f"{path} 目录中共有 {len(entries)} 个项目")
            except PermissionError:
                logger.warning(f"无权限访问目录: {path}")
                result["error"] = "无权限访问该目录"
                return result
            except Exception as e:
                logger.warning(f"列出目录内容失败: {path}, 错误: {str(e)}")
                result["error"] = f"列出目录内容失败: {str(e)}"
                return result

            # 先处理目录，再处理文件
            entry_map = {e.name: e for e in entries}
            directories = []
            files = []

            for entry in entries:
                try:
                    if entry.is_dir():
                        directories.append(entry)
                    elif entry.is_file() and self._is_supported_file(entry.path):
                        files.append(entry)
                except OSError:
                    continue

            # 子文件的目录级手动匹配就是当前目录的匹配，直接复用，不再逐文件查询
            current_dir_manual = result.get("manual_match")
            current_dir_scope = result.get("manual_scope")

            # 添加目录到结果
            for entry in sorted(directories, key=lambda e: e.name):
                child = {
                    "name": entry.name,
                    "path": entry.path,
                    "type": "directory",
                    "children": []
                }
                manual_dir_match = self._get_manual_match(entry.path, check_legacy=False)
                child["manual_match"] = manual_dir_match
                child["manual_scope"] = manual_dir_match.get("scope") if manual_dir_match else None
                child["directory_path"] = entry.path
                
                record = self._get_directory_record(entry.path)
                if record:
                    child["scrape_status"] = record.get("scrape_status", {})
                    child["last_scrape_time"] = record.get("last_scrape_time")
                else:
                    child["scrape_status"] = {"total_files": 0, "scraped_files": 0}
                    child["last_scrape_time"] = None
                
                child["scrape_status"] = self._get_directory_recursive_stats(entry.path)
                result["children"].append(child)

            # 添加媒体文件到结果
            for entry in sorted(files, key=lambda e: e.name):
                child = {
                    "name": entry.name,
                    "path": entry.path,
                    "type": "media",
                    "children": []
                }
                file_manual = self._get_manual_file_match(entry.path)
                if file_manual:
                    child["manual_match"] = file_manual
                    child["manual_scope"] = file_manual.get("scope")
                else:
                    child["manual_match"] = current_dir_manual
                    child["manual_scope"] = current_dir_scope
                child["directory_path"] = path
                # 弹幕文件与媒体同目录，用本次scandir结果判断存在性，避免逐文件stat
                ass_name = f"{os.path.splitext(entry.name)[0]}.danmu.chs.ass"
                ass_entry = entry_map.get(ass_name)
                if ass_entry is not None:
                    try:
                        child["danmu_count"] = self._count_danmu_lines_cached(ass_entry.path, ass_entry.stat())
                    except OSError:
                        child["danmu_count"] = 0
                else:
                    child["danmu_count"] = 0
                result["children"].append(child)

            result["scrape_status"] = self._get_directory_recursive_stats(path)

            logger.debug(f"目录 {path} 扫描完成，发现 {len(files)} 个媒体文件，{len(directories)} 个子目录")
            return result
        except Exception as e:
            logger.error(f"扫描路径失败: {path}, 错误: {e}")
            # 出错时返回基本信息，不中断整个扫描
            result["error"] = str(e)
            return result

    def _get_directory_recursive_stats(self, directory_path: str) -> Dict[str, int]:
        """
        获取目录向下四层（包含当前目录）的汇总统计数据
        :param directory_path: 目录路径
        :return: 汇总统计 {"total_files": int, "scraped_files": int}
        """
        total_files = 0
        scraped_files = 0
        max_depth = 4

        try:
            for root, dirs, files in os.walk(directory_path):
                depth = root[len(directory_path):].count(os.sep)
                if depth >= max_depth:
                    dirs[:] = []
                    continue

                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if self._is_supported_file(os.path.join(root, file)):
                        total_files += 1
                        ass_file = f"{os.path.splitext(os.path.join(root, file))[0]}.danmu.chs.ass"
                        if os.path.exists(ass_file):
                            danmu_count = self._count_danmu_lines_cached(ass_file)
                            if danmu_count >= self._min_danmu_count:
                                scraped_files += 1
        except Exception as e:
            logger.warning(f"获取目录递归统计失败: {directory_path}, 错误: {e}")

        return {"total_files": total_files, "scraped_files": scraped_files}

    def generate_danmu_single(self, file_path: str) -> schemas.Response:
        """
        为单个文件生成弹幕
        :param file_path: 媒体文件路径
        :return: 生成结果
        """
        if not file_path or not os.path.exists(file_path):
            return schemas.Response(success=False, message="文件不存在")
            
        if not self._is_supported_file(file_path):
            if file_path.endswith('.strm') and not self._enable_strm:
                return schemas.Response(success=False, message=".strm文件刮削功能未启用")
            else:
                return schemas.Response(success=False, message="不支持的文件格式")
            
        start_time = time.time()
        try:
            result = self.generate_danmu(file_path)
            elapsed = int(time.time() - start_time)
            
            # 判断是否成功
            ok = isinstance(result, str) and result.endswith('.danmu.chs.ass')
            
            # 提取错误信息
            error_reason = ""
            if not ok:
                if isinstance(result, str) and result.startswith('error:'):
                    parts = result.split(':', 2)
                    error_reason = parts[2] if len(parts) >= 3 else result
                elif result is None:
                    error_reason = "弹幕生成失败"
                else:
                    error_reason = result
            
            # 获取弹幕数量
            ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
            danmu_count = 0
            if os.path.exists(ass_file):
                danmu_count = self._count_danmu_lines_cached(ass_file)
            
            # 记录历史
            detail = {
                "file": os.path.basename(file_path),
                "result": "success" if ok else "failed",
                "danmu_count": danmu_count,
                "error": error_reason if not ok else ""
            }
            history_record = {
                "type": "single",
                "path": file_path,
                "processed": 1,
                "success": 1 if ok else 0,
                "failed": 0 if ok else 1,
                "duration": elapsed,
                "details": [detail]
            }
            self._add_history_record(history_record)
            
            if not ok:
                if result is None:
                    return schemas.Response(success=False, message="弹幕生成失败")
                # 返回清理后的错误信息（去掉error:前缀）
                if isinstance(result, str) and not result.endswith('.ass'):
                    clean_msg = result
                    if result.startswith('error:'):
                        parts = result.split(':', 2)
                        clean_msg = parts[2] if len(parts) >= 3 else parts[1] if len(parts) >= 2 else result
                    return schemas.Response(success=False, message=clean_msg)
            
            logger.info(f"生成弹幕成功，弹幕数量: {danmu_count}")
            if danmu_count == 0:
                return schemas.Response(success=False, message="弹幕数量为0 跳过生成")
            return schemas.Response(
                success=True,
                message="弹幕生成成功",
                data={
                    "danmu_count": danmu_count,
                    "file_path": file_path
                }
            )
        except Exception as e:
            elapsed = int(time.time() - start_time)
            logger.error(f"生成弹幕失败: {e}")
            # 记录失败历史
            self._add_history_record({
                "type": "single",
                "path": file_path,
                "processed": 1,
                "success": 0,
                "failed": 1,
                "duration": elapsed,
                "details": [{
                    "file": os.path.basename(file_path),
                    "result": "failed",
                    "danmu_count": 0,
                    "error": f"生成弹幕失败: {str(e)}"
                }]
            })
            return schemas.Response(success=False, message=f"生成弹幕失败: {str(e)}")

    def check_api_status(self, api_url: Optional[str] = None) -> schemas.Response:
        target_url = (api_url or self._danmu_api_url or "http://localhost:9321").rstrip('/')
        try:
            resp = requests.get(
                f"{target_url}/api/logs",
                headers=generator.DanmuAPI.HEADERS,
                timeout=5
            )
            if resp.status_code == 200:
                return schemas.Response(success=True, message=f"API可访问 ({target_url})")
            elif resp.status_code == 401:
                return schemas.Response(success=False, message=f"API返回401未授权，需要配置Token，请在地址中添加Token，如 http://localhost:9321/your_token")
            else:
                return schemas.Response(success=False, message=f"API返回异常 HTTP {resp.status_code}")
        except Exception as e:
            return schemas.Response(success=False, message=f"API检测失败: {str(e)}")

    def search_danmu(self, keyword: Optional[str] = None, type: Optional[str] = None) -> schemas.Response:
        """
        搜索弹幕资源
        """
        keyword = keyword.strip() if keyword else ""
        if not keyword:
            return schemas.Response(success=False, message="搜索关键字不能为空")

        params = {"keyword": keyword}
        if type and type != "all":
            params["type"] = type

        try:
            response = requests.get(
                f"{generator.DanmuAPI.get_api_url()}/api/v2/search/anime",
                params=params,
                headers=generator.DanmuAPI.HEADERS,
                timeout=(5, 15)
            )
            if response.status_code != 200:
                logger.error(f"搜索弹幕失败，HTTP {response.status_code}: {response.text}")
                return schemas.Response(success=False, message=f"搜索失败: HTTP {response.status_code}")

            data = response.json()
            if not data.get("success", False):
                message = data.get("errorMessage") or "搜索失败"
                logger.warning(f"弹幕搜索返回失败: {message}")
                return schemas.Response(success=False, message=message, data=data)

            return schemas.Response(success=True, data=data)
        except Exception as e:
            logger.error(f"搜索弹幕资源失败: {e}")
            return schemas.Response(success=False, message=f"搜索失败: {str(e)}")

    def set_manual_match(self, data: Dict[str, Any]) -> schemas.Response:
        """
        保存手动匹配结果
        """
        if not isinstance(data, dict):
            return schemas.Response(success=False, message="请求数据无效")

        file_path = data.get("file_path")
        directory_path = data.get("directory")
        scope = (data.get("scope") or "").lower()
        anime = data.get("anime") or {}

        if scope not in {"file", "directory"}:
            scope = "directory" if directory_path or (file_path and data.get("directory")) else "file"

        if scope == "file":
            if not file_path:
                return schemas.Response(success=False, message="缺少文件路径")
        manual_dir = self._resolve_manual_directory(file_path=file_path, directory_path=directory_path)
        if scope == "directory":
            if not manual_dir:
                return schemas.Response(success=False, message="无法确定手动匹配目录")
            if not os.path.isdir(manual_dir):
                return schemas.Response(success=False, message="匹配目录不存在，请刷新后重试")

        anime_id = anime.get("animeId") or anime.get("anime_id")
        if anime_id is None:
            return schemas.Response(success=False, message="缺少animeId")

        try:
            anime_id = int(anime_id)
        except (TypeError, ValueError):
            return schemas.Response(success=False, message="animeId格式无效")

        episode_offset = data.get("episodeOffset", data.get("episode_offset"))
        if episode_offset in (None, ""):
            episode_offset = 0
        try:
            episode_offset = int(episode_offset)
        except (TypeError, ValueError):
            return schemas.Response(success=False, message="集数偏移必须为整数")

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
            "updatedAt": datetime.now().isoformat(timespec="seconds")
        }
        if episode_offset:
            manual_info["episodeOffset"] = episode_offset

        try:
            if scope == "file":
                manual_info["scope"] = "file"
                self._update_manual_file_match_cache(file_path, manual_info)
                logger.info(f"单文件手动匹配已保存: {file_path} -> {anime_id}")
            else:
                manual_info["scope"] = "directory"
                self._write_manual_match_file(manual_dir, manual_info)
                self._update_manual_match_cache(manual_dir, manual_info)
                logger.info(f"目录手动匹配已保存: {manual_dir} -> {anime_id}")
            return schemas.Response(
                success=True,
                message="手动匹配已保存",
                data={
                    "directory": manual_dir if scope == "directory" else self._resolve_manual_directory(file_path=file_path),
                    "file_path": file_path if scope == "file" else None,
                    "manual_match": manual_info
                }
            )
        except Exception as e:
            logger.error(f"保存手动匹配失败: {e}")
            return schemas.Response(success=False, message=f"保存失败: {str(e)}")

    def remove_manual_match(self, file_path: Optional[str] = None, directory: Optional[str] = None,
                             scope: Optional[str] = None) -> schemas.Response:
        """
        移除手动匹配
        """
        scope = (scope or "").lower()
        if scope not in {"file", "directory"}:
            scope = "file" if file_path and not directory else "directory"

        if scope == "file":
            norm = self._normalize_path(file_path)
            if not norm:
                return schemas.Response(success=False, message="未提供有效文件路径")
            removed = self._manual_file_matches.pop(norm, None)
            if removed:
                self._save_manual_state()
            return schemas.Response(success=True, message="单文件手动匹配已移除", data={"file_path": file_path})

        manual_dir = self._resolve_manual_directory(file_path=file_path, directory_path=directory)
        if not manual_dir:
            return schemas.Response(success=False, message="未提供有效目录")

        json_path = self._manual_json_path(manual_dir)
        try:
            if os.path.exists(json_path):
                os.remove(json_path)
                logger.info(f"已删除手动匹配文件: {json_path}")
        except Exception as e:
            logger.warning(f"删除手动匹配文件失败: {e}")

        self._update_manual_match_cache(manual_dir, None)
        return schemas.Response(success=True, message="目录手动匹配已移除", data={"directory": manual_dir})

    def scan_subfolder(self, subfolder_path: str = None) -> schemas.Response:
        """
        专门用于扫描子文件夹的内容（点击式导航）
        :param subfolder_path: 子文件夹路径
        :return: 该子文件夹的内容
        """
        logger.debug(f"扫描子文件夹: {subfolder_path}")
        
        if not subfolder_path:
            logger.warning("未提供子文件夹路径")
            return schemas.Response(success=False, message="未提供子文件夹路径")
        
        if not os.path.exists(subfolder_path):
            logger.warning(f"子文件夹不存在: {subfolder_path}")
            return schemas.Response(success=False, message="文件夹不存在")
        
        if not os.path.isdir(subfolder_path):
            logger.warning(f"指定路径不是文件夹: {subfolder_path}")
            return schemas.Response(success=False, message="指定路径不是文件夹")
        
        try:
            # 检查当前路径是否为用户配置的根路径之一
            is_root = False
            if self._path:
                root_paths = [p.strip() for p in self._path.split('\n') if p.strip()]
                is_root = subfolder_path in root_paths
            
            # 直接扫描这个子文件夹的内容
            result = self._scan_current_directory(subfolder_path, is_root=is_root)
            logger.debug("子文件夹扫描完成")
            return schemas.Response(success=True, data=result)
        except Exception as e:
            logger.error(f"扫描子文件夹失败: {subfolder_path}, 错误: {e}")
            return schemas.Response(success=False, message=f"扫描子文件夹失败: {str(e)}")

    def get_retry_tasks(self) -> schemas.Response:
        """
        获取重试任务列表
        :return: 重试任务列表
        """
        # 转换datetime对象为字符串以便前端显示
        display_tasks = {}
        with self._retry_lock:
            for file_path, task_info in self._retry_tasks.items():
                display_tasks[file_path] = {
                    "retry_count": task_info["retry_count"],
                    "last_attempt": task_info["last_attempt"].strftime("%Y-%m-%d %H:%M:%S"),
                    "file_path": task_info["file_path"],
                    "last_danmu_count": task_info.get("last_danmu_count", 0),
                    "error_type": task_info.get("error_type", "unknown"),
                    "error_message": task_info.get("error_message", ""),
                    "next_retry_time": task_info.get("next_retry_time", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                }
        
        return schemas.Response(
            success=True,
            message=f"获取到 {len(display_tasks)} 个重试任务",
            data={
                "tasks": display_tasks,
                "total": len(display_tasks),
                "min_danmu_count": self._min_danmu_count,
                "max_retry_times": self._max_retry_times
            }
        )

    def process_retry_tasks(self) -> Dict[str, Any]:
        """
        处理重试任务
        :return: 处理结果
        """
        if not self._retry_tasks:
            return schemas.Response(success=True, message="没有待处理的重试任务")
        
        logger.info(f"开始处理 {len(self._retry_tasks)} 个重试任务")
        processed_count = 0
        success_count = 0
        failed_count = 0
        removed_count = 0
        
        # 创建副本以避免在迭代时修改字典
        with self._retry_lock:
            tasks_to_process = list(self._retry_tasks.items())

        for file_path, task_info in tasks_to_process:
            # 检查文件是否仍然存在
            if not os.path.exists(file_path):
                logger.warning(f"重试任务文件不存在，移除: {file_path}")
                with self._retry_lock:
                    self._retry_tasks.pop(file_path, None)
                removed_count += 1
                continue

            # 检查是否达到最大重试次数
            if task_info["retry_count"] >= self._max_retry_times:
                logger.warning(f"文件 {file_path} 已达到最大重试次数 ({self._max_retry_times})，移除")
                with self._retry_lock:
                    self._retry_tasks.pop(file_path, None)
                removed_count += 1
                continue

            # 检查下次重试时间是否到达
            next_retry_time = task_info.get("next_retry_time")
            if next_retry_time and datetime.now() < next_retry_time:
                continue
            
            logger.info(f"处理重试任务: {file_path} (第 {task_info['retry_count'] + 1} 次尝试)")
            
            try:
                # 生成弹幕（这会自动更新重试任务状态）
                result = self.generate_danmu(file_path)
                processed_count += 1
                
                # 检查结果：成功时result为.ass文件路径
                if isinstance(result, str) and result.endswith('.danmu.chs.ass'):
                    # 检查弹幕文件是否满足要求
                    ass_file = f"{os.path.splitext(file_path)[0]}.danmu.chs.ass"
                    if os.path.exists(ass_file):
                        danmu_count = self._count_danmu_lines_cached(ass_file)
                        if danmu_count >= self._min_danmu_count:
                            success_count += 1
                            logger.info(f"重试成功: {file_path}，弹幕数量: {danmu_count}")
                        else:
                            failed_count += 1
                            logger.info(f"重试失败: {file_path}，弹幕数量仍不足: {danmu_count}")
                    else:
                        failed_count += 1
                        logger.warning(f"重试失败: {file_path}，弹幕文件不存在")
                else:
                    failed_count += 1
                    logger.warning(f"重试失败: {file_path}，{result}")
                    
            except Exception as e:
                logger.error(f"处理重试任务失败: {file_path}，错误: {e}")
                failed_count += 1
        
        # 保存更新后的重试任务列表
        self._save_retry_tasks()
        
        result_message = f"重试任务处理完成。处理: {processed_count}, 成功: {success_count}, 失败: {failed_count}, 移除: {removed_count}, 剩余: {len(self._retry_tasks)}"
        logger.info(result_message)
        
        return schemas.Response(
            success=True,
            message=result_message,
            data={
                "processed": processed_count,
                "success": success_count,
                "failed": failed_count,
                "removed": removed_count,
                "remaining": len(self._retry_tasks)
            }
        )

    def clear_retry_tasks(self) -> Dict[str, Any]:
        """
        清空重试任务
        :return: 清空结果
        """
        with self._retry_lock:
            task_count = len(self._retry_tasks)
            self._retry_tasks = {}
        self._save_retry_tasks()
        
        logger.info(f"已清空 {task_count} 个重试任务")
        return schemas.Response(
            success=True,
            message=f"已清空 {task_count} 个重试任务"
        )

    def remove_retry_task(self, file_path: str) -> Dict[str, Any]:
        """
        移除重试任务
        :param file_path: 要移除的重试任务的文件路径
        :return: 移除结果
        """
        if not file_path:
            return schemas.Response(success=False, message="文件路径不能为空")
            
        with self._retry_lock:
            removed = self._retry_tasks.pop(file_path, None)
        if removed:
            self._save_retry_tasks()
            logger.info(f"重试任务已移除: {file_path}")
            return schemas.Response(
                success=True,
                message=f"重试任务已移除: {file_path}"
            )
        else:
            return schemas.Response(
                success=False,
                message=f"未找到重试任务: {file_path}"
            )

    def clean_subtitles(self, file_path: str = None, directory_path: str = None) -> schemas.Response:
        """
        清理字幕文件
        :param file_path: 单个媒体文件路径（清理该文件相关的弹幕和合并字幕）
        :param directory_path: 目录路径（清理该目录下所有弹幕和合并字幕）
        :return: 清理结果
        """
        deleted_files = []
        
        if file_path:
            # 清理单个文件的弹幕和合并字幕
            base_name = os.path.splitext(file_path)[0]
            # 弹幕文件
            danmu_file = f"{base_name}.danmu.chs.ass"
            if os.path.exists(danmu_file):
                os.remove(danmu_file)
                deleted_files.append(os.path.basename(danmu_file))
            # 合并字幕文件
            with_danmu_file = f"{base_name}.chs.withDanmu.ass"
            if os.path.exists(with_danmu_file):
                os.remove(with_danmu_file)
                deleted_files.append(os.path.basename(with_danmu_file))
        elif directory_path:
            # 清理目录下所有弹幕和合并字幕文件
            try:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        if file.endswith('.danmu.chs.ass') or '.withDanmu.ass' in file:
                            full_path = os.path.join(root, file)
                            os.remove(full_path)
                            deleted_files.append(os.path.relpath(full_path, directory_path))
            except Exception as e:
                return schemas.Response(success=False, message=f"清理目录失败: {str(e)}")
        else:
            return schemas.Response(success=False, message="请提供file_path或directory_path参数")
        
        if deleted_files:
            logger.info(f"已清理字幕文件: {deleted_files}")
            return schemas.Response(
                success=True,
                message=f"成功清理 {len(deleted_files)} 个字幕文件",
                data={"deleted": deleted_files}
            )
        else:
            return schemas.Response(
                success=True,
                message="没有可清理的字幕文件"
            )

    def auto_process_retry_tasks(self):
        """
        定时自动处理重试任务
        """
        try:
            if not self._enabled or not self._enable_retry_task:
                logger.debug("弹幕插件或重试任务功能未启用，跳过定时处理")
                return
                
            if not self._retry_tasks:
                logger.debug("没有待处理的重试任务")
                return
                
            logger.info(f"定时任务开始处理 {len(self._retry_tasks)} 个重试任务")
            
            # 调用现有的处理重试任务方法
            result = self.process_retry_tasks()
            
            if result.success:
                logger.info(f"定时任务完成，{result.message}")
            else:
                logger.warning(f"定时任务处理失败: {result.message}")
                
        except Exception as e:
            logger.error(f"定时处理重试任务失败: {e}")

    def _get_full_status(self) -> schemas.Response:
        with self._scrape_lock:
            progress = dict(self._scrape_progress)
        if progress.get("running") and progress.get("started_at"):
            progress["duration"] = int(time.time() - progress["started_at"])
        progress.pop("started_at", None)
        
        stats = {"total_files": 0, "success_count": 0, "failed_count": 0, "retry_tasks_count": 0}
        
        for record in self._directory_records.values():
            scrape_status = record.get("scrape_status", {})
            stats["total_files"] += scrape_status.get("total_files", 0)
            stats["success_count"] += scrape_status.get("scraped_files", 0)
        
        for record in self._global_history:
            stats["failed_count"] += record.get("failed", 0)
        
        with self._retry_lock:
            stats["retry_tasks_count"] = len(self._retry_tasks)
            retry_tasks = dict(self._retry_tasks)
        
        next_retry_time = None
        for task_info in retry_tasks.values():
            nrt = task_info.get("next_retry_time")
            if nrt and (next_retry_time is None or nrt < next_retry_time):
                next_retry_time = nrt
        
        last_run = None
        if self._global_history:
            last_run = self._global_history[0]
        
        api_status = self.check_api_status()
        
        # 检查媒体库路径可访问性
        media_paths = [p.strip() for p in self._path.split('\n') if p.strip()]
        if media_paths:
            media_library_accessible = all(os.path.exists(p) for p in media_paths)
        else:
            media_library_accessible = False
        
        return schemas.Response(
            success=True,
            data={
                "enabled": self._enabled,
                "api_connected": api_status.success,
                "api_message": api_status.message,
                "media_library_accessible": media_library_accessible,
                "media_library_count": len(media_paths),
                "stats": stats,
                "next_retry_time": next_retry_time.strftime("%Y-%m-%d %H:%M:%S") if next_retry_time else None,
                "last_run": last_run,
                **progress
            }
        )

    def scan_directory_stats(self, directory_path: str = None) -> schemas.Response:
        if not directory_path:
            return schemas.Response(success=False, message="缺少目录路径")
        if not os.path.isdir(directory_path):
            return schemas.Response(success=False, message="目录不存在")
        
        total_files = 0
        scraped_files = 0
        dir_stats = {}
        max_depth = 6
        
        for root, dirs, files in os.walk(directory_path):
            depth = root[len(directory_path):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = []
                continue
            
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if self._is_supported_file(os.path.join(root, file)):
                    total_files += 1
                    ass_file = f"{os.path.splitext(os.path.join(root, file))[0]}.danmu.chs.ass"
                    if os.path.exists(ass_file):
                        danmu_count = self._count_danmu_lines_cached(ass_file)
                        if danmu_count >= self._min_danmu_count:
                            scraped_files += 1
            
            dir_stats[root] = {
                "total_files": total_files,
                "scraped_files": scraped_files
            }
        
        self._update_directory_record(directory_path, {
            "scrape_status": {
                "total_files": total_files,
                "scraped_files": scraped_files
            },
            "last_scrape_time": datetime.now().isoformat(timespec="seconds")
        })
        
        return schemas.Response(
            success=True,
            data={
                "directory_path": directory_path,
                "total_files": total_files,
                "scraped_files": scraped_files,
                "dir_stats": dir_stats
            }
        )

    def get_history(self, page: int = 1, page_size: int = 20, include_details: bool = False) -> schemas.Response:
        start = (page - 1) * page_size
        end = start + page_size
        
        history_slice = self._global_history[start:end]
        
        if not include_details:
            for record in history_slice:
                record.pop("details", None)
        
        return schemas.Response(
            success=True,
            data={
                "history": history_slice,
                "total": len(self._global_history),
                "has_more": end < len(self._global_history)
            }
        )

    def clear_history(self) -> schemas.Response:
        self._global_history = []
        self._save_directory_records()
        return schemas.Response(
            success=True,
            message="历史记录已清空"
        )

    def scan_orphan_subtitles(self, path: str = None) -> schemas.Response:
        if not path:
            path = self._path
        
        if not path:
            return schemas.Response(success=False, message="未配置刮削路径")
        
        paths = [p.strip() for p in path.split('\n') if p.strip()]
        orphan_subtitles = []
        
        media_extensions = {'.mp4', '.mkv', '.strm'}
        
        for scan_path in paths:
            if not os.path.exists(scan_path):
                continue
            
            for root, _, files in os.walk(scan_path):
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext.lower() != '.ass':
                        continue
                    
                    if 'danmu' not in file.lower():
                        continue
                    
                    full_path = os.path.join(root, file)
                    base_name = os.path.splitext(full_path)[0].replace('.danmu.chs', '').replace('.danmu', '')
                    
                    has_media = False
                    for media_ext in media_extensions:
                        if os.path.exists(base_name + media_ext):
                            has_media = True
                            break
                    
                    if not has_media:
                        try:
                            stat_result = os.stat(full_path)
                            orphan_subtitles.append({
                                "path": full_path,
                                "size": stat_result.st_size,
                                "modified_time": datetime.fromtimestamp(stat_result.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            })
                        except OSError:
                            continue
        
        return schemas.Response(
            success=True,
            data={
                "scanning": False,
                "orphan_subtitles": orphan_subtitles,
                "total_found": len(orphan_subtitles),
                "scan_path": path
            }
        )

    def clean_orphan_subtitles(self, paths: List[str] = None) -> schemas.Response:
        if not paths or not isinstance(paths, list):
            return schemas.Response(success=False, message="请提供要清理的文件路径列表")
        
        cleaned_count = 0
        failed_count = 0
        cleaned_paths = []
        
        for file_path in paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    cleaned_paths.append(file_path)
                    logger.info(f"已清理残留弹幕字幕文件: {file_path}")
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"清理残留弹幕字幕文件失败: {file_path}, 错误: {e}")
        
        return schemas.Response(
            success=True,
            data={
                "cleaned_count": cleaned_count,
                "failed_count": failed_count,
                "cleaned_paths": cleaned_paths
            }
        )
