import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("danmutv.scheduler")


class Scheduler:
    JOB_RETRY = "danmutv_retry"
    JOB_AUTO_SCAN = "danmutv_auto_scan"

    def __init__(self):
        self._scheduler = BackgroundScheduler(daemon=True)
        self._svc = None
        self._config: dict = {}

    def start(self, svc) -> None:
        if self._scheduler.running:
            return
        self._svc = svc
        self._config = svc.get_config()
        self._reload_jobs(self._config)
        self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def reschedule(self, config: dict) -> None:
        self._config = config or {}
        if not self._scheduler.running:
            return
        self._reload_jobs(self._config)

    def _reload_jobs(self, config: dict) -> None:
        self._reschedule_retry(config)
        self._reschedule_auto_scan(config)

    def _reschedule_retry(self, config: dict) -> None:
        existing = self._scheduler.get_job(self.JOB_RETRY)
        if config.get("enable_retry_task", True):
            trigger = IntervalTrigger(minutes=5)
            if existing:
                existing.reschedule(trigger)
            else:
                self._scheduler.add_job(
                    self._safe_process_retry,
                    trigger=trigger,
                    id=self.JOB_RETRY,
                    max_instances=1,
                    coalesce=True,
                    replace_existing=True,
                )
        elif existing:
            existing.remove()

    def _reschedule_auto_scan(self, config: dict) -> None:
        existing = self._scheduler.get_job(self.JOB_AUTO_SCAN)
        if config.get("auto_scrape"):
            interval = int(config.get("auto_scrape_interval", 3600) or 3600)
            if interval < 60:
                interval = 60
            trigger = IntervalTrigger(seconds=interval)
            if existing:
                existing.reschedule(trigger)
            else:
                self._scheduler.add_job(
                    self._safe_auto_scan,
                    trigger=trigger,
                    id=self.JOB_AUTO_SCAN,
                    max_instances=1,
                    coalesce=True,
                    replace_existing=True,
                )
        elif existing:
            existing.remove()

    # ---- job wrappers (no exception must escape) ----
    def _safe_process_retry(self) -> None:
        try:
            if not self._svc:
                return
            cfg = self._svc.get_config()
            if not cfg.get("enable_retry_task", True):
                return
            result = self._svc.process_retry_tasks()
            logger.info(f"定时重试任务完成: {result}")
        except Exception as e:
            logger.exception(f"定时重试任务异常: {e}")

    def _safe_auto_scan(self) -> None:
        try:
            if not self._svc:
                return
            cfg = self._svc.get_config()
            if not cfg.get("auto_scrape"):
                return
            mode = cfg.get("auto_scrape_mode", "incremental")
            logger.info(f"开始定时自动刮削（模式: {mode}）")
            result = self._svc.auto_scrape_configured_paths(mode=mode)
            logger.info(f"定时自动刮削结果: {result}")
        except Exception as e:
            logger.exception(f"定时自动刮削异常: {e}")
