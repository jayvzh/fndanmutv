import logging
import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("danmutv.config")

# 项目根目录（backend/app/config.py -> backend -> root）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DANMUTV_",
        env_file=".env",
        extra="ignore",
    )

    # 本地开发默认使用项目根 data/；Docker 通过环境变量覆盖为 /data
    data_dir: str = str(_PROJECT_ROOT / "data")
    token: str = ""
    log_level: str = "INFO"
    # 前端构建产物目录，单独使用 FRONTEND_DIST 环境变量
    frontend_dist: str = str(_PROJECT_ROOT / "frontend" / "dist")

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
