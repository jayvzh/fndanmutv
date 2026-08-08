import chardet
import requests
import os
import re
import hashlib
import subprocess
import json
import time
import threading
import random
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("danmutv.generator")

@dataclass
class VideoInfo:
    file_name: str
    file_hash: str
    file_size: int
    video_duration: int
    match_mode: str = "hashAndFileName"

class StrmProcessor:
    @staticmethod
    def is_strm_file(file_path: str) -> bool:
        """检查是否为.strm文件"""
        return file_path.lower().endswith('.strm')
    
    @staticmethod
    def get_strm_url(file_path: str) -> Optional[str]:
        """读取.strm文件获取流媒体URL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                logger.info(f"从.strm文件读取到URL: {url}")
                return url if url else None
        except Exception as e:
            logger.error(f"读取.strm文件失败: {e}")
            return None
    
    @staticmethod
    def create_fake_video_info(file_path: str) -> VideoInfo:
        """为.strm文件创建虚拟的VideoInfo对象，用于TMDB匹配"""
        file_name = os.path.basename(file_path)
        # 使用文件名作为hash（确保唯一性）
        fake_hash = hashlib.md5(file_name.encode()).hexdigest()
        
        return VideoInfo(
            file_name=file_name,
            file_hash=fake_hash,
            file_size=0,  # .strm文件大小通常很小，设为0
            video_duration=0,  # 无法获取时长，设为0
            match_mode="hashAndFileName"
        )

class DanmuAPI:
    HEADERS = {
        'Accept': 'application/json',
        "User-Agent": "Moviepilot/plugins 2.0.0"
    }
    MANUAL_MATCH_FILE = ".dandan.anime.json"
    TIMEOUT = (10, 60)
    _MIN_REQUEST_INTERVAL = 1.0

    _api_url = "http://localhost:9321"
    _api_token = ""
    _last_request_time = 0
    _request_lock = threading.Lock()
    # 429全局冷却：收到限流后，所有请求等待至该时间戳
    _rate_limit_until = 0.0

    @classmethod
    def set_api_url(cls, full_url: str):
        import re
        
        full_url = full_url.rstrip('/')
        
        match = re.match(r'^(https?://[^/]+)(/[^/]+)?$', full_url)
        if match:
            cls._api_url = match.group(1)
            cls._api_token = match.group(2).lstrip('/') if match.group(2) else ""
        else:
            cls._api_url = full_url
            cls._api_token = ""

    @classmethod
    def get_api_url(cls) -> str:
        if cls._api_token:
            return f"{cls._api_url}/{cls._api_token}"
        return cls._api_url

    @classmethod
    def _throttle_request(cls):
        with cls._request_lock:
            now = time.time()
            # 429全局冷却：如果在冷却期内，等待至冷却结束
            if cls._rate_limit_until > now:
                wait = cls._rate_limit_until - now
                logger.info(f"API限流冷却中，等待{wait:.1f}秒")
                time.sleep(wait)
                now = time.time()
            elapsed = now - cls._last_request_time
            if elapsed < cls._MIN_REQUEST_INTERVAL:
                time.sleep(cls._MIN_REQUEST_INTERVAL - elapsed)
            cls._last_request_time = time.time()

    @classmethod
    def _trigger_rate_limit(cls, cooldown: float = 5.0):
        """触发429限流冷却，所有线程在冷却期内暂停请求"""
        with cls._request_lock:
            cls._rate_limit_until = max(cls._rate_limit_until, time.time() + cooldown)

    @classmethod
    def _manual_file_path(cls, directory: str) -> str:
        return os.path.join(directory, cls.MANUAL_MATCH_FILE)

    @staticmethod
    def _normalize_episode(episode: Optional[int]) -> int:
        try:
            value = int(episode)
        except (TypeError, ValueError):
            value = 1
        return value if value > 0 else 1

    @staticmethod
    def _apply_episode_offset(episode: Optional[int], offset: Any) -> Optional[int]:
        """
        Shift local episode number to the dandanplay-side numbering.
        Local episode + offset = dandanplay episode, clamped to >= 1.
        """
        try:
            offset_int = int(offset)
        except (TypeError, ValueError):
            return episode
        if offset_int == 0:
            return episode
        try:
            episode_int = int(episode)
        except (TypeError, ValueError):
            episode_int = 1
        return max(1, episode_int + offset_int)

    @classmethod
    def _compose_comment_id(cls, anime_id: Any, episode: Optional[int]) -> Optional[str]:
        try:
            anime_id_int = int(anime_id)
        except (TypeError, ValueError):
            return None
        episode_int = cls._normalize_episode(episode)
        return str(anime_id_int * 10000 + episode_int)

    @classmethod
    def _write_manual_mapping(cls, directory: str, data: Dict[str, Any]) -> None:
        if not directory:
            return
        anime_id = data.get("animeId") or data.get("anime_id")
        if anime_id is None:
            return
        try:
            anime_id_int = int(anime_id)
        except (TypeError, ValueError):
            logger.warning(f"手动匹配数据中的animeId无效: {anime_id}")
            return
        payload = dict(data)
        payload["animeId"] = anime_id_int
        payload.pop("anime_id", None)
        payload.setdefault("updatedAt", datetime.now().isoformat(timespec="seconds"))
        manual_path = cls._manual_file_path(directory)
        try:
            with open(manual_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"已写入手动匹配文件: {manual_path}")
        except Exception as e:
            logger.error(f"写入手动匹配文件失败: {e}")

    @classmethod
    def _load_manual_mapping(cls, directory: str) -> Optional[Dict[str, Any]]:
        if not directory or not os.path.isdir(directory):
            return None

        manual_path = cls._manual_file_path(directory)
        if os.path.exists(manual_path):
            try:
                with open(manual_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                anime_id = data.get("animeId") or data.get("anime_id")
                if anime_id is not None:
                    return data
            except Exception as e:
                logger.warning(f"读取手动匹配文件失败: {e}")

        # 兼容旧的 .id 文件
        try:
            for file in os.listdir(directory):
                if not file.endswith('.id'):
                    continue
                legacy_path = os.path.join(directory, file)
                try:
                    anime_id = int(os.path.splitext(file)[0])
                except (TypeError, ValueError):
                    logger.warning(f"忽略无法解析的ID文件: {legacy_path}")
                    continue
                data = {
                    "animeId": anime_id,
                    "source": "legacy-id-file",
                    "updatedAt": datetime.now().isoformat(timespec="seconds")
                }
                cls._write_manual_mapping(directory, data)
                try:
                    os.remove(legacy_path)
                    logger.info(f"已转换旧的ID文件并移除: {legacy_path}")
                except Exception as err:
                    logger.warning(f"移除旧ID文件失败: {err}")
                return data
        except Exception as e:
            logger.warning(f"检查手动匹配目录失败: {e}")

        return None
    @staticmethod
    def calculate_md5_of_first_16MB(file_path: str) -> str:
        md5 = hashlib.md5()
        size_16MB = 16 * 1024 * 1024
        try:
            with open(file_path, 'rb') as f:
                data = f.read(size_16MB)
                md5.update(data)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"计算MD5失败: {e}")
            return ""

    @staticmethod
    def get_video_duration(file_path: str) -> Optional[float]:
        try:
            process = subprocess.Popen(
                ['ffmpeg', '-i', file_path],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            try:
                _, stderr = process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                logger.error(f"获取视频时长超时(120s): {file_path}")
                return None

            stderr = stderr.decode('utf-8', errors='ignore')
            duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", stderr)

            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                return hours * 3600 + minutes * 60 + seconds
            return None
        except Exception as e:
            logger.error(f"获取视频时长失败: {e}")
            return None

    @staticmethod
    def get_file_size(file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"获取文件大小失败: {e}")
            return 0

    @classmethod
    def search_by_tmdb_id(cls, tmdb_id: int, episode: Optional[int] = None,
                          tmdb_id_type: int = 0) -> Optional[str]:
        """
        使用TMDB ID搜索弹幕（新API不支持直接TMDB搜索，使用文件名匹配代替）
        :param tmdb_id: TMDB ID
        :param episode: 集数
        :param tmdb_id_type: TMDB ID类型，0=电视剧，1=电影
        :return: 弹幕ID
        """
        logger.warning(f"新API不支持直接TMDB搜索，请使用文件名匹配")
        return None

    @classmethod
    def search_danmu(cls, keyword: str, media_type: str = "all") -> Optional[Dict]:
        """
        搜索弹幕资源
        :param keyword: 搜索关键字
        :param media_type: 类型（all/tvseries/movie/ova）
        :return: 搜索结果
        """
        try:
            url = f"{cls.get_api_url()}/api/v2/search/anime"
            params = {"keyword": keyword}
            if media_type and media_type != "all":
                params["type"] = media_type
            response = requests.get(url, params=params, headers=cls.HEADERS,
                                    timeout=cls.TIMEOUT)
            if response.status_code == 200:
                return response.json()
            logger.error(f"搜索弹幕失败: {response.text}")
            return None
        except Exception as e:
            logger.error(f"搜索弹幕失败: {e}")
            return None

    @classmethod
    def get_comment_id(cls, file_path: str, use_tmdb_id: bool = False, tmdb_id: Optional[int] = None, episode: Optional[int] = None, cache_ttl: Optional[int] = None, tmdb_id_type: int = 0) -> Optional[str]:
        """
        获取弹幕ID
        :param file_path: 视频文件路径
        :param use_tmdb_id: 是否使用TMDB ID
        :param tmdb_id: TMDB ID
        :param episode: 集数
        :param tmdb_id_type: TMDB ID类型，0=电视剧，1=电影
        :return: 弹幕ID
        """
        try:
            file_name = os.path.basename(file_path)
            
            if StrmProcessor.is_strm_file(file_path):
                logger.info(f"检测到.strm文件: {file_path}")
                strm_url = StrmProcessor.get_strm_url(file_path)
                if strm_url:
                    logger.info(f"STRM文件指向: {strm_url}")
            
            video_dir = os.path.dirname(file_path)
            manual_mapping = cls._load_manual_mapping(video_dir)
            if manual_mapping:
                manual_episode = cls._apply_episode_offset(
                    episode, manual_mapping.get("episodeOffset")
                )
                manual_comment = cls._compose_comment_id(
                    manual_mapping.get("animeId") or manual_mapping.get("anime_id"),
                    manual_episode
                )
                if manual_comment:
                    logger.info(f"使用目录手动匹配ID: {manual_comment}")
                    return manual_comment
            
            title = cls._extract_title_from_filename(file_name)
            file_episode = cls._extract_episode_from_filename(file_name)
            
            if not title:
                logger.warning(f"无法从文件名提取标题: {file_name}")
                return None
            
            target_episode = episode if episode is not None else file_episode
            logger.info(f"从文件名提取: title={title}, episode={target_episode}, episode_type={type(target_episode).__name__}")
            
            if target_episode is not None:
                try:
                    target_episode_int = int(target_episode)
                    logger.info(f"集数转换成功: {target_episode} -> {target_episode_int}, type={type(target_episode_int).__name__}")
                except (ValueError, TypeError) as e:
                    logger.error(f"集数格式错误: {target_episode}, type={type(target_episode).__name__}, error={e}")
                    return None
                match_file_name = f"{title}.S01E{target_episode_int:02d}"
                logger.info(f"使用 S01E 格式匹配: {match_file_name}")
                
                url = f"{cls.get_api_url()}/api/v2/match"
                response = None
                for retry in range(4):
                    cls._throttle_request()
                    response = requests.post(url, json={"fileName": match_file_name}, 
                                             headers=cls.HEADERS, timeout=cls.TIMEOUT)
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:
                        wait = 3 * (2 ** retry)  # 指数退避：3s, 6s, 12s, 24s
                        logger.warning(f"匹配请求被限流(429)，等待{wait}秒后重试 ({retry+1}/4)")
                        cls._trigger_rate_limit(wait)
                        time.sleep(wait)
                    else:
                        break
                
                if response and response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("isMatched") and result.get("matches"):
                        episode_id = str(result["matches"][0]["episodeId"])
                        episode_title = result["matches"][0].get("episodeTitle", "")
                        logger.info(f"匹配成功: episodeId={episode_id}, title={episode_title}")
                        return episode_id
            
            if use_tmdb_id and tmdb_id is not None:
                comment_id = cls.search_by_tmdb_id(tmdb_id, episode, tmdb_id_type)
                if comment_id:
                    return comment_id
            
            return None
        except Exception as e:
            logger.error(f"获取弹幕ID失败: {e}")
            return None

    @staticmethod
    def _extract_title_from_filename(file_name: str) -> Optional[str]:
        """从文件名提取标题（移除年份、集数、扩展名等）"""
        import re
        
        name = os.path.splitext(file_name)[0]
        
        # 移除常见的集数标识
        patterns = [
            r'\.S\d+E\d+',
            r'\.E\d+',
            r'\.\d{4}',
            r'-\s*\d+',
            r'\s*\(\d+\)',
            r'\[[^\]]+\]',
            r'\([^)]+\)',
        ]
        
        for pattern in patterns:
            name = re.sub(pattern, '', name)
        
        # 移除扩展名和多余的点/空格
        name = name.strip('. ').strip()
        
        return name if name else None

    @staticmethod
    def _extract_episode_from_filename(file_name: str) -> Optional[int]:
        """从文件名提取集数"""
        import re
        
        # 匹配 E01, E02, S01E01 等格式
        match = re.search(r'[sS](\d+)[eE](\d+)', file_name, re.IGNORECASE)
        if match:
            return int(match.group(2))
        
        # 匹配 E01, E02 等格式（无前缀季数）
        match = re.search(r'[eE](\d+)', file_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # 匹配 .数字. 格式（如 .01.）
        match = re.search(r'\.(\d{2,3})\.', file_name)
        if match:
            num = int(match.group(1))
            if num <= 999:
                return num
        
        return None

    @staticmethod
    def get_title_from_nfo(file_path: str) -> Optional[str]:
        nfo_file = os.path.splitext(file_path)[0] + '.nfo'
        try:
            with open(nfo_file, 'r', encoding='utf-8') as f:
                nfo_content = f.read()
                title_match = re.search(r'<title>(.*)</title>', nfo_content)
                if title_match:
                    logger.info(f'从nfo文件中获取标题 - {title_match.group(1)}')
                    return title_match.group(1)
                logger.error('未找到标题信息')
                return None
        except Exception as e:
            logger.error(f'读取nfo文件失败: {e}')
            return None

    @classmethod
    def get_comments(cls, comment_id: str, cache_ttl: Optional[int] = None) -> Tuple[Optional[Dict], str]:
        """
        获取弹幕内容
        :param comment_id: 弹幕ID
        :param cache_ttl: 缓存时间（分钟），传给中转服务器控制缓存
        :return: (弹幕数据, 错误类型)；成功时错误类型为空串，失败时为 rate_limit/network
        """
        try:
            url = f"{cls.get_api_url()}/api/v2/comment/{comment_id}?format=json&duration=true"
            if cache_ttl is not None:
                url += f"&cache_ttl={cache_ttl}"

            response = None
            last_error = ""
            for retry in range(4):
                cls._throttle_request()
                response = requests.get(url, headers=cls.HEADERS, timeout=cls.TIMEOUT)
                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    last_error = "rate_limit"
                    wait = 3 * (2 ** retry)  # 指数退避：3s, 6s, 12s, 24s
                    logger.warning(f"获取弹幕被限流(429)，等待{wait}秒后重试 ({retry+1}/4)")
                    cls._trigger_rate_limit(wait)
                    time.sleep(wait)
                else:
                    last_error = "network"
                    break

            if response and response.status_code == 200:
                result = response.json()
                if "comments" not in result:
                    result = {"comments": result}
                return result, ""
            logger.error(f"获取弹幕失败: {response.text if response else '无响应'}")
            return None, last_error or "network"
        except Exception as e:
            logger.error(f"获取弹幕失败: {e}")
            return None, "network"

class DanmuConverter:
    @staticmethod
    def convert_timestamp(timestamp: float) -> str:
        timestamp = round(timestamp * 100.0)
        hour, minute = divmod(timestamp, 360000)
        minute, second = divmod(minute, 6000)
        second, centsecond = divmod(second, 100)
        return f'{int(hour)}:{int(minute):02d}:{int(second):02d}.{int(centsecond):02d}'

    @staticmethod
    def write_ass_head(f, width: int, height: int, fontface: str, fontsize: float, alpha: float, styleid: str, multi_layer: bool = False, multi_layer_count: int = 2):
        alpha_value = int((1 - alpha) * 255)
        
        if multi_layer:
            front_alpha = int((1 - alpha * 1.0) * 255)
            mid_alpha = int((1 - alpha * 0.8) * 255)
            front_fontsize = fontsize * 1.2
            mid_fontsize = fontsize
            
            if multi_layer_count >= 3:
                # 3层模式：顶层/中层/底层
                back_alpha = int((1 - alpha * 0.7) * 255)
                back_fontsize = fontsize * 0.9
                
                f.write(
                    f'''[Script Info]
; Script generated by Hankun 
; Super thanks to https://github.com/m13253/danmaku2ass and https://www.dandanplay.com/
Script Updated By: MoviePilot Danmu Plugin https://github.com/jayvzh/MoviePilot-Plugins
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
Aspect Ratio: {width}:{height}
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {styleid}Front, {fontface}, {front_fontsize:.0f}, &H{front_alpha:02X}FFFFFF, &H{front_alpha:02X}FFFFFF, &H{front_alpha:02X}000000, &H{front_alpha:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(front_fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0
Style: {styleid}Mid, {fontface}, {mid_fontsize:.0f}, &H{mid_alpha:02X}FFFFFF, &H{mid_alpha:02X}FFFFFF, &H{mid_alpha:02X}000000, &H{mid_alpha:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(mid_fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0
Style: {styleid}Back, {fontface}, {back_fontsize:.0f}, &H{back_alpha:02X}FFFFFF, &H{back_alpha:02X}FFFFFF, &H{back_alpha:02X}000000, &H{back_alpha:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(back_fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
                )
            else:
                # 2层模式：顶层/中层
                f.write(
                    f'''[Script Info]
; Script generated by Hankun 
; Super thanks to https://github.com/m13253/danmaku2ass and https://www.dandanplay.com/
Script Updated By: MoviePilot Danmu Plugin https://github.com/jayvzh/MoviePilot-Plugins
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
Aspect Ratio: {width}:{height}
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {styleid}Front, {fontface}, {front_fontsize:.0f}, &H{front_alpha:02X}FFFFFF, &H{front_alpha:02X}FFFFFF, &H{front_alpha:02X}000000, &H{front_alpha:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(front_fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0
Style: {styleid}Mid, {fontface}, {mid_fontsize:.0f}, &H{mid_alpha:02X}FFFFFF, &H{mid_alpha:02X}FFFFFF, &H{mid_alpha:02X}000000, &H{mid_alpha:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(mid_fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
                )
        else:
            f.write(
                f'''[Script Info]
; Script generated by Hankun 
; Super thanks to https://github.com/m13253/danmaku2ass and https://www.dandanplay.com/
Script Updated By: MoviePilot Danmu Plugin https://github.com/jayvzh/MoviePilot-Plugins
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
Aspect Ratio: {width}:{height}
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {styleid}, {fontface}, {fontsize:.0f}, &H{alpha_value:02X}FFFFFF, &H{alpha_value:02X}FFFFFF, &H{alpha_value:02X}000000, &H{alpha_value:02X}000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, {max(fontsize / 25.0, 1):.0f}, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
            )

    @staticmethod
    def find_non_overlapping_track(tracks: Dict[int, float], current_time: float, max_tracks: int) -> Optional[int]:
        for track in range(1, max_tracks + 1):
            if track not in tracks or current_time >= tracks[track]:
                return track
        # 所有轨道都被占用时返回None，避免强行使用忙碌轨道导致重叠
        return None

    @staticmethod
    def find_non_overlapping_track_v2(tracks: Dict[int, dict], current_time: float, text_width: float,
                                      screen_width: int, speed: float, max_tracks: int,
                                      buffer: float = 15.0) -> Optional[int]:
        """统一的滚动弹幕轨道查找（间隙检测 + 追赶检测）。

        tracks 每项: {'born': float, 'speed': float, 'width': float}
        间隙只需 > buffer，因为新弹幕是逐渐从右往左进入的，不需要完整宽度的间隙。
        """
        best_track = None
        best_clearance = -1.0

        for track in range(1, max_tracks + 1):
            if track not in tracks:
                return track

            rd = tracks[track]
            prev_speed = rd['speed']
            prev_width = rd['width']
            elapsed = current_time - rd['born']

            if elapsed < 0:
                continue

            # 上一条右边缘当前位置: 起点(screen_width) - 已移动距离 + 自身宽度
            right_edge = screen_width - elapsed * prev_speed + prev_width

            if right_edge < 0:
                # 上一条已完全离开屏幕左侧，轨道空闲
                return track

            # 当前间隙 = 屏幕右侧 - 上一条右边缘
            clearance = screen_width - right_edge

            if clearance <= buffer:
                continue

            # 追赶检测: 新弹幕更快时，确保到上一条退出前间隙不会耗尽
            if speed > prev_speed:
                remaining_time = (screen_width + prev_width) / prev_speed - elapsed
                if remaining_time > 0:
                    min_clearance = clearance - remaining_time * (speed - prev_speed)
                    if min_clearance <= buffer:
                        continue

            if clearance > best_clearance:
                best_clearance = clearance
                best_track = track

        return best_track

    @classmethod
    def convert_comments_to_ass(cls, comments: List[Dict], output_file: str, width: int,
                              height: int, fontface: str, fontsize: float, alpha: float, duration: float, screen_area: str = 'full',
                              enable_multi_layer: bool = False,
                              random_top_bottom: bool = False, top_ratio: int = 0, bottom_ratio: int = 0,
                              density_count: int = 0,
                              width_scale: float = 1.0,
                              multi_layer_count: int = 2):
        styleid = 'Danmu'

        # 宽度扩展（适配超宽屏视频，解决弹幕左右空白问题）
        if width_scale != 1.0:
            width = int(width * width_scale)
        
        # 根据屏幕区域计算有效高度和轨道数
        if screen_area == 'half':
            effective_height = height // 2  # 上半屏
            logger.info(f"使用半屏弹幕模式，有效高度: {effective_height}")
        elif screen_area == 'third':
            effective_height = height // 3  # 上1/3屏
            logger.info(f"使用1/3屏弹幕模式，有效高度: {effective_height}")
        elif screen_area == 'quarter':
            effective_height = height // 4  # 上1/4屏
            logger.info(f"使用1/4屏弹幕模式，有效高度: {effective_height}")
        else:  # full
            effective_height = height
            logger.info(f"使用全屏弹幕模式，有效高度: {effective_height}")
        
        max_tracks = int(effective_height) // int(fontsize)
        logger.info(f"最大弹幕轨道数: {max_tracks}")
        if width_scale != 1.0:
            logger.info(f"弹幕宽度扩展: {width_scale}x，PlayResX: {width}")
        
        scrolling_tracks = {}
        top_tracks = {}
        bottom_tracks = {}
        # 多层模式下，每层独立轨道字典和轨道数
        if enable_multi_layer:
            scrolling_tracks_front = {}
            scrolling_tracks_mid = {}
            # back层默认空字典（2层模式不会使用，仅作容错）
            scrolling_tracks_back = {}
            max_tracks_front = int(effective_height) // int(fontsize * 1.2)
            max_tracks_mid = max_tracks
            max_tracks_back = 0
            if multi_layer_count >= 3:
                scrolling_tracks_back = {}
                max_tracks_back = int(effective_height) // int(fontsize * 0.9)
                logger.info(f"多层弹幕(3层)轨道数 - 顶层:{max_tracks_front}, 中层:{max_tracks_mid}, 底层:{max_tracks_back}")
            else:
                logger.info(f"多层弹幕(2层)轨道数 - 顶层:{max_tracks_front}, 中层:{max_tracks_mid}")

        logger.info(f"{output_file} - 共匹配到{len(comments)}条弹幕。")

        # 弹幕计数器
        written_count = 0
        dropped_format = 0
        dropped_empty = 0
        dropped_scroll = 0
        dropped_bottom = 0
        dropped_top = 0
        dropped_error = 0
        dropped_density = 0

        # 密度条数控制：预扫描统计非彩色（白色）弹幕数，计算整数百分比保留比例
        # 彩色弹幕全部保留；仅对非彩色弹幕按比例随机淘汰
        keep_ratio_pct = 100  # 整数百分比，100=全部保留
        if density_count and density_count > 0:
            white_count = 0
            for c in comments:
                cp = c.get('p', '').split(',')
                if len(cp) < 3 or not c.get('m', ''):
                    continue
                try:
                    if int(cp[2]) == 16777215:  # 白色
                        white_count += 1
                except (ValueError, IndexError):
                    pass
            if white_count > density_count:
                keep_ratio_pct = max(1, int(density_count * 100 / white_count))
                logger.info(
                    f"弹幕密度条数: 目标{density_count}条, 非彩色{white_count}条, "
                    f"按{keep_ratio_pct}%保留非彩色弹幕（彩色弹幕全部保留）"
                )
            else:
                logger.info(
                    f"弹幕密度条数: 目标{density_count}条, 非彩色{white_count}条, 数量未超限，全部保留"
                )

        with open(output_file, 'w', encoding='utf-8') as f:
            cls.write_ass_head(f, width, height, fontface, fontsize, alpha, styleid, multi_layer=enable_multi_layer, multi_layer_count=multi_layer_count)
            
            for comment in comments:
                try:
                    p = comment.get('p', '').split(',')
                    if len(p) < 3:
                        dropped_format += 1
                        continue
                    
                    timeline = float(p[0])
                    pos = int(p[1])
                    color = int(p[2])
                    text = comment.get('m', '')
                    user = str(p[3])
                    
                    if not text:
                        dropped_empty += 1
                        continue

                    # 密度条数控制：彩色弹幕全部保留；非彩色弹幕按整数百分比随机保留
                    if keep_ratio_pct < 100 and color == 16777215:
                        if random.randint(1, 100) > keep_ratio_pct:
                            dropped_density += 1
                            continue

                    # ASS颜色格式为 &HBBGGGRR&（BGR），需将RGB转换为BGR
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    color_hex = f'&H{b:02X}{g:02X}{r:02X}'
                    styles = ''
                    
                    if pos == 1:  # 滚动弹幕
                        # 随机分配顶部/底部弹幕（从滚动弹幕中转换）
                        if random_top_bottom and (top_ratio > 0 or bottom_ratio > 0):
                            is_colored_tb = color != 16777215  # 白色=16777215
                            if is_colored_tb and top_ratio > 0:
                                # 彩色弹幕优先划分到顶部弹幕
                                pos = 5  # 转为顶部弹幕
                            else:
                                r_tb = random.random() * 100
                                if top_ratio > 0 and r_tb < top_ratio:
                                    pos = 5  # 转为顶部弹幕
                                elif bottom_ratio > 0 and r_tb < top_ratio + bottom_ratio:
                                    pos = 4  # 转为底部弹幕

                    if pos == 1:  # 滚动弹幕
                        if enable_multi_layer:
                            is_colored = color != 16777215  # 白色=16777215
                            if is_colored:
                                # 彩色弹幕优先分配到顶层
                                layer = 'front'
                                layer_num = 10
                                duration_factor = 0.75 + random.random() * 0.15
                                layer_style = f'{styleid}Front'
                                layer_fontsize = fontsize * 1.2
                            else:
                                r = random.random()
                                if multi_layer_count >= 3:
                                    # 3层模式：顶层20% / 中层60% / 底层20%
                                    if r < 0.20:
                                        layer = 'front'
                                        layer_num = 10
                                        duration_factor = 0.75 + random.random() * 0.15
                                        layer_style = f'{styleid}Front'
                                        layer_fontsize = fontsize * 1.2
                                    elif r < 0.80:  # 中层60% (0.20+0.60=0.80)
                                        layer = 'mid'
                                        layer_num = 5
                                        duration_factor = 1.10 + random.random() * 0.2
                                        layer_style = f'{styleid}Mid'
                                        layer_fontsize = fontsize
                                    else:
                                        layer = 'back'
                                        layer_num = 0
                                        duration_factor = 1.35 + random.random() * 0.2
                                        layer_style = f'{styleid}Back'
                                        layer_fontsize = fontsize * 0.9
                                else:
                                    # 2层模式：顶层15% / 中层85%
                                    if r < 0.15:
                                        layer = 'front'
                                        layer_num = 10
                                        duration_factor = 0.75 + random.random() * 0.15
                                        layer_style = f'{styleid}Front'
                                        layer_fontsize = fontsize * 1.2
                                    else:
                                        layer = 'mid'
                                        layer_num = 5
                                        duration_factor = 1.10 + random.random() * 0.2
                                        layer_style = f'{styleid}Mid'
                                        layer_fontsize = fontsize
                            
                            layer_duration = duration * duration_factor
                            start_time = cls.convert_timestamp(timeline)
                            end_time = cls.convert_timestamp(timeline + layer_duration)
                            
                            text_width = len(text) * layer_fontsize * 0.6
                            velocity = (width + text_width) / layer_duration

                            # 根据层选择独立轨道字典和轨道数
                            if layer == 'front':
                                layer_tracks = scrolling_tracks_front
                                layer_max = max_tracks_front
                            elif layer == 'mid':
                                layer_tracks = scrolling_tracks_mid
                                layer_max = max_tracks_mid
                            else:
                                layer_tracks = scrolling_tracks_back
                                layer_max = max_tracks_back

                            track_id = cls.find_non_overlapping_track_v2(
                                layer_tracks, timeline, text_width, width, velocity, layer_max
                            )
                            if track_id is None:
                                dropped_scroll += 1
                                continue

                            layer_tracks[track_id] = {
                                'born': timeline,
                                'speed': velocity,
                                'width': text_width
                            }

                            initial_y = (track_id - 1) * layer_fontsize + 10
                            styles = f'\\move({width}, {initial_y}, {-text_width}, {initial_y})'
                            
                            f.write(f'Dialogue: {layer_num},{start_time},{end_time},{layer_style},,0,0,0,,{{\\c{color_hex}{styles}}}{text}\n')
                        else:
                            start_time = cls.convert_timestamp(timeline)
                            end_time = cls.convert_timestamp(timeline + duration)

                            text_width = len(text) * fontsize * 0.6
                            velocity = (width + text_width) / duration

                            track_id = cls.find_non_overlapping_track_v2(
                                scrolling_tracks, timeline, text_width, width, velocity, max_tracks
                            )
                            if track_id is None:
                                dropped_scroll += 1
                                continue
                            scrolling_tracks[track_id] = {
                                'born': timeline,
                                'speed': velocity,
                                'width': text_width
                            }
                            initial_y = (track_id - 1) * fontsize + 10
                            styles = f'\\move({width}, {initial_y}, {-text_width}, {initial_y})'

                            f.write(f'Dialogue: 0,{start_time},{end_time},{styleid},,0,0,0,,{{\\c{color_hex}{styles}}}{text}\n')
                    elif pos == 4:  # 底部弹幕
                        start_time = cls.convert_timestamp(timeline)
                        end_time = cls.convert_timestamp(timeline + duration)
                        
                        track_id = cls.find_non_overlapping_track(bottom_tracks, timeline, max_tracks)
                        if track_id is None:
                            dropped_bottom += 1
                            continue  # 全部轨道占用，跳过避免重叠
                        bottom_tracks[track_id] = timeline + duration
                        # 底部弹幕需要根据屏幕区域调整位置
                        if screen_area in ('half', 'third', 'quarter'):
                            bottom_y = effective_height - 10 - (track_id - 1) * fontsize
                        else:
                            bottom_y = height - 50 - (track_id - 1) * fontsize
                        styles = f'\\an2\\pos({width/2}, {bottom_y})'
                        
                        f.write(f'Dialogue: 0,{start_time},{end_time},{styleid},,0,0,0,,{{\\c{color_hex}{styles}}}{text}\n')
                    elif pos == 5:  # 顶部弹幕
                        start_time = cls.convert_timestamp(timeline)
                        end_time = cls.convert_timestamp(timeline + duration)
                        
                        track_id = cls.find_non_overlapping_track(top_tracks, timeline, max_tracks)
                        if track_id is None:
                            dropped_top += 1
                            continue  # 全部轨道占用，跳过避免重叠
                        top_tracks[track_id] = timeline + duration
                        styles = f'\\an8\\pos({width/2}, {50 + (track_id - 1) * fontsize})'
                        
                        f.write(f'Dialogue: 0,{start_time},{end_time},{styleid},,0,0,0,,{{\\c{color_hex}{styles}}}{text}\n')
                    else:
                        start_time = cls.convert_timestamp(timeline)
                        end_time = cls.convert_timestamp(timeline + duration)
                        styles = f'\\move(0, 0, {width}, 0)'
                        
                        f.write(f'Dialogue: 0,{start_time},{end_time},{styleid},,0,0,0,,{{\\c{color_hex}{styles}}}{text}\n')

                    written_count += 1
                except Exception as e:
                    dropped_error += 1
                    logger.error(f"处理弹幕数据失败: {e}, 弹幕数据: {comment}")
                    continue
            
            total_dropped = dropped_format + dropped_empty + dropped_density + dropped_scroll + dropped_bottom + dropped_top + dropped_error
            logger.info(f"弹幕统计 - 总数:{len(comments)}, 写入:{written_count}, 丢弃:{total_dropped} "
                        f"(格式错误:{dropped_format}, 空文本:{dropped_empty}, 密度丢弃:{dropped_density}, 滚动满:{dropped_scroll}, "
                        f"底部满:{dropped_bottom}, 顶部满:{dropped_top}, 异常:{dropped_error})")
            logger.info('弹幕生成成功 - ' + output_file)

class SubtitleProcessor:
    @staticmethod
    def get_video_streams(file_path: str) -> Dict:
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            return json.loads(result.stdout) if result.returncode == 0 else {}
        except Exception as e:
            logger.error(f"获取视频流信息失败: {e}")
            return {}

    @staticmethod
    def get_video_resolution(file_path: str) -> Tuple[int, int]:
        """
        获取视频的真实分辨率
        :param file_path: 视频文件路径
        :return: (宽度, 高度) 元组
        """
        try:
            # .strm文件无法直接获取视频分辨率，使用默认值
            if StrmProcessor.is_strm_file(file_path):
                logger.info(f".strm文件使用默认分辨率: 1920x1080")
                return 1920, 1080
            
            streams_info = SubtitleProcessor.get_video_streams(file_path)
            for stream in streams_info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 1920)
                    height = stream.get('height', 1080)
                    logger.info(f"检测到视频分辨率: {width}x{height}")
                    return width, height
            logger.warning(f"未找到视频流，使用默认分辨率: 1920x1080")
            return 1920, 1080
        except Exception as e:
            logger.error(f"获取视频分辨率失败: {e}，使用默认分辨率: 1920x1080")
            return 1920, 1080

    @staticmethod
    def extract_subtitles(file_path: str, output_file: str, stream_index: int) -> bool:
        try:
            result = subprocess.run(
                ['ffmpeg', '-i', file_path, '-map', f'0:{stream_index}', '-c:s', 'ass', output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"提取字幕失败: {e}")
            return False

    @classmethod
    def try_extract_sub(cls, file_path: str):
        streams_info = cls.get_video_streams(file_path)
        for stream in streams_info.get('streams', []):
            if stream.get('codec_type') == 'subtitle':
                stream_index = stream['index']
                base_name = os.path.splitext(file_path)[0]
                language = stream.get('tags', {}).get('language', 'unknown')
                
                if language not in ['zh', 'zho', 'chi', 'chs', 'cht', 'cn']:
                    continue
                    
                output_file = f"{base_name}.{language}.ass"
                # 已有本地提取的字幕文件，跳过重新提取
                if os.path.exists(output_file):
                    logger.info(f"已有本地字幕文件，跳过提取: {output_file}")
                    break
                    
                if cls.extract_subtitles(file_path, output_file, stream_index):
                    logger.info(f'成功提取内嵌字幕 - {output_file}')
                    break

    @staticmethod
    def find_subtitle_file(file_path: str) -> Optional[str]:
        filename = os.path.splitext(os.path.basename(file_path))[0]
        ass_candidates = []
        srt_candidates = []
        for root, _, files in os.walk(os.path.dirname(file_path)):
            for file in files:
                if 'danmu' in file or not file.startswith(filename):
                    continue
                full_path = os.path.join(root, file)
                if file.endswith(('.ass', '.ssa')):
                    ass_candidates.append(full_path)
                elif file.endswith('.srt'):
                    srt_candidates.append(full_path)
        # Prefer .ass/.ssa over .srt for richer style information
        if ass_candidates:
            logger.info(f"找到字幕文件 - {ass_candidates[0]}")
            return ass_candidates[0]
        if srt_candidates:
            logger.info(f"找到字幕文件 - {srt_candidates[0]}")
            return srt_candidates[0]
        logger.info("没找到字幕文件")
        return None
    
    @staticmethod
    def can_extract_subtitles(file_path: str) -> bool:
        """检查是否可以从文件中提取字幕"""
        # .strm文件无法提取内嵌字幕
        return not StrmProcessor.is_strm_file(file_path)

    @staticmethod
    def _convert_srt_timestamp_to_ass(srt_ts: str) -> str:
        """Convert SRT timestamp HH:MM:SS,mmm to ASS H:MM:SS.CC"""
        srt_ts = srt_ts.strip().replace(',', '.')
        parts = srt_ts.split(':')
        if len(parts) != 3:
            return '0:00:00.00'
        hours = int(parts[0])
        minutes = int(parts[1])
        sec_parts = parts[2].split('.')
        seconds = int(sec_parts[0])
        ms_str = sec_parts[1] if len(sec_parts) > 1 else '0'
        ms_str = ms_str.ljust(3, '0')[:3]  # Normalize to exactly 3 digits
        centiseconds = int(ms_str) // 10
        return f'{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}'

    @staticmethod
    def _parse_srt_to_ass_events(srt_content: str, style_name: str) -> List[str]:
        """Parse SRT content into ASS Dialogue lines"""
        # Strip HTML tags commonly found in SRT
        html_tag_re = re.compile(r'<[^>]+>')
        timestamp_re = re.compile(
            r'(\d+:\d{2}:\d{2}[,.]\d+)\s*-->\s*(\d+:\d{2}:\d{2}[,.]\d+)'
        )

        # Normalize line endings (handles \r\n and \r)
        srt_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        lines = []
        for block in blocks:
            block_lines = block.strip().splitlines()
            if len(block_lines) < 2:
                continue

            ts_match = None
            text_start = 0
            for i, line in enumerate(block_lines):
                ts_match = timestamp_re.search(line)
                if ts_match:
                    text_start = i + 1
                    break

            if not ts_match or text_start >= len(block_lines):
                continue

            start = SubtitleProcessor._convert_srt_timestamp_to_ass(ts_match.group(1))
            end = SubtitleProcessor._convert_srt_timestamp_to_ass(ts_match.group(2))

            # Join multiline text with ASS line break \N and strip HTML tags
            text_parts = []
            for tl in block_lines[text_start:]:
                cleaned = html_tag_re.sub('', tl.strip())
                if cleaned:
                    text_parts.append(cleaned)
            text = r'\N'.join(text_parts)

            if text:
                lines.append(
                    f'Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}'
                )
        return lines

    @staticmethod
    def _generate_srt_ass_style(width: int, fontface: str, fontsize: float) -> str:
        """Generate an ASS style line for SRT subtitles (white text, black border, bottom center)"""
        return (
            f'Style: SubtitleSRT, {fontface}, {fontsize:.0f}, '
            f'&H00FFFFFF, &H00FFFFFF, &H00000000, &H80000000, '
            f'0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, '
            f'{max(fontsize / 25.0, 1):.0f}, 0, 2, 20, 20, 20, 0'
        )

    @staticmethod
    def _scale_ass_events(events_text: str, ratio_x: float, ratio_y: float) -> str:
        """Scale absolute coordinates and inline font sizes in ASS Dialogue lines.

        Handles: \\pos, \\org, \\move (first 4 coords), rectangular \\clip/\\iclip,
        and inline \\fs overrides.  Does NOT touch vector clips or \\p drawing paths.
        """

        def _scale_coord_pair(m: re.Match) -> str:
            """Scale a 2-arg tag like \\pos(x,y) or \\org(x,y)"""
            tag = m.group(1)
            x = float(m.group(2)) * ratio_x
            y = float(m.group(3)) * ratio_y
            return f'\\{tag}({x:.2f},{y:.2f})'

        def _scale_move(m: re.Match) -> str:
            """Scale \\move(x1,y1,x2,y2[,t1,t2]) — only scale the first 4 coords"""
            x1 = float(m.group(1)) * ratio_x
            y1 = float(m.group(2)) * ratio_y
            x2 = float(m.group(3)) * ratio_x
            y2 = float(m.group(4)) * ratio_y
            rest = m.group(5)  # optional ",t1,t2" or empty
            return f'\\move({x1:.2f},{y1:.2f},{x2:.2f},{y2:.2f}{rest})'

        def _scale_rect_clip(m: re.Match) -> str:
            """Scale rectangular \\clip(x1,y1,x2,y2) or \\iclip(...)"""
            tag = m.group(1)  # "clip" or "iclip"
            x1 = float(m.group(2)) * ratio_x
            y1 = float(m.group(3)) * ratio_y
            x2 = float(m.group(4)) * ratio_x
            y2 = float(m.group(5)) * ratio_y
            return f'\\{tag}({x1:.2f},{y1:.2f},{x2:.2f},{y2:.2f})'

        def _scale_fs(m: re.Match) -> str:
            """Scale inline \\fs (but not \\fsp, \\fscx, \\fscy)"""
            size = float(m.group(1)) * ratio_y
            return f'\\fs{size:.0f}'

        # Pre-compile patterns
        # \pos(x,y) or \org(x,y) — closing ')' is optional for malformed ASS
        re_coord_pair = re.compile(
            r'\\(pos|org)\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)?'
        )
        # \move(x1,y1,x2,y2[,t1,t2]) — closing ')' is optional
        re_move = re.compile(
            r'\\move\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,'
            r'\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*((?:,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*)?)\)?'
        )
        # Rectangular \clip / \iclip with exactly 4 numeric args — closing ')' is optional
        re_rect_clip = re.compile(
            r'\\(i?clip)\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,'
            r'\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)?'
        )
        # Inline \fs followed by digits (not \fsp, \fscx, \fscy)
        re_fs = re.compile(r'\\fs(\d+(?:\.\d+)?)(?![a-zA-Z])')

        result_lines = []
        for line in events_text.splitlines():
            if not line.startswith('Dialogue:'):
                result_lines.append(line)
                continue

            # Scale Dialogue margins (parts[5]=MarginL, [6]=MarginR, [7]=MarginV)
            parts = line.split(',', 9)
            if len(parts) >= 10:
                for idx, ratio in ((5, ratio_x), (6, ratio_x), (7, ratio_y)):
                    val = parts[idx].strip()
                    if val and int(val) != 0:
                        parts[idx] = str(int(int(val) * ratio))
                line = ','.join(parts)

            # Scale override tags in the Text field
            line = re_coord_pair.sub(_scale_coord_pair, line)
            line = re_move.sub(_scale_move, line)
            line = re_rect_clip.sub(_scale_rect_clip, line)
            line = re_fs.sub(_scale_fs, line)
            result_lines.append(line)
        return '\n'.join(result_lines)

    # Style-name keywords that mark effect/sign subtitles (never blurred)
    _EFFECT_STYLE_KEYWORDS = ('sign', 'title', 'op', 'ed', 'screen', 'note',
                              'comment', 'insert', 'overlap', 'flashback',
                              'song', 'karaoke', 'staff', 'logo')
    # Inline tags that mark positioned/transformed lines.
    # \fad/\fade are common in plain dialogue and intentionally NOT listed.
    _EFFECT_TEXT_TAGS = ('\\pos', '\\move', '\\org', '\\clip', '\\iclip',
                         '\\fr', '\\fax', '\\fay', '\\t(')
    _RE_DRAWING_TAG = re.compile(r'\\p\d')      # \p1 drawing mode (\pos not matched: needs a digit)
    _RE_KARAOKE_TAG = re.compile(r'\\[kK][fo]?\d')

    @classmethod
    def _is_effect_dialogue(cls, style_name: str, text: str) -> bool:
        """
        判断是否为特效字幕行（定位/旋转/变换/绘图/卡拉OK等），特效行不加blur
        :param style_name: 样式名
        :param text: 事件文本字段
        """
        style_lower = style_name.lower()
        for keyword in cls._EFFECT_STYLE_KEYWORDS:
            if keyword in style_lower:
                return True
        for tag in cls._EFFECT_TEXT_TAGS:
            if tag in text:
                return True
        if cls._RE_DRAWING_TAG.search(text) or cls._RE_KARAOKE_TAG.search(text):
            return True
        # \an non-bottom alignment (1,2,3 are bottom)
        an_match = re.search(r'\\an(\d)', text)
        if an_match and int(an_match.group(1)) > 3:
            return True
        # Legacy \a non-bottom alignment
        a_match = re.search(r'\\a(\d+)', text)
        if a_match and int(a_match.group(1)) not in (1, 2, 3):
            return True
        return False

    @staticmethod
    def _resolve_playres(content: str) -> Tuple[Optional[int], Optional[int]]:
        """从ASS内容中解析PlayResX/PlayResY，缺失的返回None"""
        mx = re.search(r"PlayResX:\s*(\d+)", content)
        my = re.search(r"PlayResY:\s*(\d+)", content)
        return (int(mx.group(1)) if mx else None,
                int(my.group(1)) if my else None)

    @staticmethod
    def combine_sub_ass(sub1: str, sub2: str, video_file_path: str = None) -> bool:
        if not sub1 or not sub2:
            return False

        try:
            # If sub2 is already a merged file, use the original subtitle instead
            sub2_base, sub2_ext = os.path.splitext(sub2)
            if sub2_base.endswith('.withDanmu'):
                original_sub2 = sub2_base[:-len('.withDanmu')] + sub2_ext
                if os.path.exists(original_sub2):
                    logger.info(f"检测到已合并字幕，使用原始字幕: {original_sub2}")
                    sub2 = original_sub2
                else:
                    logger.warning(f"已合并字幕的原始文件不存在: {original_sub2}")
                    return False

            with open(sub1, 'r', encoding='utf-8-sig') as f:
                sub1_content = f.read()

            with open(sub2, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                file_encoding = result['encoding']

            with open(sub2, 'r', encoding=file_encoding) as f:
                sub2_content = f.read()
                
            if os.path.splitext(sub2)[1].lower() in ['.ass', '.ssa']:
                # Merge: use danmu's resolution as base, scale original subtitle UP to match
                # Danmu resolution: we always write PlayRes into the danmu header
                d_x, d_y = SubtitleProcessor._resolve_playres(sub1_content)
                d_x, d_y = d_x or 1920, d_y or 1080

                # Original resolution per ASS spec: both missing -> 384x288,
                # one missing -> derived from the other at 4:3
                s_x, s_y = SubtitleProcessor._resolve_playres(sub2_content)
                if s_x is None and s_y is None:
                    s_x, s_y = 384, 288
                elif s_x is None:
                    s_x = round(s_y * 4 / 3)
                elif s_y is None:
                    s_y = round(s_x * 3 / 4)

                # Use danmu's resolution as base for merged file
                # Scale original subtitle UP to danmu resolution if needed
                ratio_x = d_x / s_x
                ratio_y = d_y / s_y
                need_scale = not (ratio_x == 1.0 and ratio_y == 1.0)
                if need_scale:
                    logger.info(
                        f"字幕坐标缩放: 原字幕 {s_x}x{s_y} -> 弹幕分辨率 {d_x}x{d_y}, "
                        f"ratio={ratio_x:.4f}x{ratio_y:.4f}"
                    )

                # Extract the danmu style lines and dialogue events
                danmu_style_lines = re.findall(r'^Style:.*$', sub1_content, re.MULTILINE)
                if not danmu_style_lines:
                    logger.error(f"弹幕文件中未找到样式行: {sub1}")
                    return False
                logger.info(f"弹幕文件中找到 {len(danmu_style_lines)} 条样式")
                danmu_event_lines = [
                    line for line in sub1_content.splitlines()
                    if line.startswith('Dialogue:')
                ]

                # Rename danmu styles if they collide with original style names
                sub2_style_names = {
                    line.split(':', 1)[1].split(',')[0].strip()
                    for line in re.findall(r'^Style:.*$', sub2_content, re.MULTILINE)
                }
                renamed_styles = []
                style_rename_map = {}
                for style_line in danmu_style_lines:
                    style_name = style_line.split(':', 1)[1].split(',')[0].strip()
                    new_name = style_name
                    if new_name in sub2_style_names:
                        while new_name in sub2_style_names or new_name in style_rename_map:
                            new_name += '_MP'
                        style_rename_map[style_name] = new_name
                        logger.info(f"弹幕样式名与原字幕冲突，重命名: {style_name} -> {new_name}")
                    else:
                        style_rename_map[style_name] = new_name
                    fields = style_line.split(',')
                    fields[0] = f'Style: {new_name}'
                    renamed_styles.append(','.join(fields))
                danmu_style_lines = renamed_styles
                
                # Update dialogue events to use renamed styles
                renamed_events = []
                for line in danmu_event_lines:
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        old_style = parts[3]
                        if old_style in style_rename_map:
                            parts[3] = style_rename_map[old_style]
                        renamed_events.append(','.join(parts))
                    else:
                        renamed_events.append(line)
                danmu_event_lines = renamed_events

                # Scale original subtitle styles and events to danmu resolution if needed
                scaled_sub2_content = sub2_content
                if need_scale:
                    # Scale original subtitle styles
                    sub2_style_lines = re.findall(r'^Style:.*$', sub2_content, re.MULTILINE)
                    scaled_sub2_styles = []
                    for style_line in sub2_style_lines:
                        fields = style_line.split(',')
                        if len(fields) >= 17:
                            fields[2] = f'{max(float(fields[2]) * ratio_y, 1):.0f}'
                            fields[16] = f'{max(float(fields[16]) * ratio_y, 0.5):.2f}'
                            scaled_sub2_styles.append(','.join(fields))
                        else:
                            scaled_sub2_styles.append(style_line)
                    
                    # Scale original subtitle events
                    sub2_event_lines = [
                        line for line in sub2_content.splitlines()
                        if line.startswith('Dialogue:')
                    ]
                    scaled_sub2_events = SubtitleProcessor._scale_ass_events(
                        '\n'.join(sub2_event_lines), ratio_x, ratio_y
                    ).splitlines()
                    
                    # Reconstruct scaled sub2 content
                    scaled_sub2_lines = []
                    for line in sub2_content.splitlines():
                        if line.startswith('Style:'):
                            if scaled_sub2_styles:
                                scaled_sub2_lines.append(scaled_sub2_styles.pop(0))
                            else:
                                scaled_sub2_lines.append(line)
                        elif line.startswith('Dialogue:'):
                            if scaled_sub2_events:
                                scaled_sub2_lines.append(scaled_sub2_events.pop(0))
                            else:
                                scaled_sub2_lines.append(line)
                        else:
                            scaled_sub2_lines.append(line)
                    scaled_sub2_content = '\n'.join(scaled_sub2_lines)
                    logger.info(f"已将原字幕缩放到弹幕分辨率")

                # Locate the original subtitle's sections to find insertion
                # points and collect per-style alignment for the blur filter
                sub2_lines = scaled_sub2_content.splitlines()
                section = None
                styles_format_idx = None    # v4+ styles Format line (danmu style goes after it)
                events_format_idx = None    # events Format line (danmu events go after it)
                events_fields = None        # parsed events Format fields, lowercased
                styles_fields = None
                style_alignments = {}       # style name -> Alignment value

                for i, raw in enumerate(sub2_lines):
                    line = raw.strip()
                    if line.startswith('[') and line.endswith(']'):
                        section = line.lower()
                        continue
                    lower = line.lower()
                    if section in ('[v4+ styles]', '[v4 styles]', '[v4++ styles]'):
                        if lower.startswith('format:'):
                            styles_fields = [f.strip().lower() for f in line.split(':', 1)[1].split(',')]
                            # Only insert our v4+ style line into a v4+ section
                            if section != '[v4 styles]' and styles_format_idx is None:
                                styles_format_idx = i
                        elif lower.startswith('style:') and styles_fields:
                            values = line.split(':', 1)[1].split(',')
                            try:
                                name_i = styles_fields.index('name')
                                align_i = styles_fields.index('alignment')
                                style_alignments[values[name_i].strip()] = int(float(values[align_i]))
                            except (ValueError, IndexError):
                                pass
                    elif section == '[events]':
                        if lower.startswith('format:') and events_format_idx is None:
                            events_fields = [f.strip().lower() for f in line.split(':', 1)[1].split(',')]
                            events_format_idx = i

                # Danmu events use the standard v4+ field order; if the original
                # declares a different one, fall back to a separate [Events] section
                standard_events = ['layer', 'start', 'end', 'style', 'name',
                                   'marginl', 'marginr', 'marginv', 'effect', 'text']
                events_insertable = events_fields == standard_events

                def _blur_dialogue(raw_line: str) -> str:
                    """为无特效的底部对白追加柔和模糊，提升纯白字幕在亮背景下的可读性"""
                    if not events_fields or events_fields[-1] != 'text':
                        return raw_line
                    text_i = len(events_fields) - 1
                    body = raw_line.split(':', 1)[1]
                    parts = body.split(',', text_i)
                    if len(parts) <= text_i:
                        return raw_line
                    style_name = parts[events_fields.index('style')].strip() \
                        if 'style' in events_fields else ''
                    effect_val = parts[events_fields.index('effect')].strip() \
                        if 'effect' in events_fields else ''
                    text = parts[text_i]
                    # Skip: Banner/Scroll effects, non-bottom styles, effect lines
                    if effect_val:
                        return raw_line
                    if style_alignments.get(style_name) not in (None, 1, 2, 3):
                        return raw_line
                    if SubtitleProcessor._is_effect_dialogue(style_name, text):
                        return raw_line
                    if text.startswith('{'):
                        parts[text_i] = '{\\blur10' + text[1:]
                    else:
                        parts[text_i] = '{\\blur10}' + text
                    return 'Dialogue:' + ','.join(parts)

                # Assemble: original lines pass through untouched (blur aside),
                # danmu style/events are inserted right after the Format lines
                output_lines = []
                in_events = False
                style_inserted = False
                events_inserted = False
                for i, raw in enumerate(sub2_lines):
                    stripped = raw.strip()
                    if stripped.startswith('[') and stripped.endswith(']'):
                        in_events = stripped.lower() == '[events]'
                    if in_events and raw.startswith('Dialogue:'):
                        output_lines.append(_blur_dialogue(raw))
                    else:
                        output_lines.append(raw)
                    if i == styles_format_idx:
                        output_lines.extend(danmu_style_lines)
                        style_inserted = True
                    if i == events_format_idx and events_insertable:
                        output_lines.extend(danmu_event_lines)
                        events_inserted = True

                # Fallbacks for non-standard structures: append separate
                # sections at the end (renderers merge same-named sections)
                if not style_inserted:
                    output_lines += [
                        '', '[V4+ Styles]',
                        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, '
                        'OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
                        'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, '
                        'Alignment, MarginL, MarginR, MarginV, Encoding',
                    ] + danmu_style_lines
                if not events_inserted:
                    output_lines += [
                        '', '[Events]',
                        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'
                    ]
                    output_lines += danmu_event_lines

                # Update PlayResX/Y in output to match danmu resolution
                final_lines = []
                for line in output_lines:
                    if line.startswith('PlayResX:'):
                        final_lines.append(f'PlayResX: {d_x}')
                    elif line.startswith('PlayResY:'):
                        final_lines.append(f'PlayResY: {d_y}')
                    else:
                        final_lines.append(line)

                output = os.path.splitext(sub2)[0] + ".withDanmu.ass"
                with open(output, 'w', encoding='utf-8-sig') as f:
                    f.write('\n'.join(final_lines))
                    f.write('\n')

                logger.info(f"字幕合并完成（原字幕保持原样）: {output}")
                return True

            elif os.path.splitext(sub2)[1].lower() == '.srt':
                # Parse SRT and convert to ASS events
                dialogue_lines = SubtitleProcessor._parse_srt_to_ass_events(
                    sub2_content, 'SubtitleSRT'
                )
                if not dialogue_lines:
                    logger.warning(f"SRT字幕解析为空: {sub2}")
                    return False

                # Get resolution from danmu file for style generation
                sub1ResX = re.search(r"PlayResX:\s*(\d+)", sub1_content)
                width = int(sub1ResX.group(1)) if sub1ResX else 1920
                srt_style = SubtitleProcessor._generate_srt_ass_style(
                    width, 'Arial', 50
                )

                # Apply blur to SRT dialogue lines
                blurred_lines = []
                for line in dialogue_lines:
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        text = parts[9]
                        parts[9] = '{\\blur10}' + text
                        blurred_lines.append(','.join(parts))
                    else:
                        blurred_lines.append(line)

                output = os.path.splitext(sub2)[0] + ".withDanmu.ass"
                with open(output, 'w', encoding='utf-8-sig') as f:
                    f.write(sub1_content)
                    f.write('\n[V4+ Styles]\n')
                    f.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
                    f.write(srt_style)
                    f.write('\n[Events]\n')
                    f.write('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
                    f.write('\n'.join(blurred_lines))

                logger.info(f"SRT字幕合并完成: {output}")
                return True

            return False
            
        except Exception as e:
            logger.error(f"合并字幕失败: {e}")
            return False

def danmu_generator(file_path: str, width: int = 1920, height: int = 1080,
                   fontface: str = 'Arial', fontsize: float = 50,
                   alpha: float = 0.8, duration: float = 6, onlyFromBili: bool = False,
                   use_tmdb_id: bool = False, tmdb_id: Optional[int] = None,
                   episode: Optional[int] = None, cache_ttl: Optional[int] = None,
                   screen_area: str = 'full', manual_comment_id: Optional[str] = None,
                   tmdb_id_type: int = 0, enable_multi_layer: bool = False,
                   random_top_bottom: bool = False, top_ratio: int = 0, bottom_ratio: int = 0,
                   density_count: int = 0,
                   width_scale: float = 1.0,
                   multi_layer_count: int = 2) -> Optional[str]:
    try:
        comment_id = manual_comment_id or DanmuAPI.get_comment_id(
            file_path, use_tmdb_id, tmdb_id, episode, cache_ttl, tmdb_id_type
        )
        if not comment_id:
            logger.info(f"未找到对应弹幕 - {file_path}")
            return "error:no_match:未找到对应弹幕"

        comments_data, comments_error = DanmuAPI.get_comments(comment_id, cache_ttl=cache_ttl)
        if not comments_data:
            if comments_error == "rate_limit":
                return "error:rate_limit:未获取到弹幕数据（429限流）"
            return "error:network:未获取到弹幕数据（网络错误）"

        comments = sorted(comments_data["comments"], key=lambda x: float(x['p'].split(',')[0]))

        if len(comments) == 0:
            logger.info(f"弹幕数量为0，跳过生成 - {file_path}")
            return "error:no_data:弹幕数量为0，跳过生成"

        # 过滤B站弹幕
        if onlyFromBili:
            comments = [comment for comment in comments if '[BiliBili]' in comment['p'].split(',')[3]]
            logger.info(f"过滤后剩余{len(comments)}条B站弹幕")

        output_file = os.path.splitext(file_path)[0] + '.danmu.chs.ass'
        
        DanmuConverter.convert_comments_to_ass(
            comments, output_file, 
            width=int(width), 
            height=int(height), 
            fontface=fontface, 
            fontsize=float(fontsize), 
            alpha=float(alpha), 
            duration=float(duration),
            screen_area=screen_area,
            enable_multi_layer=enable_multi_layer,
            random_top_bottom=random_top_bottom,
            top_ratio=top_ratio,
            bottom_ratio=bottom_ratio,
            density_count=density_count,
            width_scale=width_scale,
            multi_layer_count=multi_layer_count
        )

        # 处理字幕合并
        sub2 = SubtitleProcessor.find_subtitle_file(file_path)
        
        # 只有非.strm文件才尝试提取内嵌字幕
        if not sub2 and SubtitleProcessor.can_extract_subtitles(file_path):
            SubtitleProcessor.try_extract_sub(file_path)
            sub2 = SubtitleProcessor.find_subtitle_file(file_path)

        if sub2:
            SubtitleProcessor.combine_sub_ass(output_file, sub2, file_path)
        else:
            if StrmProcessor.is_strm_file(file_path):
                logger.info(f'.strm文件未找到外部字幕，仅生成弹幕文件 - {file_path}')
            else:
                logger.info(f'未找到原生字幕，跳过合并 - {file_path}')

        return output_file

    except Exception as e:
        logger.error(f"生成弹幕失败: {e}")
        return f"生成弹幕失败: {str(e)}"
