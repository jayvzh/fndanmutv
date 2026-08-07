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
    enabled: bool = False
    width: int = 1920
    height: int = 1080
    fontsize: int = 48
    alpha: float = 0.7
    duration: int = 14
    path: str = ""
    auto_scrape: bool = True
    enable_retry_task: bool = True
    enable_history_details: bool = False
    screen_area: str = "quarter"
    enable_strm: bool = True
    danmu_api_url: str = "http://danmu-api:9321"
    enable_multi_layer: bool = False
    multi_layer_count: int = 2
    random_top_bottom: bool = False
    top_ratio: int = 0
    bottom_ratio: int = 0
    density: int = 100
    width_scale: float = 1.0
    auto_scrape_interval: int = 3600
    auto_scrape_on_start: bool = False

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
