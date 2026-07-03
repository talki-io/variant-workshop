from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crawl import fetch_and_ingest
from ..db import get_db
from ..models import CrawlSource
from ..schemas import (
    CrawlResultOut,
    CrawlSourceOut,
    OkOut,
    SourceCreateIn,
    SourceUpdateIn,
)
from ..security import require_admin
from ..usage import RATES, record_usage

router = APIRouter(prefix="/api", tags=["sources"], dependencies=[Depends(require_admin)])

_TYPES = {"RSS", "搜索API", "Playwright"}


@router.get("/sources", response_model=list[CrawlSourceOut])
def get_sources(db: Session = Depends(get_db)) -> list[CrawlSource]:
    return list(db.scalars(select(CrawlSource).order_by(CrawlSource.id)))


@router.post("/sources", response_model=CrawlSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(body: SourceCreateIn, db: Session = Depends(get_db)) -> CrawlSource:
    """新增抓取源落库（admin）。新源默认启用、健康 ok、尚未抓取。"""
    if body.type not in _TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"type 必须是 {sorted(_TYPES)} 之一",
        )
    src = CrawlSource(
        id="s_" + uuid4().hex[:8],
        name=body.name,
        type=body.type,
        url=body.url,
        frequency=body.frequency,
        last_crawl="—",
        health="ok",
        enabled=True,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


@router.put("/sources/{source_id}", response_model=CrawlSourceOut)
def update_source(source_id: str, body: SourceUpdateIn, db: Session = Depends(get_db)) -> CrawlSource:
    """部分更新抓取源（名称/类型/URL/频率/启用开关）（admin）。"""
    src = db.get(CrawlSource, source_id)
    if src is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="抓取源不存在")
    if body.type is not None and body.type not in _TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"type 必须是 {sorted(_TYPES)} 之一",
        )
    for field in ("name", "type", "url", "frequency", "enabled"):
        val = getattr(body, field)
        if val is not None:
            setattr(src, field, val)
    db.commit()
    db.refresh(src)
    return src


@router.delete("/sources/{source_id}", response_model=OkOut)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> OkOut:
    """删除抓取源（admin）。"""
    src = db.get(CrawlSource, source_id)
    if src is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="抓取源不存在")
    db.delete(src)
    db.commit()
    return OkOut(ok=True)


@router.post("/sources/{source_id}/crawl", response_model=CrawlResultOut)
def crawl_source(source_id: str, db: Session = Depends(get_db)) -> CrawlResultOut:
    """立即抓取某源（M1）。RSS 走 httpx 条件请求，Playwright 走无头 Chromium 渲染；同步更新源健康/时间。"""
    src = db.get(CrawlSource, source_id)
    if src is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="抓取源不存在")
    if src.type == "搜索API":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索API 源类型尚未实现（需接入具体搜索服务，属下一轮）",
        )
    enrich = settings.use_real_llm and bool(settings.anthropic_api_key)
    if src.type == "Playwright":
        from ..crawl_playwright import fetch_playwright_and_ingest

        result = fetch_playwright_and_ingest(db, src.name, src.url, enrich=enrich)
    else:  # RSS
        result = fetch_and_ingest(
            db, src.name, src.url, enrich=enrich,
            etag=src.etag, last_modified=src.last_modified,   # E4 条件请求
        )
    src.last_crawl = datetime.now().strftime("%Y-%m-%d %H:%M")
    src.health = "ok" if result["ok"] else "error"
    if result["ok"] and result.get("etag") is not None:
        src.etag = result["etag"]
    if result["ok"] and result.get("last_modified") is not None:
        src.last_modified = result["last_modified"]
    db.commit()
    # 记录 M3 富化（Haiku）真实用量
    for u in result.get("enrich_usage", []):
        rate = RATES["Haiku"]
        cost = round(u["input"] / 1000 * rate["in"] + u["output"] / 1000 * rate["out"], 4)
        record_usage(db, "system", "Haiku", u["input"], u["output"], cost, "新闻摘要")
    return CrawlResultOut(
        ok=result["ok"],
        fetched=result["fetched"],
        inserted=result["inserted"],
        skipped=result["skipped"],
        message=result["message"],
    )
