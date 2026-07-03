"""Pydantic v2 出参模型。全部 camelCase alias，1:1 对齐 frontend/src/types/index.ts。

约定：DB/内部用 snake_case，序列化时用 alias_generator=to_camel 转 camelCase；
`populate_by_name=True` 允许用字段名或 alias 构造；response 用 by_alias 输出。
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ===== 用户 / 鉴权 =====
class UserOut(CamelModel):
    id: str
    name: str
    role: str
    avatar: str | None = None


class LoginIn(CamelModel):
    username: str
    password: str


class LoginOut(CamelModel):
    token: str
    user: UserOut


# ===== 调性 =====
class ToneOut(CamelModel):
    id: str
    handle: str
    name: str
    desc: str


# ===== 账号风格样本（往期爆款，few-shot 锚）=====
class StyleSampleOut(CamelModel):
    id: str
    tone_id: str
    body: str
    source: str | None = None
    enabled: bool
    created_at: str


class StyleSampleIn(CamelModel):
    body: str
    source: str | None = None


# ===== 变体 =====
class VariantOut(CamelModel):
    id: str
    rank: int
    score: int
    dimensions: dict
    body: str
    soft_flag_sentence: str | None = None
    compliance: str
    soft_flag_count: int | None = None
    ai_score: int
    style_distance: float
    confirmed: bool


class VariantBatchOut(CamelModel):
    tone_id: str
    diversity: float
    variants: list[VariantOut]
    session_id: str | None = None


class NewsContext(CamelModel):
    """引用新闻时随生成一起传入的「事实底稿」——把新闻的结构化素材喂给模型，
    使文案贴合真实事实（数字/标的/角度），而非仅凭标题臆造。M3 富化产物的下游消费。
    出入参共用：入参由前端 camelCase 传入；出参（会话恢复）由 DB 的 snake dict 校验后 camel 输出。
    """

    headline: str
    key_facts: list[str] = []
    tickers: list[str] = []
    angle_hints: list[str] = []


class GenerateIn(CamelModel):
    tone_id: str
    prompt: str
    source_headline: str | None = None  # 引用新闻生成时带上，便于历史展示
    news_context: NewsContext | None = None  # 引用新闻的结构化事实底稿（喂给模型 grounding）


class GenerationSessionOut(CamelModel):
    """一次生成会话（含其变体），供工作台恢复上次生成 + 历史列表。"""

    id: str
    tone_id: str
    prompt: str
    source_headline: str | None = None
    news_context: NewsContext | None = None  # 供恢复会话后「重新生成」仍贴事实
    diversity: float
    created_at: str
    favorite: bool = False
    variants: list[VariantOut]


class SessionUpdateIn(CamelModel):
    favorite: bool


class VariantEditIn(CamelModel):
    body: str


class RegenerateIn(CamelModel):
    prompt: str


# ===== 新闻 =====
class NewsOut(CamelModel):
    id: str
    headline: str
    source: str
    published_at: str
    published_label: str
    freshness: str
    heat: int
    key_facts: list[str]
    tickers: list[str]
    angle_hints: list[str]
    url: str
    label: str


class NewsLabelIn(CamelModel):
    label: str  # none | relevant | irrelevant


# ===== 消耗看板 =====
class KpiOut(CamelModel):
    today_tokens: int
    today_cost: float
    active_users: int
    quota_used_pct: float
    quota_used: str
    quota_total: str
    tokens_trend: float
    cost_trend: float
    users_trend: float


class DailyUsageOut(CamelModel):
    date: str
    model: str
    tokens: int


class TopUserOut(CamelModel):
    rank: int
    name: str
    tokens: int


class UsageDetailOut(CamelModel):
    id: str
    user: str
    time: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    scene: str


class DashboardOut(CamelModel):
    kpi: KpiOut
    daily: list[DailyUsageOut]
    top_users: list[TopUserOut]
    details: list[UsageDetailOut]


# ===== 抓取源 / 配额 =====
class CrawlSourceOut(CamelModel):
    id: str
    name: str
    type: str
    url: str
    frequency: str
    last_crawl: str
    health: str
    enabled: bool


class SourceCreateIn(CamelModel):
    name: str
    type: str  # RSS | 搜索API | Playwright
    url: str
    frequency: str


class SourceUpdateIn(CamelModel):
    """部分更新：仅传入的字段生效（含启用开关 enabled）。"""

    name: str | None = None
    type: str | None = None
    url: str | None = None
    frequency: str | None = None
    enabled: bool | None = None


class QuotaConfigIn(CamelModel):
    per_user_daily: int
    over_threshold_pct: int
    circuit_breaker: bool
    breaker_condition: str
    global_daily: int


class OkOut(CamelModel):
    ok: bool


class QuotaConfigOut(CamelModel):
    per_user_daily: int
    over_threshold_pct: int
    circuit_breaker: bool
    breaker_condition: str
    global_daily: int
    global_used: int
    global_used_pct: float


class UserQuotaOut(CamelModel):
    name: str
    used: int
    total: int
    is_self: bool | None = None


class QuotaOut(CamelModel):
    config: QuotaConfigOut
    users: list[UserQuotaOut]


# ===== 合规自检（内部工具端点）=====
class ComplianceCheckIn(CamelModel):
    text: str


class ComplianceCheckOut(CamelModel):
    status: str  # pass | soft | blocked
    banned_hits: list[str]
    soft_flag_sentence: str | None = None
    soft_flag_count: int
    soft_hits: list[str]
    injection_detected: bool
    injection_patterns: list[str]
    sanitized_text: str


# ===== 行为埋点 / 采用（M7）=====
class TelemetryIn(CamelModel):
    event_type: str
    variant_id: str | None = None
    news_id: str | None = None
    tone_id: str | None = None
    position: int | None = None
    edited_sentences: list[str] | None = None
    meta: dict | None = None


class AckOut(CamelModel):
    ok: bool
    event_id: str


class EventTypeCount(CamelModel):
    event_type: str
    count: int


class VariantAdoptCount(CamelModel):
    variant_id: str
    count: int


class TelemetrySummaryOut(CamelModel):
    total: int
    by_type: list[EventTypeCount]
    top_adopted: list[VariantAdoptCount]


# ===== M1 采集触发结果 =====
class CrawlResultOut(CamelModel):
    ok: bool
    fetched: int
    inserted: int
    skipped: int
    message: str
