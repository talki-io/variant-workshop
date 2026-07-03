"""Playwright 抓取的纯函数单测（不依赖浏览器）：挑战页检测 + 新闻链接抽取。

真正的浏览器渲染（fetch_playwright）需镜像内 Chromium，属集成验证，不在此离线跑。
"""

from app.crawl_playwright import (
    config_for,
    extract_news_links,
    is_challenge_page,
)

# 仿 idnfinancials 列表页片段（真实链接形态 /news/<id>/<slug>）
LIST_HTML = """
<html><body>
  <a href="/news/65582/hashim-group-acquires-ift-from-isat">Hashim Group Acquires IFT from ISAT</a>
  <a href="https://www.idnfinancials.com/news/65576/jci-jumps-2-46-as-foreign-investors-buy">JCI jumps 2.46% as foreign investors buy</a>
  <a href="/about">About</a>
  <a href="/news/65576/jci-jumps-2-46-as-foreign-investors-buy">JCI jumps 2.46% as foreign investors buy</a>
  <a href="/news/65563/antam-gold-buyback-price-jumps">short</a>
</body></html>
"""

CF_HTML = """<!DOCTYPE html><html><head><title>Just a moment...</title></head>
<body><div id="challenge-error-text">Enable JavaScript and cookies to continue</div>
<script>window._cf_chl_opt={cRay:'abc'}</script></body></html>"""


def test_detects_cloudflare_challenge():
    assert is_challenge_page(CF_HTML, "Just a moment...") is True
    assert is_challenge_page("<html><body>Berita pasar hari ini</body></html>", "IDX News") is False


def test_extract_dedups_and_resolves_and_filters():
    entries = extract_news_links(LIST_HTML, "https://www.idnfinancials.com/news", r"/news/\d+/")
    links = [e.link for e in entries]
    # 相对→绝对；同一 URL 去重（第 2、4 条同一篇）；/about 不匹配被排除
    assert "https://www.idnfinancials.com/news/65582/hashim-group-acquires-ift-from-isat" in links
    assert links.count("https://www.idnfinancials.com/news/65576/jci-jumps-2-46-as-foreign-investors-buy") == 1
    assert all("/about" not in u for u in links)
    # 标题过短（"short"）被过滤
    assert all(len(e.title) >= 12 for e in entries)


def test_title_fallback_from_slug_when_anchor_empty():
    html = '<a href="/news/999/laba-emiten-naik-tajam-kuartal-ini"></a>'
    entries = extract_news_links(html, "https://www.idnfinancials.com", r"/news/\d+/")
    assert len(entries) == 1
    assert entries[0].title.lower().startswith("laba emiten naik")


def test_config_for_matches_domain_and_falls_back():
    assert config_for("https://www.idnfinancials.com/news")["link_re"] == r"/news/\d+/"
    # IDX 走 DOM 结构化模式（标题在 .card-title，不在 <a> 文本）
    assert config_for("https://sub.idx.co.id/en/news/news")["item"] == ".bzg_c"
    # 未知域用默认配置（锚正则模式）
    assert "link_re" in config_for("https://unknown-site.example/berita")


def test_junk_uuid_titles_are_rejected():
    # 锚文本为空 + slug 是 UUID → 兜底会得到 UUID 串，必须被垃圾闸拦掉，绝不入库
    html = ('<a href="/en/news/news/4f0aee29-9473-f111-b149-dacbee12ffcb?id=1"></a>'
            '<a href="/en/news/news/real-story-emiten-naik">Emiten teknologi melonjak tajam</a>')
    entries = extract_news_links(html, "https://www.idx.co.id", r"/news/news/[^\"']+")
    titles = [e.title for e in entries]
    assert "Emiten teknologi melonjak tajam" in titles
    assert all("4f0aee29" not in t for t in titles)
