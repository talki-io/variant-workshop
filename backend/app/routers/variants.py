from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..breaker import breaker
from ..compliance import merge_status, scan_compliance, semantic_check_batch
from ..config import settings
from ..db import get_db
from ..models import GenerationSession, QuotaConfig, StyleSample, Tone, User, Variant
from ..schemas import (
    AckOut,
    GenerateIn,
    GenerationSessionOut,
    OkOut,
    RegenerateIn,
    SessionUpdateIn,
    VariantBatchOut,
    VariantEditIn,
    VariantOut,
)
from ..security import get_current_user
from ..telemetry import record_event
from ..usage import estimate_tokens, global_tokens_today, record_usage, user_tokens_today

router = APIRouter(prefix="/api", tags=["variants"])

FIXED_DIVERSITY = 0.72
GEN_MODEL = "Sonnet"  # DESIGN：生成走 Sonnet / Opus，快线走 Sonnet

# LLM 模型 ID → (记账标签, RATES 键)
_MODEL_LABEL = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus"}


_FEWSHOT_MAX = 4  # 生成时注入的爆款样本条数上限（与 pipeline 一致）


_ADHOC_MAX = 3  # 临时仿写范本最多取几段
_FEWSHOT_TOTAL = 6  # few-shot 总量上限（控 token）


def _load_samples(db: Session, tone_id: str) -> list[str]:
    """取某账号启用中的爆款样本正文（做 few-shot 风格锚），最多 _FEWSHOT_MAX 条，最早在前保稳定。"""
    return list(
        db.scalars(
            select(StyleSample.body)
            .where(StyleSample.tone_id == tone_id, StyleSample.enabled.is_(True))
            .order_by(StyleSample.created_at, StyleSample.id)
            .limit(_FEWSHOT_MAX)
        )
    )


def _fewshot_for(db: Session, tone_id: str, style_refs: list[str] | None) -> list[str]:
    """合并 few-shot 风格锚：本次临时仿写范本（优先）+ 账号已有爆款样本，总量截断控 token。"""
    ad_hoc = [s.strip() for s in (style_refs or []) if s and s.strip()][:_ADHOC_MAX]
    return (ad_hoc + _load_samples(db, tone_id))[:_FEWSHOT_TOTAL]


def _label(model_id: str) -> str:
    for key, label in _MODEL_LABEL.items():
        if key in model_id:
            return label
    return "Sonnet"


def _record_llm_usage(db: Session, user_name: str, usages: list[dict]) -> None:
    """把管线各次调用的真实用量按模型聚合，写入 token_usage。"""
    from collections import defaultdict

    from ..usage import RATES

    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for u in usages:
        label = _label(u["model"])
        agg[label][0] += u["input"]
        agg[label][1] += u["output"]
    for label, (ti, to) in agg.items():
        rate = RATES.get(label, RATES["Sonnet"])
        cost = round(ti / 1000 * rate["in"] + to / 1000 * rate["out"], 4)
        scene = "合规分类" if label == "Haiku" else "文案生成"
        record_usage(db, user_name, label, ti, to, cost, scene)


@router.post("/variants", response_model=VariantBatchOut)
def generate_variants(
    body: GenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VariantBatchOut:
    tone = db.get(Tone, body.tone_id)
    if tone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="调性不存在")

    cfg = db.get(QuotaConfig, 1)

    # —— 成本护栏（§6）——
    if cfg and cfg.circuit_breaker and breaker.is_open():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="生成服务已熔断（近期错误率过高），请稍后重试",
        )

    real = settings.use_real_llm and bool(settings.anthropic_api_key)

    # 配额预检：用固定估算（真实路径出参未知，按 5 条中等长度估）。
    est_in, est_out, _ = estimate_tokens(body.prompt, ["x" * 200] * 5, GEN_MODEL)
    if cfg:
        used = user_tokens_today(db, user.name)
        if used + est_in + est_out > cfg.per_user_daily:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"今日 token 配额已用尽（{used}/{cfg.per_user_daily}），请明日再试或联系管理员提额",
            )
        if cfg.global_used + global_tokens_today(db) + est_in + est_out > cfg.global_daily:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="全局日预算已用尽，请稍后再试")

    if real:
        # —— 真实生成路径（M5 + M6）——
        from ..pipeline.generate import generate_variants as run_pipeline

        tone_dict = {"id": tone.id, "handle": tone.handle, "name": tone.name, "desc": tone.desc}
        news_ctx = body.news_context.model_dump() if body.news_context else None
        style_refs = [s.strip() for s in (body.style_refs or []) if s and s.strip()][:_ADHOC_MAX] or None
        samples = _fewshot_for(db, tone.id, style_refs)
        try:
            batch, usages = run_pipeline(tone_dict, body.prompt, news=news_ctx, samples=samples)
        except Exception as ex:  # noqa: BLE001
            breaker.record(False)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=f"生成失败：{type(ex).__name__}"
            ) from ex
        breaker.record(True)
        _record_llm_usage(db, user.name, usages)
        # 持久化为一次「生成会话」：会话行 + 归属变体，供切模块/刷新后恢复 + 历史列表
        from datetime import datetime
        from uuid import uuid4

        session = GenerationSession(
            id="gs_" + uuid4().hex[:12],
            user=user.name,
            tone_id=tone.id,
            prompt=body.prompt,
            source_headline=body.source_headline,
            news_context=news_ctx,
            style_refs=style_refs,
            diversity=batch["diversity"],
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.add(session)
        for v in batch["variants"]:
            v["id"] = "g_" + uuid4().hex[:12]
            db.add(Variant(
                id=v["id"], tone_id=tone.id, rank=v["rank"], score=v["score"],
                dimensions=v["dimensions"], body=v["body"], soft_flag_sentence=v.get("softFlagSentence"),
                compliance=v["compliance"], soft_flag_count=v.get("softFlagCount"),
                ai_score=v["aiScore"], style_distance=v["styleDistance"], confirmed=False,
                session_id=session.id,
            ))
        db.commit()
        batch["sessionId"] = session.id
        return VariantBatchOut.model_validate(batch)

    # —— 灌库固定批次（无 key / 未开启真实生成）——
    rows = list(db.scalars(select(Variant).where(Variant.tone_id == body.tone_id).order_by(Variant.rank)))
    if not rows:
        rows = list(db.scalars(select(Variant).where(Variant.tone_id == "t1").order_by(Variant.rank)))
    est_in, est_out, cost = estimate_tokens(body.prompt, [v.body for v in rows], GEN_MODEL)
    record_usage(db, user.name, GEN_MODEL, est_in, est_out, cost, "文案生成")
    breaker.record(True)
    variants = [VariantOut.model_validate(v, from_attributes=True) for v in rows]
    return VariantBatchOut(tone_id=body.tone_id, diversity=FIXED_DIVERSITY, variants=variants)


def _session_out(db: Session, s: GenerationSession) -> GenerationSessionOut:
    vs = list(db.scalars(select(Variant).where(Variant.session_id == s.id).order_by(Variant.rank)))
    return GenerationSessionOut(
        id=s.id,
        tone_id=s.tone_id,
        prompt=s.prompt,
        source_headline=s.source_headline,
        news_context=s.news_context,
        style_refs=s.style_refs,
        diversity=s.diversity,
        created_at=s.created_at,
        favorite=s.favorite,
        variants=[VariantOut.model_validate(v, from_attributes=True) for v in vs],
    )


@router.get("/variants/sessions", response_model=list[GenerationSessionOut])
def list_sessions(
    limit: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[GenerationSessionOut]:
    """当前用户最近的生成会话（含变体；收藏优先、其后按最新在前），供工作台恢复上次生成 + 历史。"""
    limit = max(1, min(limit, 100))
    sessions = db.scalars(
        select(GenerationSession)
        .where(GenerationSession.user == user.name)
        .order_by(
            GenerationSession.favorite.desc(),
            GenerationSession.created_at.desc(),
            GenerationSession.id.desc(),
        )
        .limit(limit)
    )
    return [_session_out(db, s) for s in sessions]


def _owned_session(db: Session, session_id: str, user: User) -> GenerationSession:
    s = db.get(GenerationSession, session_id)
    if s is None or s.user != user.name:  # 不泄露他人会话是否存在
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="生成会话不存在")
    return s


@router.patch("/variants/sessions/{session_id}", response_model=GenerationSessionOut)
def update_session(
    session_id: str,
    body: SessionUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationSessionOut:
    """收藏 / 取消收藏某会话（仅本人）。"""
    s = _owned_session(db, session_id, user)
    s.favorite = body.favorite
    db.commit()
    db.refresh(s)
    return _session_out(db, s)


@router.delete("/variants/sessions/{session_id}", response_model=OkOut)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OkOut:
    """删除某会话及其变体（仅本人）。"""
    s = _owned_session(db, session_id, user)
    for v in db.scalars(select(Variant).where(Variant.session_id == session_id)):
        db.delete(v)
    db.delete(s)
    db.commit()
    return OkOut(ok=True)


@router.post("/variants/{variant_id}/confirm", response_model=AckOut)
def confirm_variant(
    variant_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AckOut:
    """采用某变体 —— 记一条强正埋点（adopt）。M7 最重要的正信号。"""
    v = db.get(Variant, variant_id)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="变体不存在")
    ev = record_event(db, user=user.name, event_type="adopt", variant_id=variant_id, tone_id=v.tone_id, position=v.rank)
    return AckOut(ok=True, event_id=ev.id)


def _recheck_compliance(body: str) -> tuple[str, str | None, int | None]:
    """编辑后重跑合规：规则层必跑；真实模式下补语义层。返回 (status, softFlagSentence, softFlagCount)。"""
    rules = scan_compliance(body)
    status = rules.status
    if settings.use_real_llm and settings.anthropic_api_key:
        sem, _ = semantic_check_batch([body])
        if sem:
            status = merge_status(rules.status, sem[0]["status"])
    soft_sentence = rules.soft_flag_sentence if status == "soft" else None
    soft_count = (rules.soft_flag_count or None) if status == "soft" else None
    return status, soft_sentence, soft_count


@router.patch("/variants/{variant_id}", response_model=VariantOut)
def edit_variant(
    variant_id: str,
    body: VariantEditIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Variant:
    """编辑变体正文并重跑合规（M6）。落库 + 记 edit 埋点（采用前编辑是弱信号）。"""
    v = db.get(Variant, variant_id)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="变体不存在")
    new_body = body.body.strip()
    if not new_body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="正文不能为空")

    compliance, soft_sentence, soft_count = _recheck_compliance(new_body)
    v.body = new_body
    v.compliance = compliance
    v.soft_flag_sentence = soft_sentence
    v.soft_flag_count = soft_count
    v.confirmed = False  # 编辑后需重新采用
    record_event(
        db, user=user.name, event_type="edit", variant_id=variant_id,
        tone_id=v.tone_id, edited_sentences=[new_body],
    )
    db.refresh(v)
    return v


@router.post("/variants/{variant_id}/regenerate", response_model=VariantOut)
def regenerate_variant(
    variant_id: str,
    body: RegenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Variant:
    """按该变体维度重新生成正文（原地替换，保 id/rank/维度）。过熔断/配额护栏，记 regenerate 弱负埋点。"""
    v = db.get(Variant, variant_id)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="变体不存在")
    tone = db.get(Tone, v.tone_id)
    if tone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="调性不存在")

    cfg = db.get(QuotaConfig, 1)
    if cfg and cfg.circuit_breaker and breaker.is_open():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="生成服务已熔断，请稍后重试")

    real = settings.use_real_llm and bool(settings.anthropic_api_key)

    # 配额预检（单条按 1 条中等长度估）
    est_in, est_out, _ = estimate_tokens(body.prompt, ["x" * 200], GEN_MODEL)
    if cfg:
        if user_tokens_today(db, user.name) + est_in + est_out > cfg.per_user_daily:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="今日 token 配额已用尽")
        if cfg.global_used + global_tokens_today(db) + est_in + est_out > cfg.global_daily:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="全局日预算已用尽")

    # 弱负信号：对旧变体记 regenerate（在替换前，position 反映其当前排名）
    record_event(db, user=user.name, event_type="regenerate", variant_id=variant_id, tone_id=v.tone_id, position=v.rank)

    if real:
        from ..pipeline.generate import regenerate_one

        tone_dict = {"id": tone.id, "handle": tone.handle, "name": tone.name, "desc": tone.desc}
        # 复用原会话的事实底稿 + 临时仿写范本，使重生成仍贴合被引用新闻与仿写风格
        news_ctx = None
        sess_style_refs = None
        if v.session_id:
            sess = db.get(GenerationSession, v.session_id)
            if sess is not None:
                news_ctx = sess.news_context
                sess_style_refs = sess.style_refs
        samples = _fewshot_for(db, tone.id, sess_style_refs)
        try:
            fields, usages = regenerate_one(tone_dict, body.prompt, v.dimensions, news=news_ctx, samples=samples)
        except Exception as ex:  # noqa: BLE001
            breaker.record(False)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"生成失败：{type(ex).__name__}") from ex
        breaker.record(True)
        _record_llm_usage(db, user.name, usages)
    else:
        # 离线/无 key：库内轮换——取同调性下另一条不同正文，换个说法给出替代
        alts = list(
            db.scalars(
                select(Variant).where(Variant.tone_id == v.tone_id, Variant.id != v.id).order_by(Variant.rank)
            )
        )
        pick = next((a for a in alts if a.body != v.body), alts[0] if alts else None)
        if pick is None:
            fields = {"body": v.body, "score": v.score, "aiScore": v.ai_score,
                      "compliance": v.compliance, "softFlagSentence": v.soft_flag_sentence,
                      "softFlagCount": v.soft_flag_count, "styleDistance": v.style_distance}
        else:
            fields = {"body": pick.body, "score": pick.score, "aiScore": pick.ai_score,
                      "compliance": pick.compliance, "softFlagSentence": pick.soft_flag_sentence,
                      "softFlagCount": pick.soft_flag_count, "styleDistance": pick.style_distance}
        est_in, est_out, cost = estimate_tokens(body.prompt, [fields["body"]], GEN_MODEL)
        record_usage(db, user.name, GEN_MODEL, est_in, est_out, cost, "文案生成")
        breaker.record(True)

    # 原地更新（保 id/rank/dimensions）
    v.body = fields["body"]
    v.score = fields["score"]
    v.ai_score = fields["aiScore"]
    v.compliance = fields["compliance"]
    v.soft_flag_sentence = fields.get("softFlagSentence")
    v.soft_flag_count = fields.get("softFlagCount")
    v.style_distance = fields["styleDistance"]
    v.confirmed = False
    db.commit()
    db.refresh(v)
    return v
