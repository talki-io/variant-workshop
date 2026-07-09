"""M1 采集层（静态 HTML）—— 服务端渲染站用 httpx + BeautifulSoup 直接抽取，无需浏览器。

比 Playwright 稳得多：不启动 Chromium、不等渲染、无选择器超时；对 OJK 这类 SSR 站是正解。
仅抓公开列表页的标题+链接，走与 RSS/Playwright 同一条 ingest（去重/抗注入/M3 富化/相关性过滤）。
命中 Cloudflare/人机验证挑战即如实上报 blocked，绝不做规避、绝不造假。
"""

import logging
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .crawl import FeedEntry, ingest_entries
from .crawl_playwright import _is_junk_title, is_challenge_page

_log = logging.getLogger("uvicorn.error")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# 每站列表页的「新闻链接」CSS 选择器；未配则用通用兜底（含常见新闻路径的 <a>）。
HTML_CONFIGS: dict[str, dict] = {
    # OJK 官方新闻稿：稿件路径 /siaran-pers/Pages/<标题-slug>.aspx，标题即锚文本
    "ojk.go.id": {"link_sel": "a[href*='/siaran-pers/Pages/']"},
}
_DEFAULT_SEL = (
    "a[href*='/news/'], a[href*='/berita/'], a[href*='/read/'], "
    "a[href*='/article/'], a[href*='/artikel/']"
)


def html_config_for(url: str) -> dict:
    host = (urlsplit(url).hostname or "").lower()
    for domain, cfg in HTML_CONFIGS.items():
        if host == domain or host.endswith("." + domain):
            return cfg
    return {"link_sel": _DEFAULT_SEL}


def fetch_html(url: str, timeout: float = 20.0, max_items: int = 15) -> dict:
    """httpx 拉静态 HTML + bs4 按选择器抽新闻列表。返回 {ok, blocked, entries, message}。"""
    cfg = html_config_for(url)
    try:
        r = httpx.get(url, headers={"User-Agent": _UA}, timeout=timeout, follow_redirects=True)
    except Exception as ex:  # noqa: BLE001 —— 网络失败如实上报
        return {"ok": False, "blocked": False, "entries": [], "message": f"抓取失败：{type(ex).__name__}: {ex}"}
    if r.status_code != 200:
        blocked = is_challenge_page(r.text) or r.status_code in (403, 503)
        return {"ok": False, "blocked": blocked, "entries": [],
                "message": f"HTTP {r.status_code}" + ("（疑似 Cloudflare/WAF 拦截，本抓取器不做规避）" if blocked else "")}
    if is_challenge_page(r.text):
        return {"ok": False, "blocked": True, "entries": [],
                "message": "被反爬拦截（Cloudflare/人机验证挑战），未获真实内容——本抓取器不做规避"}

    soup = BeautifulSoup(r.text, "lxml")
    seen: set[str] = set()
    entries: list[FeedEntry] = []
    for a in soup.select(cfg["link_sel"]):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not href or len(title) < 12 or _is_junk_title(title):
            continue
        link = urljoin(url, href)
        if link in seen:
            continue
        seen.add(link)
        entries.append(FeedEntry(title=title, link=link, published_at=None, summary=""))
        if len(entries) >= max_items:
            break
    if not entries:
        return {"ok": True, "blocked": False, "entries": [],
                "message": "抓取成功但未匹配到新闻链接（选择器可能需按该站结构调整）"}
    return {"ok": True, "blocked": False, "entries": entries, "message": "静态抓取完成"}


def fetch_html_and_ingest(db, source_name: str, url: str, enrich: bool = False, max_items: int = 15) -> dict:
    """静态抓取 + 入库（复用 ingest 的去重/抗注入/富化/相关性硬过滤）。形状对齐 crawl.fetch_and_ingest。"""
    fr = fetch_html(url, max_items=max_items)
    if not fr["ok"]:
        return {"ok": False, "blocked": fr.get("blocked", False), "fetched": 0, "inserted": 0,
                "skipped": 0, "enrich_usage": [], "message": fr["message"]}
    if not fr["entries"]:
        return {"ok": True, "blocked": False, "fetched": 0, "inserted": 0, "skipped": 0,
                "enrich_usage": [], "message": fr["message"]}
    result = ingest_entries(db, source_name, fr["entries"], enrich=enrich)
    return {"ok": True, "blocked": False, **result, "message": "静态抓取完成"}
