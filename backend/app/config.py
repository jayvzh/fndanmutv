import logging
import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("danmutv.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DANMUTV_",
        env_file=".env",
        extra="ignore",
    )

    data_dir: str = "/data"
    token: str = ""
    log_level: str = "INFO"
    # 前端构建产物目录，单独使用 FRONTEND_DIST 环境变量
    frontend_dist: str = "/app/static"

    def __init__(self, **values):
        super().__init__(**values)
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        if not self.token:
            self.token = secrets.token_urlsafe(24)
            logger.warning(
                "未配置 DANMUTV_TOKEN，已自动生成临时 Token（重启后会变化）：%s",
                self.token,
            )

    def ensure_data_dir(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_db_path(self) -> str:
        return str(self.ensure_data_dir() / "danmutv.db")


settings = Settings()
