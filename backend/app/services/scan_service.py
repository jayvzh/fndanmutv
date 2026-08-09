import os
from typing import Any, Optional

from app.models import ApiResponse
from app import timeutil

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m4v", ".strm"}


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


def scan_current_directory(svc, path: str, is_root: bool = False,
                           min_danmu_count: int = 100,
                           enable_strm: bool = True) -> dict:
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
            child["scrape_status"] = _directory_recursive_stats(
                svc, entry.path, min_danmu_count=min_danmu_count, enable_strm=enable_strm
            )
            result["children"].append(child)

        for entry in sorted(files, key=lambda e: e.name):
            child = {
                "name": entry.name,
                "path": entry.path,
                "type": "media",
                "children": [],
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

        result["scrape_status"] = _directory_recursive_stats(
            svc, path, min_danmu_count=min_danmu_count, enable_strm=enable_strm
        )
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


def scan_path(svc, path: Optional[str] = None, current_dir: Optional[str] = None,
              configured_path: str = "", min_danmu_count: int = 100,
              enable_strm: bool = True) -> ApiResponse:
    if current_dir:
        return scan_subfolder(svc, current_dir, configured_path=configured_path,
                              min_danmu_count=min_danmu_count, enable_strm=enable_strm)
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
                                           enable_strm=enable_strm)
                )
        return ApiResponse.ok(data=result)

    single_path = paths[0]
    if not os.path.exists(single_path):
        return ApiResponse.fail(f"路径不存在: {single_path}")
    return ApiResponse.ok(
        data=scan_current_directory(svc, single_path, is_root=True,
                                    min_danmu_count=min_danmu_count,
                                    enable_strm=enable_strm)
    )


def scan_subfolder(svc, subfolder_path: Optional[str] = None,
                   configured_path: str = "", min_danmu_count: int = 100,
                   enable_strm: bool = True) -> ApiResponse:
    if not subfolder_path:
        return ApiResponse.fail("未提供子文件夹路径")
    if not os.path.exists(subfolder_path):
        return ApiResponse.fail("文件夹不存在")
    if not os.path.isdir(subfolder_path):
        return ApiResponse.fail("指定路径不是文件夹")
    is_root = False
    if configured_path:
        roots = [p.strip() for p in configured_path.split("\n") if p.strip()]
        is_root = subfolder_path in roots
    data = scan_current_directory(svc, subfolder_path, is_root=is_root,
                                  min_danmu_count=min_danmu_count,
                                  enable_strm=enable_strm)
    return ApiResponse.ok(data=data)


def scan_directory_stats(svc, directory_path: Optional[str] = None,
                         min_danmu_count: int = 100, enable_strm: bool = True,
                         persist: bool = True) -> ApiResponse:
    if not directory_path:
        return ApiResponse.fail("缺少目录路径")
    if not os.path.isdir(directory_path):
        return ApiResponse.fail("目录不存在")

    total_files = 0
    scraped_files = 0
    dir_stats: dict[str, dict] = {}
    max_depth = 6

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

    if persist and svc is not None and hasattr(svc, "update_directory_record"):
        svc.update_directory_record(
            directory_path,
            {
                "scrape_status": {
                    "total_files": total_files,
                    "scraped_files": scraped_files,
                },
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


def scan_orphan_subtitles(path: Optional[str] = None, configured_path: str = "") -> ApiResponse:
    if not path:
        path = configured_path
    if not path:
        return ApiResponse.fail("未配置刮削路径")

    paths = [p.strip() for p in path.split("\n") if p.strip()]
    orphan_subtitles = []
    media_extensions = {".mp4", ".mkv", ".strm"}

    for scan_p in paths:
        if not os.path.exists(scan_p):
            continue
        for root, _, files in os.walk(scan_p):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() != ".ass":
                    continue
                if "danmu" not in file.lower():
                    continue
                full_path = os.path.join(root, file)
                base_name = (
                    os.path.splitext(full_path)[0]
                    .replace(".danmu.chs", "")
                    .replace(".danmu", "")
                )
                has_media = any(os.path.exists(base_name + m) for m in media_extensions)
                if not has_media:
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
