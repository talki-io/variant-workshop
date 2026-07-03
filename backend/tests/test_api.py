from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import News


def _login(c: TestClient, username: str, password: str = "demo1234"):
    return c.post("/api/auth/login", json={"username": username, "password": password})


def _headers(c: TestClient, username: str) -> dict:
    return {"Authorization": f"Bearer {_login(c, username).json()['token']}"}


_TEST_NEWS_ID = "n_test_fixture"


def _ensure_news() -> tuple[str, bool]:
    """确保至少一条新闻用于打标测试（新闻表现在只由真实抓取填充，测试不依赖种子）。

    返回 (news_id, created)。已有真实新闻则复用其一，否则插入一条 test.local 测试行（仅测试库、跑完清理）。
    """
    with SessionLocal() as db:
        existing = db.query(News).first()
        if existing is not None:
            return existing.id, False
        db.add(News(
            id=_TEST_NEWS_ID, headline="pytest fixture news", source="test",
            published_at="2026-01-01T00:00:00+07:00", published_label="test", freshness="old",
            heat=0, key_facts=[], tickers=[], angle_hints=[],
            url="https://test.local/fixture", label="none",
        ))
        db.commit()
        return _TEST_NEWS_ID, True


def _cleanup_news(created: bool) -> None:
    if not created:
        return
    with SessionLocal() as db:
        row = db.get(News, _TEST_NEWS_ID)
        if row is not None:
            db.delete(row)
            db.commit()


def test_login_ok_and_me():
    with TestClient(app) as c:
        r = _login(c, "admin")
        assert r.status_code == 200
        d = r.json()
        assert d["token"] and d["user"]["role"] == "admin"
        me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {d['token']}"})
        assert me.status_code == 200 and me.json()["name"] == "admin"


def test_login_bad_password_401():
    with TestClient(app) as c:
        assert _login(c, "admin", "wrong").status_code == 401


def test_bad_token_401():
    with TestClient(app) as c:
        assert c.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_tones_news_require_auth():
    with TestClient(app) as c:
        assert c.get("/api/tones").status_code == 401
        assert c.get("/api/news").status_code == 401
        h = _headers(c, "editor")
        assert len(c.get("/api/tones", headers=h).json()) == 4
        # 新闻表只由真实抓取填充（不再灌演示假数据），全新库可能为空——断言返回的是列表即可
        assert isinstance(c.get("/api/news", headers=h).json(), list)


def test_admin_only_endpoints_rbac():
    with TestClient(app) as c:
        eh = _headers(c, "editor")
        ah = _headers(c, "admin")
        for path in ("/api/dashboard", "/api/sources", "/api/quota"):
            assert c.get(path, headers=eh).status_code == 403, path
            assert c.get(path, headers=ah).status_code == 200, path


def test_response_shapes_are_camel():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        sources = c.get("/api/sources", headers=ah).json()
        # 种子源已换成真实 RSS/Playwright 源（见 HANDOFF §7j）
        assert "RSS" in {s["type"] for s in sources}
        assert "lastCrawl" in sources[0]
        quota = c.get("/api/quota", headers=ah).json()
        assert set(quota) == {"config", "users"}
        assert "perUserDaily" in quota["config"] and "globalUsedPct" in quota["config"]
        dash = c.get("/api/dashboard", headers=ah).json()
        assert {"kpi", "daily", "topUsers", "details"} <= set(dash)
        assert "todayTokens" in dash["kpi"]


# ===== 写回端点（HANDOFF-FIXME §1）=====


def test_news_label_persists_and_restores():
    nid, created = _ensure_news()
    with TestClient(app) as c:
        h = _headers(c, "editor")
        original = {n["id"]: n["label"] for n in c.get("/api/news", headers=h).json()}[nid]
        try:
            r = c.put(f"/api/news/{nid}/label", headers=h, json={"label": "relevant"})
            assert r.status_code == 200 and r.json()["label"] == "relevant"
            # 落库：重新读取仍为 relevant
            again = {n["id"]: n for n in c.get("/api/news", headers=h).json()}
            assert again[nid]["label"] == "relevant"
        finally:
            c.put(f"/api/news/{nid}/label", headers=h, json={"label": original})
            _cleanup_news(created)


def test_news_label_validation_and_auth():
    nid, created = _ensure_news()
    with TestClient(app) as c:
        h = _headers(c, "editor")
        assert c.put(f"/api/news/{nid}/label", json={"label": "relevant"}).status_code == 401
        assert c.put(f"/api/news/{nid}/label", headers=h, json={"label": "bogus"}).status_code == 422
        assert c.put("/api/news/does_not_exist/label", headers=h, json={"label": "relevant"}).status_code == 404
    _cleanup_news(created)


def test_source_crud_admin_only():
    with TestClient(app) as c:
        eh = _headers(c, "editor")
        ah = _headers(c, "admin")
        payload = {"name": "临时测试源", "type": "RSS", "url": "https://example.com/rss", "frequency": "每 60 分钟"}
        # editor 被拒
        assert c.post("/api/sources", headers=eh, json=payload).status_code == 403
        # admin 新增
        created = c.post("/api/sources", headers=ah, json=payload)
        assert created.status_code == 201
        sid = created.json()["id"]
        assert created.json()["enabled"] is True and created.json()["type"] == "RSS"
        try:
            # 更新：切类型校验 + 启用开关
            assert c.put(f"/api/sources/{sid}", headers=ah, json={"type": "bogus"}).status_code == 422
            upd = c.put(f"/api/sources/{sid}", headers=ah, json={"enabled": False, "name": "改名了"})
            assert upd.status_code == 200 and upd.json()["enabled"] is False and upd.json()["name"] == "改名了"
        finally:
            assert c.delete(f"/api/sources/{sid}", headers=ah).json()["ok"] is True
        # 删后 404
        assert c.put(f"/api/sources/{sid}", headers=ah, json={"enabled": True}).status_code == 404
        assert c.delete(f"/api/sources/{sid}", headers=ah).status_code == 404


def test_quota_update_admin_only_and_restores():
    with TestClient(app) as c:
        eh = _headers(c, "editor")
        ah = _headers(c, "admin")
        cfg = c.get("/api/quota", headers=ah).json()["config"]
        body = {k: cfg[k] for k in ("perUserDaily", "overThresholdPct", "circuitBreaker", "breakerCondition", "globalDaily")}
        assert c.put("/api/quota", headers=eh, json=body).status_code == 403
        try:
            bumped = {**body, "overThresholdPct": (body["overThresholdPct"] % 99) + 1}
            r = c.put("/api/quota", headers=ah, json=bumped)
            assert r.status_code == 200 and r.json()["config"]["overThresholdPct"] == bumped["overThresholdPct"]
        finally:
            c.put("/api/quota", headers=ah, json=body)


def _first_variant(c: TestClient, headers: dict) -> dict:
    batch = c.post("/api/variants", headers=headers, json={"toneId": "t1", "prompt": "测试用例"}).json()
    return batch["variants"][0]


def test_variant_edit_recheck_and_restore():
    with TestClient(app) as c:
        h = _headers(c, "editor")
        var = _first_variant(c, h)
        vid, original = var["id"], var["body"]
        try:
            r = c.patch(f"/api/variants/{vid}", headers=h, json={"body": "Ini teks baru untuk pengujian."})
            assert r.status_code == 200
            assert r.json()["body"].startswith("Ini teks baru")
            assert r.json()["confirmed"] is False
            assert r.json()["compliance"] in {"pass", "soft", "blocked"}
            # 空正文 422、缺 token 401、不存在 404
            assert c.patch(f"/api/variants/{vid}", headers=h, json={"body": "   "}).status_code == 422
            assert c.patch(f"/api/variants/{vid}", json={"body": "x"}).status_code == 401
            assert c.patch("/api/variants/nope/", headers=h, json={"body": "x"}).status_code in (404, 405)
        finally:
            c.patch(f"/api/variants/{vid}", headers=h, json={"body": original})


def test_variant_regenerate_offline():
    with TestClient(app) as c:
        h = _headers(c, "editor")
        var = _first_variant(c, h)
        vid, original = var["id"], var["body"]
        try:
            r = c.post(f"/api/variants/{vid}/regenerate", headers=h, json={"prompt": "换个说法"})
            assert r.status_code == 200
            assert r.json()["confirmed"] is False
            assert r.json()["compliance"] in {"pass", "soft", "blocked"}
            assert c.post("/api/variants/nope/regenerate", headers=h, json={"prompt": "x"}).status_code == 404
        finally:
            c.patch(f"/api/variants/{vid}", headers=h, json={"body": original})


def test_generation_sessions_retrieval_and_isolation():
    """离线生成不建会话，故直接插入会话+变体验证读取端点（含变体归属 + 按用户隔离）。"""
    from app.db import SessionLocal
    from app.models import GenerationSession, Variant

    sid = "gs_test_x1"
    vid = "g_test_x1"
    db = SessionLocal()
    try:
        db.add(GenerationSession(
            id=sid, user="editor", tone_id="t1", prompt="pytest 会话",
            source_headline="某新闻标题", diversity=0.8, created_at="2026-07-02 12:00:00",
        ))
        db.add(Variant(
            id=vid, tone_id="t1", rank=1, score=80, dimensions={"hook": "悬念"}, body="测试正文",
            compliance="pass", ai_score=30, style_distance=0.3, confirmed=False, session_id=sid,
        ))
        db.commit()
    finally:
        db.close()

    with TestClient(app) as c:
        eh = _headers(c, "editor")
        ah = _headers(c, "admin")
        assert c.get("/api/variants/sessions").status_code == 401
        sess = c.get("/api/variants/sessions", headers=eh).json()
        mine = next((s for s in sess if s["id"] == sid), None)
        assert mine is not None
        assert mine["prompt"] == "pytest 会话" and mine["sourceHeadline"] == "某新闻标题"
        assert mine["favorite"] is False
        assert [v["id"] for v in mine["variants"]] == [vid]
        # admin 看不到 editor 的会话（按用户隔离）
        assert all(s["id"] != sid for s in c.get("/api/variants/sessions", headers=ah).json())

        # 收藏：仅本人可改；admin 改 editor 的会话 → 404
        assert c.patch(f"/api/variants/sessions/{sid}", headers=ah, json={"favorite": True}).status_code == 404
        r = c.patch(f"/api/variants/sessions/{sid}", headers=eh, json={"favorite": True})
        assert r.status_code == 200 and r.json()["favorite"] is True
        # 删除：admin 删不了 editor 的 → 404；本人可删，变体一并删除
        assert c.delete(f"/api/variants/sessions/{sid}", headers=ah).status_code == 404
        assert c.delete(f"/api/variants/sessions/{sid}", headers=eh).json()["ok"] is True
        assert all(s["id"] != sid for s in c.get("/api/variants/sessions", headers=eh).json())

    db = SessionLocal()
    try:
        # 会话与变体都应已随删除清除；兜底清理
        if db.get(Variant, vid):
            db.delete(db.get(Variant, vid))
        if db.get(GenerationSession, sid):
            db.delete(db.get(GenerationSession, sid))
        db.commit()
    finally:
        db.close()


# ===== 账号风格样本（往期爆款 few-shot 锚）=====
def test_style_samples_crud():
    with TestClient(app) as c:
        h = _headers(c, "admin")
        # 列出 t1 的种子样本（seed 导入 10 条）
        r = c.get("/api/tones/t1/samples", headers=h)
        assert r.status_code == 200
        base = len(r.json())
        assert base >= 1  # 至少有种子爆款
        assert all(s["toneId"] == "t1" for s in r.json())

        # 新增一条
        r = c.post("/api/tones/t1/samples", headers=h,
                   json={"body": "pytest 爆款样本：第一人称开场+干货+软CTA。", "source": "pytest"})
        assert r.status_code == 200
        sid = r.json()["id"]
        assert r.json()["source"] == "pytest"
        assert len(c.get("/api/tones/t1/samples", headers=h).json()) == base + 1

        # 空正文 422 / 不存在的调性 404
        assert c.post("/api/tones/t1/samples", headers=h, json={"body": "   "}).status_code == 422
        assert c.post("/api/tones/nope/samples", headers=h, json={"body": "x"}).status_code == 404

        # 删除，恢复计数
        assert c.delete(f"/api/samples/{sid}", headers=h).status_code == 200
        assert len(c.get("/api/tones/t1/samples", headers=h).json()) == base
        assert c.delete(f"/api/samples/{sid}", headers=h).status_code == 404
