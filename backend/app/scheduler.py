"""M1 采集定时调度（默认关闭，crawl_scheduler_enabled=True 时启用）。

定时抓取所有「启用的 RSS 源」；真实 LLM 开启时顺带 M3 富化。多实例部署应改用集中式调度，避免重复抓取。
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from .config import settings
from .crawl import fetch_and_ingest_many
from .db import SessionLocal
from .models import CrawlSource
from .usage import RATES, record_usage

_log = logging.getLogger("uvicorn.error")
_scheduler: BackgroundScheduler | None = None


def _record_enrich(db, usages: list[dict]) -> None:
    for u in usages:
        rate = RATES["Haiku"]
        cost = round(u["input"] / 1000 * rate["in"] + u["output"] / 1000 * rate["out"], 4)
        record_usage(db, "system", "Haiku", u["input"], u["output"], cost, "新闻摘要")


def _crawl_enabled_rss() -> None:
    enrich = settings.use_real_llm and bool(settings.anthropic_api_key)
    with SessionLocal() as db:
        # ---- RSS：多源并发（网络段线程池并行，入库段主线程串行）----
        rss = list(
            db.scalars(select(CrawlSource).where(CrawlSource.type == "RSS", CrawlSource.enabled.is_(True)))
        )
        results = fetch_and_ingest_many(db, rss, enrich=enrich)
        for s in rss:
            r = results.get(s.id)
            if r is None:
                continue
            s.last_crawl = datetime.now().strftime("%Y-%m-%d %H:%M")
            s.health = "ok" if r["ok"] else "error"
            if r["ok"] and r.get("etag") is not None:
                s.etag = r["etag"]
            if r["ok"] and r.get("last_modified") is not None:
                s.last_modified = r["last_modified"]
            _record_enrich(db, r.get("enrich_usage", []))
            _log.info("定时抓取 %s：%s", s.name, r.get("message"))

        # ---- Playwright：无头浏览器逐个渲染（重、单浏览器实例，串行）----
        pw = list(
            db.scalars(select(CrawlSource).where(CrawlSource.type == "Playwright", CrawlSource.enabled.is_(True)))
        )
        if pw:
            from .crawl_playwright import fetch_playwright_and_ingest

            for s in pw:
                try:
                    r = fetch_playwright_and_ingest(db, s.name, s.url, enrich=enrich)
                except Exception as ex:  # noqa: BLE001
                    s.health = "error"
                    _log.warning("定时渲染抓取 %s 失败：%s", s.name, ex)
                    continue
                s.last_crawl = datetime.now().strftime("%Y-%m-%d %H:%M")
                s.health = "ok" if r["ok"] else "error"
                _record_enrich(db, r.get("enrich_usage", []))
                _log.info("定时渲染抓取 %s：%s", s.name, r.get("message"))
        db.commit()


def start_scheduler(interval_minutes: int = 15) -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # next_run_time=now：启动后立刻先抓一轮，而非等满一个 interval 才首次执行
    _scheduler.add_job(
        _crawl_enabled_rss, "interval", minutes=interval_minutes,
        id="rss_crawl", next_run_time=datetime.now(), max_instances=1, coalesce=True,
    )
    _scheduler.start()
    _log.info("定时抓取已启用（每 %d 分钟，启动即抓一轮）", interval_minutes)
