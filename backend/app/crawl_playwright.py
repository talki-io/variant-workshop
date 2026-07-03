"""M1 采集层（Playwright）—— JS 渲染站抓取，供 RSS 拿不到的动态站兜底。

设计原则：
- **只做合法渲染**：用真实无头 Chromium 正常打开页面、执行页面 JS（含站点自带的 Cloudflare 托管挑战，
  与真人浏览器访问同理）。**不做**指纹伪造 / 打码 / 代理池等"反爬规避"——那属检测规避，
  IDX 是 OJK 监管交易所，需业务/法务明确授权，本模块一律不越线。
- **检测到反爬即如实上报**：命中 Cloudflare/人机验证挑战页 → 返回 blocked + 明确 message，
  绝不返回空数据冒充成功、更不造假新闻。
- 复用 M1 的 FeedEntry / ingest_entries：渲染出的条目走同一条去重+抗注入+M3 富化+相关性回填链路。

纯函数（extract_news_links / is_challenge_page）不依赖浏览器，可离线单测；
真正的浏览器渲染集中在 fetch_playwright，装了 Chromium 才跑。
"""

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .crawl import FeedEntry

_log = logging.getLogger("uvicorn.error")

# 每站抽取配置，两种模式：
#   1) DOM 结构化（含 item/title/link 选择器）：标题不在 <a> 文本里的卡片式列表用之（如 IDX）。
#   2) 锚正则（link_re）：标题就是链接文本的站用之（如 Yahoo Finance / 通用兜底）。
# IDX 的选择器经实地渲染确认：卡片 .bzg_c、标题 .card-title、详情链接 a[href*=/news/news/]。
SITE_CONFIGS: dict[str, dict] = {
    "idx.co.id": {"item": ".bzg_c", "title": ".card-title",
                  "link": "a[href*='/news/news/']", "wait": ".card-title"},
    "idnfinancials.com": {"link_re": r"/news/\d+/", "wait": "a[href*='/news/']"},
    "stockbit.com": {"link_re": r"/(post|symbol)/[^\"']+", "wait": None},
}
_DEFAULT_CONFIG = {"link_re": r"/(news|berita|article|read|post)/[^\"']+", "wait": None}

# 垃圾标题闸：UUID/纯十六进制/空洞 slug（无正常词）一律拒收，杜绝把无意义标题当新闻入库。
_JUNK_RE = re.compile(r"^[0-9a-fA-F][0-9a-fA-F \-]{18,}$")


def _is_junk_title(title: str) -> bool:
    """标题是否为 UUID/十六进制之类的无意义串（非真实新闻标题）。"""
    return bool(_JUNK_RE.match(title.strip()))

# Cloudflare / 通用人机验证挑战页特征（命中即判定被反爬拦截）
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf_chl_opt",
    "challenge-platform",
    "enable javascript and cookies",
    "cf-challenge",
    "/cdn-cgi/challenge-platform",
    "checking your browser",
)

_WS_RE = re.compile(r"\s+")


def config_for(url: str) -> dict:
    host = (urlsplit(url).hostname or "").lower()
    for domain, cfg in SITE_CONFIGS.items():
        if host == domain or host.endswith("." + domain):
            return cfg
    return _DEFAULT_CONFIG


def is_challenge_page(html: str, title: str = "") -> bool:
    """判断渲染结果是否为 Cloudflare/人机验证挑战页（而非真实内容）。"""
    blob = f"{title}\n{html}".lower()
    return any(m in blob for m in _CHALLENGE_MARKERS)


class _AnchorCollector(HTMLParser):
    """收集所有 <a href> 及其可见文本；nested 标签内的文本一并归到当前 <a>。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._href = href
                self._buf = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = _WS_RE.sub(" ", "".join(self._buf)).strip()
            self.anchors.append((self._href, text))
            self._href = None
            self._buf = []


def _title_from_slug(href: str) -> str:
    """锚文本为空时的兜底：从 URL 末段 slug 还原可读标题。"""
    slug = urlsplit(href).path.rstrip("/").rsplit("/", 1)[-1]
    words = re.sub(r"[-_]+", " ", slug).strip()
    return words[:1].upper() + words[1:] if words else ""


def extract_news_links(html: str, base_url: str, link_re: str, max_items: int = 15,
                       min_title_len: int = 12) -> list[FeedEntry]:
    """从渲染后的 HTML 抽取新闻条目（href 匹配 link_re），按出现顺序去重，返回 FeedEntry 列表。"""
    parser = _AnchorCollector()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 —— 容错：畸形 HTML 不致崩
        pass
    pat = re.compile(link_re)
    seen: set[str] = set()
    entries: list[FeedEntry] = []
    for href, text in parser.anchors:
        if not pat.search(href):
            continue
        link = urljoin(base_url, href)
        if link in seen:
            continue
        title = text or _title_from_slug(link)
        if len(title) < min_title_len or _is_junk_title(title):
            continue
        seen.add(link)
        entries.append(FeedEntry(title=title, link=link, published_at=None, summary=""))
        if len(entries) >= max_items:
            break
    return entries


def _extract_dom(page, cfg: dict, base_url: str, max_items: int = 15,
                 min_title_len: int = 12) -> list[FeedEntry]:
    """DOM 结构化抽取：遍历卡片(item)，各取标题(title)+详情链接(link)。标题不在 <a> 内的站用之。"""
    seen: set[str] = set()
    entries: list[FeedEntry] = []
    for card in page.query_selector_all(cfg["item"]):
        t_el = card.query_selector(cfg["title"])
        l_el = card.query_selector(cfg["link"])
        if t_el is None or l_el is None:
            continue
        title = _WS_RE.sub(" ", (t_el.inner_text() or "")).strip()
        href = l_el.get_attribute("href")
        if not href:
            continue
        link = urljoin(base_url, href)
        if link in seen or len(title) < min_title_len or _is_junk_title(title):
            continue
        seen.add(link)
        entries.append(FeedEntry(title=title, link=link, published_at=None, summary=""))
        if len(entries) >= max_items:
            break
    return entries


def fetch_playwright(url: str, timeout: float = 30.0, max_items: int = 15) -> dict:
    """用无头 Chromium 渲染 JS 页面并抽取新闻条目。不做反爬规避。

    返回 {ok, blocked, entries, message}。
    - Playwright/浏览器未安装 → ok=False（不抛，供无浏览器环境优雅降级）。
    - 命中 Cloudflare/人机验证 → ok=False, blocked=True + 明确 message，entries 为空。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "blocked": False, "entries": [],
                "message": "Playwright 未安装（镜像未内置浏览器）"}

    cfg = config_for(url)
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = browser.new_context(
                    user_agent=ua, locale="id-ID", viewport={"width": 1366, "height": 900}
                ).new_page()
                page.set_default_timeout(timeout * 1000)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:  # noqa: BLE001 —— networkidle 超时不致命
                        pass
                except Exception as nav_ex:  # noqa: BLE001 —— goto 超时/中断：仍尝试读现有内容判断是否被挑战挡住
                    try:
                        html, title = page.content(), page.title()
                    except Exception:  # noqa: BLE001
                        raise nav_ex
                    if is_challenge_page(html, title):
                        return {"ok": False, "blocked": True, "entries": [],
                                "message": "被反爬拦截（页面停在 Cloudflare/人机验证挑战，导航未完成）——本抓取器不做规避"}
                    raise

                html, title = page.content(), page.title()
                # 站点自带的 JS 挑战可能需要几秒自动放行——给一次等待+重取，仍是"正常执行页面JS"，非规避
                if is_challenge_page(html, title):
                    page.wait_for_timeout(7000)
                    html, title = page.content(), page.title()
                if is_challenge_page(html, title):
                    return {"ok": False, "blocked": True, "entries": [],
                            "message": "被反爬拦截（Cloudflare/人机验证挑战），未获取真实内容——需业务/法务授权与官方数据渠道，本抓取器不做规避"}

                if cfg.get("wait"):
                    try:
                        page.wait_for_selector(cfg["wait"], timeout=8000)
                        html = page.content()
                    except Exception:  # noqa: BLE001
                        pass

                # DOM 结构化模式（标题不在 <a> 文本里，如 IDX）vs 锚正则模式（标题即链接文本，如 Yahoo）
                if cfg.get("item"):
                    entries = _extract_dom(page, cfg, url, max_items=max_items)
                else:
                    entries = extract_news_links(html, url, cfg["link_re"], max_items=max_items)
                if not entries:
                    return {"ok": True, "blocked": False, "entries": [],
                            "message": "渲染成功但未抽到匹配的新闻链接（选择器/正则可能需按该站结构调整）"}
                return {"ok": True, "blocked": False, "entries": entries, "message": "渲染抓取完成"}
            finally:
                browser.close()
    except Exception as ex:  # noqa: BLE001 —— 渲染/启动失败如实上报，不冒充成功
        _log.warning("Playwright 渲染失败 %s：%s", url, ex)
        return {"ok": False, "blocked": False, "entries": [], "message": f"渲染失败：{type(ex).__name__}: {ex}"}


def fetch_playwright_and_ingest(db, source_name: str, url: str, enrich: bool = False,
                                max_items: int = 15) -> dict:
    """渲染抓取 + 入库（复用 ingest_entries 的去重/抗注入/富化/相关性回填）。

    返回形状对齐 crawl.fetch_and_ingest（ok/fetched/inserted/skipped/enrich_usage/message），
    额外带 blocked 供上层区分"被反爬"与"普通失败"。
    """
    from .crawl import ingest_entries

    fr = fetch_playwright(url, max_items=max_items)
    if not fr["ok"]:
        return {"ok": False, "blocked": fr.get("blocked", False), "fetched": 0, "inserted": 0,
                "skipped": 0, "enrich_usage": [], "message": fr["message"]}
    if not fr["entries"]:
        return {"ok": True, "blocked": False, "fetched": 0, "inserted": 0, "skipped": 0,
                "enrich_usage": [], "message": fr["message"]}
    result = ingest_entries(db, source_name, fr["entries"], enrich=enrich)
    return {"ok": True, "blocked": False, **result, "message": "渲染抓取完成"}
