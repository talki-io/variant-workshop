"""M1 采集层（RSS）—— 确定性抓取，无 LLM（富化在 M3）。

二次迭代（2026-07-03）优化点：
- 并发：`fetch_feed` 纯网络+解析、线程安全，供调度器/端点多源并发抓取；DB 写入仍在主线程串行。
- 条件请求：支持 ETag / Last-Modified，命中 304 直接短路（not_modified），零解析零富化。
- 去重：URL 指纹剥离追踪参数（utm_*/fbclid…）与 fragment；批次内叠加标题近重复；入库前批量单查已存在 id。
- 富字段来源：解析 description / content:encoded / summary，喂给 M3 富化 → 精度大升。
- 清洗：标题/摘要 HTML 反转义 + 去标签；按字节 + XML 声明解析，避免印尼语乱码。
- 相关性：M3 富化返回的 relevant 回填 label（relevant/irrelevant），不再恒为 none。

三段结构 parse_feed / ingest_entries / fetch_and_ingest 保留，便于不联网单测。
"""

import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .compliance import sanitize_untrusted
from .models import News

_ATOM = "{http://www.w3.org/2005/Atom}"
_CONTENT_ENCODED = "{http://purl.org/rss/1.0/modules/content/}encoded"
_DC_DATE = "{http://purl.org/dc/elements/1.1/}date"

# 追踪参数：入指纹前剥离，令带 utm/fbclid 的同一篇文章归并为一条
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "mc_cid", "mc_eid",
    "ref", "ref_src", "source", "cmpid", "spm", "yclid", "igshid", "_hsenc", "_hsmi",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w一-鿿]+")


@dataclass
class FeedEntry:
    title: str
    link: str
    published_at: datetime | None = None
    summary: str = ""   # A1：description / content:encoded / atom summary（已清洗）


def _clean_html(s: str) -> str:
    """反转义 HTML 实体 + 去标签 + 折叠空白。RSS 标题/摘要常带 &amp; / <b> / CDATA。"""
    if not s:
        return ""
    s = html.unescape(s)
    s = _TAG_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_date(raw: str) -> datetime | None:
    """稳健解析发布时间：先 RFC822（RSS pubDate），再 ISO8601（Atom/dc:date）。失败返回 None。"""
    if not raw:
        return None
    raw = raw.strip()
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_feed(content: str | bytes) -> list[FeedEntry]:
    """用 feedparser 专业解析 RSS 2.0 / Atom（容错强、自动识别编码/日期/摘要/content:encoded）。

    比手写 xml.etree 更稳：兼容各站非规范 feed、内建日期解析、字段更全。失败返回空列表。
    """
    import feedparser

    d = feedparser.parse(content)  # bytes/str 皆可，内部按 XML 声明识别编码
    entries: list[FeedEntry] = []
    for e in d.entries:
        title = _clean_html(e.get("title", ""))
        link = e.get("link", "")
        # 摘要优先取 content:encoded（正文更全），回退 summary/description；清标签 + 截断控 token
        summary = ""
        if e.get("content"):
            try:
                summary = e["content"][0].get("value", "")
            except (IndexError, AttributeError, TypeError):
                summary = ""
        summary = _clean_html(summary or e.get("summary") or e.get("description") or "")[:600]
        # feedparser 已把日期归一化为 UTC struct_time
        dt = None
        pp = e.get("published_parsed") or e.get("updated_parsed")
        if pp:
            try:
                dt = datetime(*pp[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                dt = None
        if title and link:
            entries.append(FeedEntry(title=title, link=link, published_at=dt, summary=summary))
    return entries


def url_fingerprint(url: str) -> str:
    """URL 指纹：小写 + 去尾斜杠 + 去 fragment + 剥离追踪查询参数，令同一篇不同链接归并。"""
    parts = urlsplit(url.strip())
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in _TRACKING_PARAMS]
    query = urlencode(sorted(kept))
    norm = urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip("/"), query, "")).lower()
    return "n_" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def title_fingerprint(title: str) -> str:
    """标题指纹：小写 + 去标点 + 折叠空白，用于批次内近重复检测（多源转载同一新闻）。"""
    norm = _PUNCT_RE.sub(" ", title.lower())
    norm = _WS_RE.sub(" ", norm).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def _freshness(dt: datetime | None) -> tuple[str, str]:
    """由发布时间推断 freshness + 相对标签（启发式，非 M3 真实热度）。"""
    if dt is None:
        return "old", "未知时间"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hours = (now - dt).total_seconds() / 3600
    if hours < 0:
        hours = 0
    if hours < 2:
        return "breaking", f"{int(hours * 60)} 分钟前"
    if hours < 24:
        return "recent", f"{int(hours)} 小时前"
    return "old", f"{int(hours / 24)} 天前"


def ingest_entries(db: Session, source_name: str, entries: list[FeedEntry], enrich: bool = False) -> dict:
    """去重后写入 news（抗注入清洗）。enrich=True 时用 M3(Haiku) 批量富化热点卡。

    去重三重：批次内 URL 指纹去重 → 批次内标题近重复去重 → 批量单查数据库已存在 id。
    返回计数 + `enrich_usage`（累计 token 用量列表，供上层记账）。
    """
    # 批次内先按 URL 指纹 / 标题指纹去重（多源转载、追踪链接）
    fresh: list[tuple[str, FeedEntry]] = []
    seen_url: set[str] = set()
    seen_title: set[str] = set()
    batch_dupe = 0
    for e in entries:
        nid = url_fingerprint(e.link)
        tfp = title_fingerprint(e.title)
        if nid in seen_url or tfp in seen_title:
            batch_dupe += 1
            continue
        seen_url.add(nid)
        seen_title.add(tfp)
        fresh.append((nid, e))

    # E2：一次查询拿到已存在的 id，替代逐条 db.get
    ids = [nid for nid, _ in fresh]
    existing: set[str] = set(
        db.scalars(select(News.id).where(News.id.in_(ids))).all()
    ) if ids else set()
    to_insert = [(nid, e) for nid, e in fresh if nid not in existing]
    skipped = (len(entries) - len(fresh)) + (len(fresh) - len(to_insert))

    # E3：批量富化——多条一次 Haiku 调用（相关性一并判定）
    enrich_usage: list[dict] = []
    cards: list[dict] = []
    degraded = False  # 富化失败降级：此时不做相关性硬过滤，避免误杀真新闻
    if enrich and to_insert:
        from .pipeline.clean import enrich_batch

        cards, usage = enrich_batch([(e.title, e.summary) for _, e in to_insert])
        degraded = usage is None
        if usage:
            enrich_usage.append(usage)

    _EMPTY = {"relevant": True, "key_facts": [], "tickers": [], "angle_hints": [], "heat": 0}
    filtered_irrelevant = 0
    pending: list[News] = []
    for i, (nid, e) in enumerate(to_insert):
        card = cards[i] if i < len(cards) else _EMPTY
        # —— 相关性硬过滤：正常富化下，判为「与印尼股票无关」的直接不入库 ——
        if enrich and not degraded:
            if not card.get("relevant", True):
                filtered_irrelevant += 1
                continue
            label = "relevant"
        else:
            label = "none"  # 未富化 / 富化降级：保留待人工，不误杀
        pending.append(News(
            id=nid,
            headline=sanitize_untrusted(e.title),   # 外部文本先中和注入片段
            source=source_name,
            published_at=(e.published_at or datetime.now(timezone.utc)).isoformat(),
            published_label=_freshness(e.published_at)[1],
            freshness=_freshness(e.published_at)[0],
            heat=card["heat"],
            key_facts=card["key_facts"],
            tickers=card["tickers"],
            angle_hints=card["angle_hints"],
            url=e.link,
            label=label,
        ))

    # 入库：先试整批提交（快路径）；若与并发抓取撞主键（同源被重复触发），回退逐条插入跳过冲突，
    # 不让一条重复毁掉整批（此前 UniqueViolation 会整批回滚 → inserted=0）。
    for obj in pending:
        db.add(obj)
    try:
        db.commit()
        inserted = len(pending)
    except IntegrityError:
        db.rollback()
        inserted = 0
        for obj in pending:
            try:
                with db.begin_nested():
                    db.add(obj)
                    db.flush()
                inserted += 1
            except IntegrityError:
                pass  # 已存在（并发/重复）→ 跳过
        db.commit()
    # skipped 计入去重 + 相关性过滤；单列 filtered 便于观测过滤强度
    return {
        "fetched": len(entries),
        "inserted": inserted,
        "skipped": skipped + filtered_irrelevant,
        "filtered_irrelevant": filtered_irrelevant,
        "enrich_usage": enrich_usage,
    }


def fetch_feed(
    url: str, timeout: float = 12.0, etag: str | None = None,
    last_modified: str | None = None, max_items: int = 15, retries: int = 2,
) -> dict:
    """纯网络抓取 + 解析（无 DB，线程安全，供并发调用）。

    E4：带 If-None-Match / If-Modified-Since，命中 304 返回 not_modified=True。
    E5：对连接错误/5xx 做有限重试。返回 {ok, not_modified, entries, etag, last_modified, message}。
    """
    headers = {"User-Agent": "Mozilla/5.0 variant-workshop-crawler/0.2"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=headers)
            if resp.status_code == 304:
                return {"ok": True, "not_modified": True, "entries": [],
                        "etag": etag, "last_modified": last_modified, "message": "内容未变（304）"}
            resp.raise_for_status()
            entries = parse_feed(resp.content)[:max_items]   # A6：按字节解析
            return {
                "ok": True, "not_modified": False, "entries": entries,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "message": "抓取完成",
            }
        except httpx.HTTPStatusError as ex:
            # 4xx 不重试；5xx 才重试
            if ex.response.status_code < 500 or attempt == retries:
                last_err = ex
                break
            last_err = ex
        except httpx.HTTPError as ex:
            last_err = ex
            if attempt == retries:
                break
    return {"ok": False, "not_modified": False, "entries": [],
            "etag": etag, "last_modified": last_modified, "message": f"抓取失败：{last_err}"}


def fetch_and_ingest(
    db: Session, source_name: str, url: str, timeout: float = 12.0, enrich: bool = False,
    max_items: int = 15, etag: str | None = None, last_modified: str | None = None,
) -> dict:
    """联网抓取单个 RSS 源并入库。网络/解析失败返回 ok=False + message，不抛出。

    透传 etag/last_modified 以支持条件请求；命中 304 时 fetched=0、返回新的（沿用旧）etag。
    """
    fr = fetch_feed(url, timeout=timeout, etag=etag, last_modified=last_modified, max_items=max_items)
    if not fr["ok"]:
        return {"ok": False, "fetched": 0, "inserted": 0, "skipped": 0, "enrich_usage": [],
                "etag": fr["etag"], "last_modified": fr["last_modified"], "message": fr["message"]}
    if fr["not_modified"]:
        return {"ok": True, "fetched": 0, "inserted": 0, "skipped": 0, "enrich_usage": [],
                "etag": fr["etag"], "last_modified": fr["last_modified"], "message": fr["message"]}
    result = ingest_entries(db, source_name, fr["entries"], enrich=enrich)
    return {"ok": True, **result, "etag": fr["etag"], "last_modified": fr["last_modified"],
            "message": "抓取完成"}


def fetch_and_ingest_many(
    db: Session, sources: list, timeout: float = 12.0, enrich: bool = False,
    max_items: int = 15, max_workers: int = 6,
) -> dict[str, dict]:
    """E1：多源并发抓取。网络段（fetch_feed）走线程池并发，入库段在主线程串行（DB 会话线程安全）。

    sources: 具备 id/name/url/etag/last_modified 属性的对象列表（CrawlSource）。
    返回 {source_id: result}，result 含 ok/fetched/inserted/skipped/enrich_usage/etag/last_modified/message。
    """
    if not sources:
        return {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(sources))) as pool:
        fetched = list(pool.map(
            lambda s: (s, fetch_feed(
                s.url, timeout=timeout,
                etag=getattr(s, "etag", None), last_modified=getattr(s, "last_modified", None),
                max_items=max_items,
            )),
            sources,
        ))

    results: dict[str, dict] = {}
    for s, fr in fetched:
        if not fr["ok"]:
            results[s.id] = {"ok": False, "fetched": 0, "inserted": 0, "skipped": 0,
                             "enrich_usage": [], "etag": fr["etag"],
                             "last_modified": fr["last_modified"], "message": fr["message"]}
            continue
        if fr["not_modified"]:
            results[s.id] = {"ok": True, "fetched": 0, "inserted": 0, "skipped": 0,
                             "enrich_usage": [], "etag": fr["etag"],
                             "last_modified": fr["last_modified"], "message": fr["message"]}
            continue
        r = ingest_entries(db, s.name, fr["entries"], enrich=enrich)
        results[s.id] = {"ok": True, **r, "etag": fr["etag"],
                         "last_modified": fr["last_modified"], "message": "抓取完成"}
    return results
