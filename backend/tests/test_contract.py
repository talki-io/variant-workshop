"""新闻契约（variant-migration 阶段 1）：summary 持久化 + /api/contract/news 拉取端点。"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import settings
from app.crawl import FeedEntry, ingest_entries, url_fingerprint
from app.db import SessionLocal
from app.main import app
from app.models import News

client = TestClient(app)

_URL_A = "https://contract.test/a"
_URL_B = "https://contract.test/b"


def _cleanup() -> None:
    with SessionLocal() as db:
        for u in (_URL_A, _URL_B):
            row = db.get(News, url_fingerprint(u))
            if row:
                db.delete(row)
        db.commit()


def test_ingest_persists_summary():
    """采集入库应持久化原文 summary（此前只作富化入参、用完即丢）。"""
    _cleanup()
    try:
        e = FeedEntry(title="SAHM naik", link=_URL_A, summary="Ringkasan isi berita.")
        with SessionLocal() as db:
            ingest_entries(db, "src", [e])
        with SessionLocal() as db:
            row = db.get(News, url_fingerprint(_URL_A))
            assert row is not None
            assert row.summary == "Ringkasan isi berita."
            assert row.ingested_at is not None
    finally:
        _cleanup()


def test_contract_token_gate(monkeypatch):
    # 未配置 SERVICE_TOKEN → 503（不是开放，也不是空令牌放行）
    monkeypatch.setattr(settings, "service_token", "")
    assert client.get("/api/contract/news").status_code == 503
    # 配置了但缺/错令牌 → 401
    monkeypatch.setattr(settings, "service_token", "svc-secret")
    assert client.get("/api/contract/news").status_code == 401
    assert client.get("/api/contract/news", headers={"X-Service-Token": "wrong"}).status_code == 401


def test_contract_pulls_incrementally(monkeypatch):
    _cleanup()
    monkeypatch.setattr(settings, "service_token", "svc-secret")
    h = {"X-Service-Token": "svc-secret"}
    # 取一个插入前的时刻做游标，隔离掉库里其它历史新闻。
    before = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    try:
        with SessionLocal() as db:
            ingest_entries(db, "src", [
                FeedEntry(title="berita A", link=_URL_A, summary="isi A"),
                FeedEntry(title="berita B", link=_URL_B, summary="isi B"),
            ])
        r = client.get("/api/contract/news", headers=h, params={"since": before})
        assert r.status_code == 200
        body = r.json()
        by_id = {it["id"]: it for it in body["items"]}
        ia, ib = url_fingerprint(_URL_A), url_fingerprint(_URL_B)
        assert ia in by_id and ib in by_id
        # 出参 camelCase，含 summary + 机器游标 ingestedAt
        assert by_id[ia]["summary"] == "isi A"
        assert "ingestedAt" in by_id[ia] and "publishedAt" in by_id[ia]
        assert body["nextSince"] is not None
        assert body["nextId"] is not None
        # 以复合游标 (nextSince, nextId) 增量再拉：A/B 不重复出现
        r2 = client.get(
            "/api/contract/news",
            headers=h,
            params={"since": body["nextSince"], "sinceId": body["nextId"]},
        )
        ids2 = {it["id"] for it in r2.json()["items"]}
        assert ia not in ids2 and ib not in ids2
    finally:
        _cleanup()


_TIED_URLS = [f"https://contract.test/tied-{i}" for i in range(5)]


def _cleanup_tied() -> None:
    with SessionLocal() as db:
        for u in _TIED_URLS:
            row = db.get(News, url_fingerprint(u))
            if row:
                db.delete(row)
        db.commit()


def test_contract_cursor_does_not_skip_rows_sharing_ingested_at(monkeypatch):
    """同一 ingested_at 的多行跨页时一条都不能丢（复合游标回归测试）。

    这不是假想场景：迁移 0015 给存量行统一盖了 now()，实测 356 行共享同一个时间戳。
    修复前游标只带 ingested_at 且用严格 `>` 比较，第二页会把同刻行整体跳过 ——
    356 行只拉得到前 100 行，其余 256 行永久不可达，而调用方收到的是「成功、0 条新数据」，
    毫无异常迹象。故此处强制 5 行同刻、逐页 limit=2 翻，断言 5 行全部拉到且不重复。
    """
    monkeypatch.setattr(settings, "service_token", "svc-secret")
    h = {"X-Service-Token": "svc-secret"}
    _cleanup_tied()
    try:
        with SessionLocal() as db:
            ingest_entries(db, "src", [
                FeedEntry(title=f"tied {i}", link=u, summary=f"isi {i}")
                for i, u in enumerate(_TIED_URLS)
            ])
            # 强制 5 行 ingested_at 完全相同 —— 复现迁移 0015 的存量行状态
            tied_at = datetime.now(timezone.utc)
            ids = [url_fingerprint(u) for u in _TIED_URLS]
            for nid in ids:
                db.get(News, nid).ingested_at = tied_at
            db.commit()

        since = (tied_at - timedelta(seconds=1)).isoformat()
        since_id = None
        seen: list[str] = []
        for _ in range(10):
            params = {"limit": 2, "since": since}
            if since_id is not None:
                params["sinceId"] = since_id
            body = client.get("/api/contract/news", headers=h, params=params).json()
            if not body["items"]:
                break
            seen.extend(it["id"] for it in body["items"])
            since, since_id = body["nextSince"], body["nextId"]

        for nid in ids:
            assert nid in seen, "同刻行被游标跳过 —— 复合游标失效，见本用例 docstring"
        assert len(seen) == len(set(seen)), "同一行被重复投递"
    finally:
        _cleanup_tied()
