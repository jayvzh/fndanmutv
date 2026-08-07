from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query

from app.deps import get_service, require_token
from app.models import ApiResponse, ManualMatchRequest
from app.services import scan_service
from app.services.danmu_service import DanmuService

# 免鉴权路由：dashboard 只读状态接口，未登录也可查看
public_router = APIRouter(prefix="/api")

# 需鉴权路由：除 dashboard 状态外的所有操作接口
router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


@public_router.get("/status")
def get_status(svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.get_status())


@public_router.get("/full_status")
def get_full_status(svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.get_full_status())


@router.get("/auth/verify")
def auth_verify():
    return ApiResponse.ok(message="ok")


@router.get("/config")
def get_config(svc: DanmuService = Depends(get_service)):
    # 契约：返回裸 dict
    return svc.get_config()


@router.post("/config")
def post_config(body: dict, svc: DanmuService = Depends(get_service)):
    svc.save_config(body)
    return ApiResponse.ok(message="配置已保存", data=svc.get_config())


@router.get("/generate_danmu")
def generate_danmu(file_path: str = Query(...), svc: DanmuService = Depends(get_service)):
    result = svc.generate_single(file_path)
    if result is None:
        return ApiResponse.fail("弹幕生成失败")
    if isinstance(result, str) and not result.endswith(".ass"):
        return ApiResponse.fail(result)
    ass_file = f"{file_path.rsplit('.', 1)[0]}.danmu.chs.ass"
    import os as _os
    count = svc.count_danmu_lines_cached(ass_file) if _os.path.exists(ass_file) else 0
    if count == 0:
        return ApiResponse.fail("弹幕数量为0 跳过生成")
    return ApiResponse.ok(data={"danmu_count": count, "file_path": file_path})


@router.get("/scrape_directory")
def scrape_directory(
    directory_path: str = Query(...),
    recursive: bool = Query(False),
    force: bool = Query(False, description="全量模式：即使已有弹幕也重新刮削"),
    svc: DanmuService = Depends(get_service),
):
    try:
        data = svc.scrape_directory(directory_path, recursive=recursive, force=force)
        return ApiResponse.ok(data=data)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/abort_scrape")
def abort_scrape(svc: DanmuService = Depends(get_service)):
    if not svc.abort_scrape():
        return ApiResponse.fail("没有正在进行的刮削任务")
    return ApiResponse.ok(message="已发送中止请求")


@router.get("/scan_path")
def scan_path(
    path: Optional[str] = Query(None),
    current_dir: Optional[str] = Query(None),
    svc: DanmuService = Depends(get_service),
):
    return svc.scan_path(path=path, current_dir=current_dir)


@router.get("/scan_subfolder")
def scan_subfolder(subfolder_path: str = Query(...), svc: DanmuService = Depends(get_service)):
    return svc.scan_subfolder(subfolder_path)


@router.get("/scan_directory_stats")
def scan_directory_stats(directory_path: str = Query(...), svc: DanmuService = Depends(get_service)):
    return svc.scan_directory_stats(directory_path)


@router.get("/scan_orphan_subtitles")
def scan_orphan_subtitles(path: Optional[str] = Query(None), svc: DanmuService = Depends(get_service)):
    return svc.scan_orphan_subtitles(path)


@router.post("/clean_orphan_subtitles")
def clean_orphan_subtitles(paths: List[str]):
    return scan_service.clean_orphans(paths)


@router.get("/clean_subtitles")
def clean_subtitles(
    file_path: Optional[str] = Query(None),
    directory_path: Optional[str] = Query(None),
):
    return scan_service.clean_subtitles(file_path=file_path, directory_path=directory_path)


@router.get("/search_danmu")
def search_danmu(
    keyword: str = Query(...),
    type: Optional[str] = Query(None),
    svc: DanmuService = Depends(get_service),
):
    try:
        data = svc.search_danmu(keyword=keyword, media_type=type)
        return ApiResponse.ok(data=data)
    except (ValueError, RuntimeError) as e:
        return ApiResponse.fail(str(e))


@router.post("/manual_match")
def manual_match(req: ManualMatchRequest, svc: DanmuService = Depends(get_service)):
    try:
        data = svc.set_manual_match(req)
        return ApiResponse.ok(message="手动匹配已保存", data=data)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/remove_manual_match")
def remove_manual_match(
    scope: Optional[str] = Query(None),
    file_path: Optional[str] = Query(None),
    directory: Optional[str] = Query(None),
    svc: DanmuService = Depends(get_service),
):
    try:
        data = svc.remove_manual_match(scope=scope, file_path=file_path, directory=directory)
        return ApiResponse.ok(message="已移除", data=data)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/retry_tasks")
def retry_tasks(svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.get_retry_tasks())


@router.get("/process_retry_tasks")
def process_retry_tasks(svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.process_retry_tasks())


@router.get("/clear_retry_tasks")
def clear_retry_tasks(svc: DanmuService = Depends(get_service)):
    count = svc.clear_retry_tasks()
    return ApiResponse.ok(message=f"已清空 {count} 个重试任务")


@router.get("/remove_retry_task")
def remove_retry_task(file_path: str = Query(...), svc: DanmuService = Depends(get_service)):
    if svc.remove_retry_task(file_path):
        return ApiResponse.ok(message=f"已移除: {file_path}")
    return ApiResponse.fail(f"未找到重试任务: {file_path}")


@router.get("/history")
def history(
    page: int = Query(1),
    page_size: int = Query(20),
    include_details: bool = Query(False),
    svc: DanmuService = Depends(get_service),
):
    return ApiResponse.ok(
        data=svc.get_history(page=page, page_size=page_size, include_details=include_details)
    )


@router.post("/clear_history")
def clear_history(svc: DanmuService = Depends(get_service)):
    svc.clear_history()
    return ApiResponse.ok(message="历史记录已清空")


@router.get("/api_status")
def api_status(api_url: Optional[str] = Query(None), svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.check_api_status(api_url))


@router.get("/generate_danmu_with_path")
def generate_danmu_with_path(
    mode: str = Query("incremental", description="incremental=增量跳过已有弹幕，full=全量重新刮削"),
    svc: DanmuService = Depends(get_service),
):
    return ApiResponse.ok(data=svc.auto_scrape_configured_paths(mode=mode))


@router.get("/update_path")
def update_path(path: Optional[str] = Query(None), svc: DanmuService = Depends(get_service)):
    return ApiResponse.ok(data=svc.update_path(path))
