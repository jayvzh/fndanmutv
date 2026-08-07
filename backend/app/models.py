from typing import Any, Optional

from pydantic import BaseModel, Field


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
    enable_multi_layer: bool = True
    multi_layer_count: int = 2
    random_top_bottom: bool = False
    top_ratio: int = 0
    bottom_ratio: int = 0
    density: int = 50
    width_scale: float = 1.2

    @classmethod
    def default_config(cls) -> dict:
        return cls().model_dump()


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
