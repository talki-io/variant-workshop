"""SQLAlchemy 模型。字段对齐 frontend/src/types/index.ts（DB 内 snake_case，出参由 schemas 转 camelCase）。

本轮建的是「服务 6 个端点 + 鉴权 + 成本护栏」所需的表；AI 管线表（模式库/语感指纹全字段/
权重表/埋点/golden/禁词）留到下一轮。style_vectors 为 pgvector stub，仅验证扩展可用。
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'editor' | 'admin'
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    # 启用/停用（软删）：停用后不能登录、现存 token 失效，但保留历史与归属。迁移 0013。
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Tone(Base):
    __tablename__ = "tones"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    handle: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    desc: Mapped[str] = mapped_column(String, nullable=False)
    # 归属用户（users.id）。账号与其参考爆款样本按创建者隔离，各用户只管理自己新增的。
    # 存量账号（迁移 0012）回填 u_admin；nullable 仅为兼容历史，新建必写。
    owner_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class News(Base):
    __tablename__ = "news"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    published_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO with +07:00
    published_label: Mapped[str] = mapped_column(String, nullable=False)
    freshness: Mapped[str] = mapped_column(String, nullable=False)  # breaking|recent|old
    heat: Mapped[int] = mapped_column(Integer, nullable=False)
    key_facts: Mapped[list] = mapped_column(JSONB, nullable=False)
    tickers: Mapped[list] = mapped_column(JSONB, nullable=False)
    angle_hints: Mapped[list] = mapped_column(JSONB, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)  # none|relevant|irrelevant
    # ↓ 迁移 0015：新闻契约（Java 拉取 + 富化移交 Java）新增字段
    # 原文摘要（RSS description / content:encoded 清洗后，≤600 字）。富化移交 Java 后，作为其富化输入；
    # 此前该文本仅作富化入参、用完即丢，News 未持久化 → Java 无米下锅，故补此列。
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # 入库时间（机器游标）：Java 增量拉取以此为 watermark，与 published_at（可回填历史时间）解耦。
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tone_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    soft_flag_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance: Mapped[str] = mapped_column(String, nullable=False)  # pass|soft|blocked
    soft_flag_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_score: Mapped[int] = mapped_column(Integer, nullable=False)
    style_distance: Mapped[float] = mapped_column(Float, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 所属生成会话（真实生成时写入；种子/离线库存变体为 NULL，不进历史）
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class GenerationSession(Base):
    """一次「工作台生成」的会话：绑定用户 + 调性 + 需求(prompt) + 新闻来源 + 多样性。

    真实生成时创建一行，产出的变体经 Variant.session_id 归属到本会话。
    前端据此在切模块/刷新后恢复上次生成，并提供历史列表——落地「产出草稿供选改」的持久化。
    """

    __tablename__ = "generation_session"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tone_id: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    source_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # 引用新闻的事实底稿快照（grounding + 重生成复用）
    style_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # 本次临时仿写范本（不入样本库，随会话存供恢复/重生成）
    diversity: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user: Mapped[str] = mapped_column(String, nullable=False)
    time: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    scene: Mapped[str] = mapped_column(String, nullable=False)


class CrawlSource(Base):
    __tablename__ = "crawl_source"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # RSS|搜索API|Playwright
    url: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    last_crawl: Mapped[str] = mapped_column(String, nullable=False)
    health: Mapped[str] = mapped_column(String, nullable=False)  # ok|error
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # E4 条件请求缓存校验器（HTTP ETag / Last-Modified）；命中 304 则跳过解析与富化
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)


class QuotaConfig(Base):
    __tablename__ = "quota_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 单行，固定 1
    per_user_daily: Mapped[int] = mapped_column(Integer, nullable=False)
    over_threshold_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    circuit_breaker: Mapped[bool] = mapped_column(Boolean, nullable=False)
    breaker_condition: Mapped[str] = mapped_column(String, nullable=False)
    global_daily: Mapped[int] = mapped_column(Integer, nullable=False)
    global_used: Mapped[int] = mapped_column(Integer, nullable=False)
    global_used_pct: Mapped[float] = mapped_column(Float, nullable=False)


class TelemetryEvent(Base):
    """行为埋点事件（DESIGN §4 M7 反馈闭环的隐式信号原料）。

    采纳/导出/复制=强正；重新生成/划走=弱负；编辑/展开/停留等=辅助信号。
    position 记曝光位次（P2-5 位置偏差校正用）。下一轮 bandit 权重表消费此表。
    """

    __tablename__ = "telemetry_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    variant_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    news_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tone_id: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edited_sentences: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class StyleVector(Base):
    """pgvector stub：本轮建表不灌，验证 CREATE EXTENSION vector 生效，为下一轮风格向量铺底。"""

    __tablename__ = "style_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tone_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=True)


class LlmModel(Base):
    """模型库：管理员维护的可用模型（多厂商），供各管线场景绑定。

    provider=anthropic 走原生 SDK；provider=openai 走 OpenAI 兼容 /chat/completions（httpx），
    覆盖 OpenAI/DeepSeek/Kimi/Qwen/Gemini(OpenAI端点)/各类中转。base_url 为中转/自定义端点，
    api_key 各模型独立（空则 anthropic 回退 .env 的 ANTHROPIC_API_KEY）。
    """

    __tablename__ = "llm_model"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)  # 展示名
    provider: Mapped[str] = mapped_column(String, nullable=False)  # anthropic | openai
    model_id: Mapped[str] = mapped_column(String, nullable=False)  # 厂商裸模型串
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class ModelConfig(Base):
    """管线场景 → 绑定模型库某模型 + 参数（动态可改，无需改代码）。

    scene 固定为管线阶段（generate/clean/compliance）；model_id 现引用 llm_model.id（模型库主键）；
    max_tokens 该场景主调用上限；temperature 可选（新模型思考态下作用有限，留空则用模型默认）。
    """

    __tablename__ = "model_config"

    scene: Mapped[str] = mapped_column(String, primary_key=True)  # generate | clean | compliance
    label: Mapped[str] = mapped_column(String, nullable=False)  # 中文展示名
    model_id: Mapped[str] = mapped_column(String, nullable=False)  # → llm_model.id
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class StyleSample(Base):
    """账号往期爆款样本：作为该调性/账号的风格锚，生成时抽取若干条做 few-shot 注入。

    这是 DESIGN「离线校准层」的最小可用形态——先用真实爆款做 few-shot 风格参照，
    日后样本充足再升级为语感指纹 / 风格向量（style_vectors）。按 tone_id 归属账号。
    """

    __tablename__ = "style_sample"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tone_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # 爆款正文（原文，含换行）
    source: Mapped[str | None] = mapped_column(String, nullable=True)  # 备注/来源标签
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class MenuItem(Base):
    """数据驱动的侧栏导航项：侧栏与面包屑从本表渲染（迁移 0014）。

    path = 菜单 key = 前端路由（须是代码里已存在的可路由 path，菜单只治理其展示与可见性，
    不能凭空造出可用页面）。icon 为前端图标白名单注册表的键名。visible_roles 决定哪些角色
    在侧栏可见 + 前端可达（真正的数据安全仍靠后端各敏感端点的 require_admin 兜底）。
    locked=true 的核心项（用户/菜单管理）禁止删除，防管理员误配自锁。
    """

    __tablename__ = "menu_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visible_roles: Mapped[list] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
