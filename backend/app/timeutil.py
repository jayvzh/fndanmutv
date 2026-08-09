"""时区工具。

统一使用中国时区（UTC+8，无夏令时），使重试任务、历史记录等时间显示为中国时间。
时区可通过环境变量 TZ 覆盖（如 Asia/Shanghai）；解析失败时回退到固定 UTC+8。
"""
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _load_tz():
    tz_name = os.getenv("TZ", "").strip()
    if tz_name and ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    # 回退到固定 UTC+8（中国时区，无夏令时）
    return timezone(timedelta(hours=8))


CN_TZ = _load_tz()


def now() -> datetime:
    """返回当前中国时区时间（aware datetime）。"""
    return datetime.now(CN_TZ)


def from_timestamp(ts: float) -> datetime:
    """将时间戳转为中国时区时间。"""
    return datetime.fromtimestamp(ts, CN_TZ)


def ensure_aware(dt: datetime) -> datetime:
    """确保 datetime 带有时区信息；naive datetime 视为中国时区。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CN_TZ)
    return dt
