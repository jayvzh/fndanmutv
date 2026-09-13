import os
import re
import time
from typing import Any, Optional

from app.models import ApiResponse
from app import timeutil

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m4v", ".strm"}
# .withDanmu.ass 的同伴是原字幕（danmu_generator 仅处理 ass/ssa/srt）
SUBTITLE_EXTENSIONS = {".ass", ".ssa", ".srt"}

# Jellyfin/Emby 弹幕插件（cxfksword jellyfin-plugin-danmu / fengymi emby-plugin-danmu）
# 命名：<视频名>[.语言][.default][SourceId_danmu].ass
# 例：难哄.2025.第12集.chs[YoukuID_danmu].ass、Show.zh-CN[BiliBiliId_danmu].ass
_RE_PLUGIN_DANMU_TAG = re.compile(r"\[[^\]]*_danmu\]", re.IGNORECASE)
_RE_PLUGIN_LANG_TAIL = re.compile(
    r"(?:\.(?:chs|cht|zh|zho|chi|cn|zh-cn|zh-tw|zh-hk|zh-sg|zh-hans|zh-hant"
    r"|en|eng|default|forced|foreign|sdh|cc))+$",
    re.IGNORECASE,
)


def _classify_danmu_ass(full_path: str) -> Optional[tuple[str, str]]:
    """识别弹幕字幕并返回 (同伴类型, 不含扩展名的同伴 basename 完整路径)。

    同伴类型："media" 找同 basename 视频；"subtitle" 找同 basename 原字幕。
    非本程序/已知弹幕插件规格的 .ass 返回 None（不纳入孤儿扫描）。
    """
    lower = full_path.lower()
    if lower.endswith(".danmu.chs.ass"):
        return "media", full_path[: -len(".danmu.chs.ass")]
    if lower.endswith(".danmu.ass"):
        return "media", full_path[: -len(".danmu.ass")]
    if lower.endswith(".withdanmu.ass"):
        return "subtitle", full_path[: -len(".withDanmu.ass")]
    if lower.endswith(".ass") and _RE_PLUGIN_DANMU_TAG.search(full_path):
        # 去掉 [xxxx_danmu] 标记与 Jellyfin 语言/标志后缀，还原视频 basename
        base = _RE_PLUGIN_DANMU_TAG.sub("", full_path[: -len(".ass")])
        base = _RE_PLUGIN_LANG_TAIL.sub("", base).rstrip(".")
        return "media", base
    return None


def is_supported_file(file_path: str, enable_strm: bool = True) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".strm":
        return enable_strm
    return ext in MEDIA_EXTENSIONS


def _count_danmu(svc, ass_path: str, stat_result: Optional[os.stat_result] = None) -> int:
    if svc is not None and hasattr(svc, "count_danmu_lines_cached"):
        return svc.count_danmu_lines_cached(ass_path, stat_result)
    try:
        st = stat_result or os.stat(ass_path)
    except OSError:
        return 0
    try:
        count = 0
        with open(ass_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    count += 1
        return count
    except OSError:
        return 0


def _manual_match(svc, path: str, scope: str = "directory"):
    if svc is None:
        return None
    if scope == "file":
        return svc.get_manual_file_match(path)
    return svc.get_manual_match(path, check_legacy=False)


def _directory_record(svc, path: str) -> Optional[dict]:
    if svc is None:
        return None
    return svc.get_directory_record(path)


def _directory_recursive_stats(svc, directory_path: str, max_depth: int = 4,
                               min_danmu_count: int = 100,
                               enable_strm: bool = True) -> dict:
    total_files = 0
    scraped_files = 0
    try:
        for root, dirs, files in os.walk(directory_path):
            depth = root[len(directory_path):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                full = os.path.join(root, file)
                if is_supported_file(full, enable_strm):
                    total_files += 1
                    ass_file = f"{os.path.splitext(full)[0]}.danmu.chs.ass"
                    if os.path.exists(ass_file):
                        if _count_danmu(svc, ass_file) >= min_danmu_count:
                            scraped_files += 1
    except OSError:
        pass
    return {"total_files": total_files, "scraped_files": scraped_files}


def _entry_mtime(entry) -> Optional[float]:
    """条目修改时间（秒级时间戳），取不到时为 None（前端排最后）"""
    try:
        return entry.stat().st_mtime
    except OSError:
        return None


def scan_current_directory(svc, path: str, is_root: bool = False,
                           min_danmu_count: int = 100,
                           enable_strm: bool = True,
                           include_child_stats: bool = True) -> dict:
    result: dict[str, Any] = {
        "name": os.path.basename(path) or path,
        "path": path,
        "type": "directory",
        "is_root": is_root,
        "children": [],
    }
    if os.path.isdir(path):
        manual_dir_match = _manual_match(svc, path, "directory")
        result["manual_match"] = manual_dir_match
        result["manual_scope"] = manual_dir_match.get("scope") if manual_dir_match else None
        result["directory_path"] = path
    else:
        parent_manual = _manual_match(svc, os.path.dirname(path), "directory")
        result["manual_match"] = parent_manual
        result["manual_scope"] = parent_manual.get("scope") if parent_manual else None
        result["directory_path"] = os.path.dirname(path)

    try:
        if os.path.isfile(path):
            if is_supported_file(path, enable_strm):
                result["type"] = "media"
                result["manual_match"] = _manual_match(svc, os.path.dirname(path), "directory")
                ass_file = f"{os.path.splitext(path)[0]}.danmu.chs.ass"
                result["danmu_count"] = _count_danmu(svc, ass_file)
            return result

        try:
            with os.scandir(path) as it:
                entries = [e for e in it if not e.name.startswith(".")]
        except PermissionError:
            result["error"] = "无权限访问该目录"
            return result
        except OSError as e:
            result["error"] = f"列出目录内容失败: {e}"
            return result

        entry_map = {e.name: e for e in entries}
        directories = []
        files = []
        for entry in entries:
            try:
                if entry.is_dir():
                    directories.append(entry)
                elif entry.is_file() and is_supported_file(entry.path, enable_strm):
                    files.append(entry)
            except OSError:
                continue

        current_dir_manual = result.get("manual_match")
        current_dir_scope = result.get("manual_scope")

        for entry in sorted(directories, key=lambda e: e.name):
            child = {
                "name": entry.name,
                "path": entry.path,
                "type": "directory",
                "children": [],
                "mtime": _entry_mtime(entry),
            }
            mm = _manual_match(svc, entry.path, "directory")
            child["manual_match"] = mm
            child["manual_scope"] = mm.get("scope") if mm else None
            child["directory_path"] = entry.path
            record = _directory_record(svc, entry.path)
            if record:
                child["last_scrape_time"] = record.get("last_scrape_time")
            else:
                child["last_scrape_time"] = None
            # 目录的视频/弹幕数量需向下递归统计；懒加载列表先返回 null，
            # 由前端仅对当前页可见目录调 /directory_stats 补全
            child["scrape_status"] = (
                _directory_recursive_stats(
                    svc, entry.path, min_danmu_count=min_danmu_count, enable_strm=enable_strm
                )
                if include_child_stats
                else None
            )
            result["children"].append(child)

        for entry in sorted(files, key=lambda e: e.name):
            child = {
                "name": entry.name,
                "path": entry.path,
                "type": "media",
                "children": [],
                "mtime": _entry_mtime(entry),
            }
            file_manual = _manual_match(svc, entry.path, "file")
            if file_manual:
                child["manual_match"] = file_manual
                child["manual_scope"] = file_manual.get("scope")
            else:
                child["manual_match"] = current_dir_manual
                child["manual_scope"] = current_dir_scope
            child["directory_path"] = path
            ass_name = f"{os.path.splitext(entry.name)[0]}.danmu.chs.ass"
            ass_entry = entry_map.get(ass_name)
            if ass_entry is not None:
                try:
                    child["danmu_count"] = _count_danmu(svc, ass_entry.path, ass_entry.stat())
                except OSError:
                    child["danmu_count"] = 0
            else:
                child["danmu_count"] = 0
            result["children"].append(child)

        # 本节点自身的递归统计同样随 include_child_stats 懒加载
        result["scrape_status"] = (
            _directory_recursive_stats(
                svc, path, min_danmu_count=min_danmu_count, enable_strm=enable_strm
            )
            if include_child_stats
            else None
        )
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


def scan_path(svc, path: Optional[str] = None, current_dir: Optional[str] = None,
              configured_path: str = "", min_danmu_count: int = 100,
              enable_strm: bool = True,
              include_child_stats: bool = True) -> ApiResponse:
    if current_dir:
        return scan_subfolder(svc, current_dir, configured_path=configured_path,
                              min_danmu_count=min_danmu_count, enable_strm=enable_strm,
                              include_child_stats=include_child_stats)
    if not path:
        path = configured_path
    if not path:
        return ApiResponse.fail("未配置刮削路径")

    paths = [p.strip() for p in path.split("\n") if p.strip()]
    if not paths:
        return ApiResponse.fail("未提供有效路径")

    if len(paths) > 1:
        result = {
            "name": "根目录",
            "path": "",
            "type": "root",
            "is_root": True,
            "children": [],
        }
        for single_path in paths:
            if os.path.exists(single_path):
                result["children"].append(
                    scan_current_directory(svc, single_path, is_root=False,
                                           min_danmu_count=min_danmu_count,
                                           enable_strm=enable_strm,
                                           include_child_stats=include_child_stats)
                )
        return ApiResponse.ok(data=result)

    single_path = paths[0]
    if not os.path.exists(single_path):
        return ApiResponse.fail(f"路径不存在: {single_path}")
    return ApiResponse.ok(
        data=scan_current_directory(svc, single_path, is_root=True,
                                    min_danmu_count=min_danmu_count,
                                    enable_strm=enable_strm,
                                    include_child_stats=include_child_stats)
    )


def _within_library(child: str, root: str) -> bool:
    """child 等于 root 或位于 root 之下（按绝对路径比较，防止 ../ 与末尾斜杠绕过）"""
    child_abs = os.path.abspath(child)
    root_abs = os.path.abspath(root)
    return child_abs == root_abs or child_abs.startswith(root_abs + os.sep)


def scan_subfolder(svc, subfolder_path: Optional[str] = None,
                   configured_path: str = "", min_danmu_count: int = 100,
                   enable_strm: bool = True,
                   include_child_stats: bool = True) -> ApiResponse:
    if not subfolder_path:
        return ApiResponse.fail("未提供子文件夹路径")
    if not os.path.exists(subfolder_path):
        return ApiResponse.fail("文件夹不存在")
    if not os.path.isdir(subfolder_path):
        return ApiResponse.fail("指定路径不是文件夹")
    roots = [p.strip() for p in configured_path.split("\n") if p.strip()] if configured_path else []
    # 目录浏览只允许媒体库配置范围内（含库根本身），防止“返回上级”越界
    if roots and not any(_within_library(subfolder_path, root) for root in roots):
        return ApiResponse.fail("路径不在媒体库配置范围内")
    is_root = subfolder_path in roots
    data = scan_current_directory(svc, subfolder_path, is_root=is_root,
                                  min_danmu_count=min_danmu_count,
                                  enable_strm=enable_strm,
                                  include_child_stats=include_child_stats)
    return ApiResponse.ok(data=data)


def directory_stats(svc, path: Optional[str] = None,
                    min_danmu_count: int = 100,
                    enable_strm: bool = True) -> ApiResponse:
    """批量获取目录的递归视频/弹幕统计（path 多目录以换行分隔）。

    供目录浏览分页懒加载：仅对当前页可见的目录向下钻取统计。
    不存在/非目录返回全 0，不中断整批请求。
    """
    paths = [p.strip() for p in (path or "").split("\n") if p.strip()]
    if not paths:
        return ApiResponse.fail("缺少目录路径")
    stats: dict[str, dict] = {}
    for single_path in paths:
        if os.path.isdir(single_path):
            stats[single_path] = _directory_recursive_stats(
                svc, single_path, min_danmu_count=min_danmu_count, enable_strm=enable_strm
            )
        else:
            stats[single_path] = {"total_files": 0, "scraped_files": 0}
    return ApiResponse.ok(data={"stats": stats})


def scan_directory_stats(svc, directory_path: Optional[str] = None,
                         min_danmu_count: int = 100, enable_strm: bool = True,
                         persist: bool = True) -> ApiResponse:
    """递归统计并落目录记录；directory_path 为空时扫描全部配置媒体库目录。"""
    if directory_path:
        if not os.path.isdir(directory_path):
            return ApiResponse.fail("目录不存在")
        total_files, scraped_files, dir_stats = _walk_library_stats(
            directory_path, min_danmu_count=min_danmu_count, enable_strm=enable_strm, svc=svc
        )
        if persist and svc is not None and hasattr(svc, "update_directory_record"):
            svc.update_directory_record(
                directory_path,
                {
                    "scrape_status": {
                        "total_files": total_files,
                        "scraped_files": scraped_files,
                    },
                    "stats_updated_at": time.time(),
                    "last_scrape_time": timeutil.now().isoformat(timespec="seconds"),
                },
            )
        return ApiResponse.ok(
            data={
                "directory_path": directory_path,
                "total_files": total_files,
                "scraped_files": scraped_files,
                "dir_stats": dir_stats,
            }
        )

    paths = []
    if svc is not None and hasattr(svc, "_configured_paths"):
        paths = [p for p in svc._configured_paths() if os.path.isdir(p)]
    if not paths:
        return ApiResponse.fail("未配置有效的媒体库路径")

    results: dict[str, dict] = {}
    total_files = 0
    scraped_files = 0
    for p in paths:
        p_total, p_scraped, _ = _walk_library_stats(
            p, min_danmu_count=min_danmu_count, enable_strm=enable_strm, svc=svc
        )
        results[p] = {"total_files": p_total, "scraped_files": p_scraped}
        total_files += p_total
        scraped_files += p_scraped
        if persist and svc is not None and hasattr(svc, "update_directory_record"):
            svc.update_directory_record(
                p,
                {
                    "scrape_status": {"total_files": p_total, "scraped_files": p_scraped},
                    "stats_updated_at": time.time(),
                    "last_scrape_time": timeutil.now().isoformat(timespec="seconds"),
                },
            )

    return ApiResponse.ok(
        data={
            "directory_path": None,
            "libraries": len(paths),
            "total_files": total_files,
            "scraped_files": scraped_files,
            "dir_stats": results,
        }
    )


def _walk_library_stats(directory_path: str, min_danmu_count: int = 100,
                        enable_strm: bool = True, svc=None,
                        max_depth: int = 6) -> tuple[int, int, dict]:
    """递归统计目录下媒体文件总数与已刮削数（限深、跳过隐藏目录）。"""
    total_files = 0
    scraped_files = 0
    dir_stats: dict[str, dict] = {}
    for root, dirs, files in os.walk(directory_path):
        depth = root[len(directory_path):].count(os.sep)
        if depth >= max_depth:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            full = os.path.join(root, file)
            if is_supported_file(full, enable_strm):
                total_files += 1
                ass_file = f"{os.path.splitext(full)[0]}.danmu.chs.ass"
                if os.path.exists(ass_file):
                    if _count_danmu(svc, ass_file) >= min_danmu_count:
                        scraped_files += 1
        dir_stats[root] = {
            "total_files": total_files,
            "scraped_files": scraped_files,
        }
    return total_files, scraped_files, dir_stats


def scan_orphan_subtitles(path: Optional[str] = None, configured_path: str = "") -> ApiResponse:
    if not path:
        path = configured_path
    if not path:
        return ApiResponse.fail("未配置刮削路径")

    paths = [p.strip() for p in path.split("\n") if p.strip()]
    orphan_subtitles = []

    for scan_p in paths:
        if not os.path.exists(scan_p):
            continue
        for root, _, files in os.walk(scan_p):
            # 同目录大小写无关比对（NAS 上 .MP4/.Ass 等大写扩展名也能命中）
            files_lower = {f.lower() for f in files}
            for file in files:
                full_path = os.path.join(root, file)
                classified = _classify_danmu_ass(full_path)
                if classified is None:
                    continue
                companion_kind, companion_base = classified
                companion_exts = (
                    MEDIA_EXTENSIONS if companion_kind == "media" else SUBTITLE_EXTENSIONS
                )
                companion_name = os.path.basename(companion_base).lower()
                has_companion = any(
                    companion_name + ext in files_lower for ext in companion_exts
                )
                if has_companion:
                    continue
                try:
                    st = os.stat(full_path)
                    orphan_subtitles.append(
                        {
                            "path": full_path,
                            "size": st.st_size,
                            "modified_time": timeutil.from_timestamp(st.st_mtime).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                    )
                except OSError:
                    continue

    return ApiResponse.ok(
        data={
            "scanning": False,
            "orphan_subtitles": orphan_subtitles,
            "total_found": len(orphan_subtitles),
            "scan_path": path,
        }
    )


def clean_orphans(paths: list[str]) -> ApiResponse:
    if not paths or not isinstance(paths, list):
        return ApiResponse.fail("请提供要清理的文件路径列表")
    cleaned_count = 0
    failed_count = 0
    cleaned_paths = []
    for file_path in paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_count += 1
                cleaned_paths.append(file_path)
        except OSError:
            failed_count += 1
    return ApiResponse.ok(
        data={
            "cleaned_count": cleaned_count,
            "failed_count": failed_count,
            "cleaned_paths": cleaned_paths,
        }
    )


def clean_subtitles(file_path: Optional[str] = None, directory_path: Optional[str] = None) -> ApiResponse:
    deleted_files = []
    if file_path:
        base_name = os.path.splitext(file_path)[0]
        danmu_file = f"{base_name}.danmu.chs.ass"
        if os.path.exists(danmu_file):
            os.remove(danmu_file)
            deleted_files.append(os.path.basename(danmu_file))
        with_danmu_file = f"{base_name}.chs.withDanmu.ass"
        if os.path.exists(with_danmu_file):
            os.remove(with_danmu_file)
            deleted_files.append(os.path.basename(with_danmu_file))
    elif directory_path:
        try:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.endswith(".danmu.chs.ass") or ".withDanmu.ass" in file:
                        full = os.path.join(root, file)
                        os.remove(full)
                        deleted_files.append(os.path.relpath(full, directory_path))
        except OSError as e:
            return ApiResponse.fail(f"清理目录失败: {e}")
    else:
        return ApiResponse.fail("请提供file_path或directory_path参数")

    if deleted_files:
        return ApiResponse.ok(
            message=f"成功清理 {len(deleted_files)} 个字幕文件",
            data={"deleted": deleted_files},
        )
    return ApiResponse.ok(message="没有可清理的字幕文件")
