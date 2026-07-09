"""幂等灌假数据。内容与 frontend/src/mocks/* 严格一致（SAHM-X / @akun_demo / 财经源A-C）。

已有数据则跳过（按各表是否为空判断），可安全重复执行。
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    CrawlSource,
    LlmModel,
    ModelConfig,
    QuotaConfig,
    StyleSample,
    Tone,
    User,
    Variant,
)
from .samples_data import HOT_SAMPLES
from .security import hash_password


def _empty(db: Session, model) -> bool:
    return db.scalar(select(func.count()).select_from(model)) == 0


def seed(db: Session) -> None:
    # ---- 用户：两个种子账号，密码均为 demo1234，验证 RBAC ----
    if _empty(db, User):
        db.add_all([
            User(id="u_admin", name="admin", role="admin",
                 password_hash=hash_password("demo1234")),
            User(id="u_editor", name="editor", role="editor",
                 password_hash=hash_password("demo1234")),
        ])

    # ---- 调性 ----
    if _empty(db, Tone):
        db.add_all([
            Tone(id="t1", handle="@akun_demo", name="犀利散户体", desc="短句 · 大量俚语"),
            Tone(id="t2", handle="@value_hunter", name="价值猎手体", desc="长句 · 数据驱动"),
            Tone(id="t3", handle="@macro_view", name="宏观视角体", desc="结构化 · 理性分析"),
            Tone(id="t4", handle="@fun_trader", name="幽默交易体", desc="玩梗 · 轻松口语"),
        ])

    # ---- 新闻 ----
    # 不再灌任何演示新闻。新闻表只由真实抓取（M1：POST /api/sources/{id}/crawl 或定时调度）填充，
    # 绝不用占位/假 URL（曾用 news.example.com 的死链假数据，链接打不开、误导为真抓内容，已移除）。
    # 全新安装时 news 表为空，属预期——跑一次抓取即有真实、可打开的新闻。

    # ---- 变体（t1 批次，含 v2/v4 软提示、v5 blocked）----
    if _empty(db, Variant):
        db.add_all([
            Variant(id="v1", tone_id="t1", rank=1, score=88,
                    dimensions={"hook": "悬念", "structure": "故事", "emotion": "FOMO", "platform": "IG", "cta": "强"},
                    body="SAHM-X diam-diam beli balik saham treasuri sendiri. Pasar belum sadar. Kamu masih tunggu sinyal?",
                    compliance="pass", ai_score=12, style_distance=0.18, confirmed=False),
            Variant(id="v2", tone_id="t1", rank=2, score=84,
                    dimensions={"hook": "对比", "structure": "对比", "emotion": "贪婪", "platform": "IG", "cta": "强"},
                    body="Sementara yang lain kejar rumor, SAHM-X udah catat laba besar. Siap-siap ketinggalan kayak kemarin?",
                    soft_flag_sentence="Siap-siap ketinggalan kayak kemarin?",
                    compliance="soft", soft_flag_count=1, ai_score=18, style_distance=0.24, confirmed=False),
            Variant(id="v3", tone_id="t1", rank=3, score=79,
                    dimensions={"hook": "数字", "structure": "列表", "emotion": "FOMO", "platform": "IG", "cta": "强"},
                    body="3 hal yang bikin SAHM-X bisa meledak minggu ini: 1) Volume naik 2x  2) Akumulasi asing  3) Breakout kunci.",
                    compliance="pass", ai_score=22, style_distance=0.31, confirmed=False),
            Variant(id="v4", tone_id="t1", rank=4, score=73,
                    dimensions={"hook": "反常识", "structure": "观点", "emotion": "怀疑", "platform": "IG", "cta": "中"},
                    body="Katanya SAHM-X biasa aja? Coba lihat chart-nya. Institusi jelas beda pandangan.",
                    soft_flag_sentence="Institusi jelas beda pandangan.",
                    compliance="soft", soft_flag_count=1, ai_score=28, style_distance=0.36, confirmed=False),
            Variant(id="v5", tone_id="t1", rank=5, score=69,
                    dimensions={"hook": "恐惧", "structure": "故事", "emotion": "恐惧", "platform": "IG", "cta": "强"},
                    body="Kalau SAHM-X break sekarang, yang FOMO nanti bukan cuma kamu. Jangan jadi penonton lagi.",
                    compliance="blocked", ai_score=31, style_distance=0.53, confirmed=False),
        ])

    # ---- token_usage：不再灌假数据。看板由真实 token_usage 聚合，明细也读真行。----
    # （真实行来自实际生成/清洗/抓取记账，见 usage.record_usage）

    # ---- 抓取源 ----
    if _empty(db, CrawlSource):
        db.add_all([
            # 真实印尼财经 RSS 源（公开订阅源，RSS-first；DESIGN §3 M1 点名 CNBC ID/Kontan 等）
            CrawlSource(id="s1", name="CNBC Indonesia · 市场", type="RSS", url="https://www.cnbcindonesia.com/market/rss", frequency="每 15 分钟", last_crawl="—", health="ok", enabled=True),
            CrawlSource(id="s2", name="Detik Finance", type="RSS", url="https://finance.detik.com/rss", frequency="每 30 分钟", last_crawl="—", health="ok", enabled=True),
            # IDX：Playwright 渲染实测可抓真实官方新闻（.card-title 结构化抽取）；Cloudflare 偶发拦截会如实置 error，不造假。
            CrawlSource(id="s3", name="IDX 官网 · 新闻（Playwright JS 渲染）", type="Playwright", url="https://www.idx.co.id/en/news/news", frequency="每 60 分钟", last_crawl="—", health="ok", enabled=True),
            # Antara/Investing 为泛经济/国际源，非印尼官方且股票密度低——默认禁用（相关性硬过滤已兜底，
            # 但优先官方/精准源：IDX 官方 + IDNFinancials + CNBC 市场）。需要时可在「抓取源」页手动启用。
            CrawlSource(id="s4", name="Antara · 经济", type="RSS", url="https://www.antaranews.com/rss/ekonomi.xml", frequency="每 2 小时", last_crawl="—", health="ok", enabled=False),
            CrawlSource(id="s5", name="Investing.com · 新闻（国际源）", type="RSS", url="https://www.investing.com/rss/news_25.rss", frequency="每 60 分钟", last_crawl="—", health="ok", enabled=False),
            CrawlSource(id="s6", name="Stockbit 社区（Playwright JS 渲染）", type="Playwright", url="https://stockbit.com/", frequency="每 4 小时", last_crawl="—", health="ok", enabled=False),
            # 印尼 JS 站均被 Cloudflare/IP 信誉拦截（本机出口 IP 无法过挑战），默认禁用；
            # 需印尼住宅/授权出口或官方数据渠道方可启用（业务决策）。Playwright 能力本身已实现并实测可用。
            CrawlSource(id="s7", name="IDNFinancials · 新闻（Playwright JS 渲染）", type="Playwright", url="https://www.idnfinancials.com/news", frequency="每 60 分钟", last_crawl="—", health="ok", enabled=False),
            # 官方/专业精准源（用户点名接入）：Kontan 投资版 RSS（可直抓）+ OJK 官方新闻稿（SharePoint 服务端渲染、非 CF SPA，Playwright 抽 /siaran-pers/Pages 稿件）
            CrawlSource(id="s8", name="Kontan · 投资", type="RSS", url="https://investasi.kontan.co.id/rss", frequency="每 30 分钟", last_crawl="—", health="ok", enabled=True),
            CrawlSource(id="s9", name="OJK · 官方新闻稿（静态抓取）", type="HTML", url="https://www.ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Default.aspx", frequency="每 4 小时", last_crawl="—", health="ok", enabled=True),
        ])

    # ---- 往期爆款样本（账号 t1 的风格锚，few-shot 用）----
    if _empty(db, StyleSample):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.add_all([
            StyleSample(id=f"sm{i + 1}", tone_id="t1", body=body, source=source,
                        enabled=True, created_at=now)
            for i, (source, body) in enumerate(HOT_SAMPLES)
        ])

    # ---- 模型库：默认 3 个 Anthropic 模型（管理员可在「模型管理」页 CRUD 增补其他厂商）----
    if _empty(db, LlmModel):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.add_all([
            LlmModel(id="mdl_haiku", name="Haiku 4.5（快·省）", provider="anthropic",
                     model_id="claude-haiku-4-5", base_url=None, api_key=None, enabled=True, created_at=now),
            LlmModel(id="mdl_sonnet", name="Sonnet 5（均衡·主力）", provider="anthropic",
                     model_id="claude-sonnet-5", base_url=None, api_key=None, enabled=True, created_at=now),
            LlmModel(id="mdl_opus", name="Opus 4.8（最强·贵）", provider="anthropic",
                     model_id="claude-opus-4-8", base_url=None, api_key=None, enabled=True, created_at=now),
        ])

    # ---- 模型配置：各管线场景绑定模型库某模型 + 参数（可在「模型管理」页改）----
    if _empty(db, ModelConfig):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.add_all([
            ModelConfig(scene="generate", label="文案生成", model_id="mdl_sonnet",
                        max_tokens=3600, temperature=None, enabled=True, updated_at=now),
            ModelConfig(scene="clean", label="新闻清洗富化", model_id="mdl_haiku",
                        max_tokens=4000, temperature=None, enabled=True, updated_at=now),
            ModelConfig(scene="compliance", label="语义合规", model_id="mdl_haiku",
                        max_tokens=600, temperature=None, enabled=True, updated_at=now),
        ])

    # ---- 配额 ----
    if _empty(db, QuotaConfig):
        # global_used 基线归零：全局已用只反映真实今日用量（干净起点，不做合成基线）。
        db.add(QuotaConfig(id=1, per_user_daily=20_000, over_threshold_pct=80,
                           circuit_breaker=True, breaker_condition="错误率 ≥ 20% 且持续 5 分钟",
                           global_daily=1_000_000, global_used=0, global_used_pct=0.0))
    # 配额页「按用户」由真实 users + 今日实时用量组装（routers/quota.py），无需灌任何用户配额数据。
    # （旧的 user_quota 假数据表已于迁移 0006 移除。）

    db.commit()
