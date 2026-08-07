import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import public_router, router as api_router
from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging
from app.services.danmu_service import DanmuService
from app.services.scheduler import Scheduler

logger = logging.getLogger("danmutv.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings.ensure_data_dir()
    init_db()

    svc = DanmuService()
    scheduler = Scheduler()
    svc.set_scheduler(scheduler)

    app.state.svc = svc
    app.state.scheduler = scheduler
    scheduler.start(svc)

    logger.info("DanmuTV 后端已启动")
    try:
        yield
    finally:
        scheduler.shutdown()
        logger.info("DanmuTV 后端已关闭")


app = FastAPI(title="DanmuTV", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8017",
        "http://127.0.0.1:8017",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(api_router)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


def _register_spa_fallback(fastapi_app: FastAPI, dist_dir: str) -> None:
    dist_path = Path(dist_dir)
    assets = dist_path / "assets"
    if assets.is_dir():
        fastapi_app.mount(
            "/assets",
            StaticFiles(directory=str(assets)),
            name="assets",
        )

    index_file = dist_path / "index.html"
    if not index_file.is_file():
        return

    @fastapi_app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        # 排除 API 路径（API 路由已在前面注册，正常不会到达这里）
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # 静态文件优先：如果 dist 下存在该文件，直接返回
        candidate = dist_path / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(index_file))


_frontend_dist = settings.frontend_dist
if _frontend_dist and Path(_frontend_dist).is_dir():
    _register_spa_fallback(app, _frontend_dist)
else:
    logger.info(f"前端目录 {_frontend_dist} 不存在，跳过静态资源挂载（开发模式）")
