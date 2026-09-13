import os
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.config import settings


class ApiResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "") -> "ApiResponse":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "ApiResponse":
        return cls(success=False, message=message, data=data)


class AppConfig(BaseModel):
    # 工具默认启用，不再保留 MoviePilot 时代的“启用插件”总开关
    width: int = 1920
    height: int = 1080
    fontsize: int = 48
    alpha: float = 0.6
    duration: int = 14
    path: str = ""
    # 是否启用媒体库定时自动刮削；关闭则仅支持手动刮削
    auto_scrape: bool = False
    # 自动刮削模式：incremental=增量（跳过已有有效弹幕），full=全量（重新刮削所有文件）
    auto_scrape_mode: str = "incremental"
    auto_scrape_interval: int = 3600
    enable_retry_task: bool = True
    enable_history_details: bool = False
    screen_area: str = "quarter"
    enable_strm: bool = True
    danmu_api_url: str = "http://danmu-api:9321"
    # 对 danmu-api 的最小请求间隔（秒），0=不限。默认 21s ≈ 3 次/分钟，
    # 对应 danmu-api 端 RATE_LIMIT_MAX_REQUESTS（默认 3 次/分钟，0=不限流）
    api_request_interval: float = 21.0
    enable_multi_layer: bool = True
    multi_layer_count: int = 2
    random_top_bottom: bool = False
    top_ratio: int = 0
    bottom_ratio: int = 0
    # 弹幕密度条数：0=全部；其余为目标保留条数（3000/5000/8000）
    density_count: int = 5000
    width_scale: float = 1.2

    @classmethod
    def default_config(cls) -> dict:
        cfg = cls().model_dump()
        # Docker 通过 DANMUTV_MEDIA_DIR 注入媒体库路径（如 /media），
        # 若用户未显式配置 path 且该目录存在，则作为默认刮削路径
        media_dir = (settings.media_dir or "").strip()
        if media_dir and not cfg.get("path") and os.path.isdir(media_dir):
            cfg["path"] = media_dir
        # Docker 内置部署通过 DANMUTV_API_REQUEST_INTERVAL 注入更快的默认节流间隔
        if settings.api_request_interval is not None:
            cfg["api_request_interval"] = settings.api_request_interval
        return cfg


class AnimeInfo(BaseModel):
    animeId: Optional[Any] = None
    animeTitle: Optional[str] = None
    imageUrl: Optional[str] = None
    type: Optional[str] = None
    typeDescription: Optional[str] = None
    episodeCount: Optional[Any] = None
    rating: Optional[Any] = None
    startDate: Optional[str] = None

    model_config = {"extra": "allow"}


class ManualMatchRequest(BaseModel):
    file_path: Optional[str] = None
    directory: Optional[str] = None
    scope: str = "directory"
    episodeOffset: Optional[int] = None
    anime: AnimeInfo = Field(default_factory=AnimeInfo)
