import os
import re
from dataclasses import dataclass
from typing import Optional

from app.danmu_generator import DanmuAPI


@dataclass
class ParsedMedia:
    title: Optional[str]
    season: Optional[int]
    episode: Optional[int]
    is_movie: bool
    is_strm: bool


_SEASON_RE = re.compile(r"[sS](\d+)[eE](\d+)")
_EP_RE = re.compile(r"(?:^|[^A-Za-z0-9])[eE][pP]?(\d{1,3})(?:\D|$)")
_DOT_NUM_RE = re.compile(r"\.(\d{2,3})(?:\.|$)")
_CHINESE_EP_RE = re.compile(r"第\s*(\d{1,3})\s*(?:集|话|話|期|回)")
_RANGE_RE = re.compile(r"第\s*(\d{1,3})\s*[-~至到]\s*(\d{1,3})\s*(?:集|话|話|期|回)")


def _extract_season(file_name: str) -> Optional[int]:
    m = _SEASON_RE.search(file_name)
    if m:
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return None
    return None


def _extract_episode(file_name: str) -> Optional[int]:
    # 优先复用引擎中的解析逻辑，覆盖 SxxExx / Exx / .NN.
    ep = DanmuAPI._extract_episode_from_filename(file_name)
    if ep is not None:
        return ep
    # 中文 "第x集/话/期"
    m = _CHINESE_EP_RE.search(file_name)
    if m:
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return None
    # 范围集取第一集
    m = _RANGE_RE.search(file_name)
    if m:
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return None
    return None


def parse_media(file_path: str) -> ParsedMedia:
    file_name = os.path.basename(file_path or "")
    season = _extract_season(file_name)
    episode = _extract_episode(file_name)
    title = DanmuAPI._extract_title_from_filename(file_name)
    is_strm = file_name.lower().endswith(".strm")
    return ParsedMedia(
        title=title,
        season=season,
        episode=episode,
        is_movie=episode is None,
        is_strm=is_strm,
    )
