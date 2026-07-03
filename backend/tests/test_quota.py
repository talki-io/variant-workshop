from datetime import datetime

from fastapi.testclient import TestClient

from app.breaker import CircuitBreaker
from app.db import SessionLocal
from app.main import app
from app.models import QuotaConfig, TokenUsage
from app.usage import estimate_tokens


def _token(client: TestClient, username: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    assert r.status_code == 200
    return r.json()["token"]


# 测试共享 live 库：配额用例需要用户"从零"起量，但不能毁掉真实 token_usage。
# 故先快照并清空该用户的现有行，跑完再原样恢复（避免删除真实用量数据）。
def _snapshot_and_clear(user: str) -> list[dict]:
    with SessionLocal() as db:
        cols = [c.name for c in TokenUsage.__table__.columns]
        saved = [
            {c: getattr(r, c) for c in cols}
            for r in db.query(TokenUsage).filter(TokenUsage.user == user).all()
        ]
        db.query(TokenUsage).filter(TokenUsage.user == user).delete()
        db.commit()
        return saved


def _restore(user: str, saved: list[dict]) -> None:
    with SessionLocal() as db:
        db.query(TokenUsage).filter(TokenUsage.user == user).delete()  # 清掉测试期新增的行
        for row in saved:
            db.add(TokenUsage(**row))
        db.commit()


def test_estimate_monotonic_and_positive_cost():
    small = estimate_tokens("hi", ["abc"], "Sonnet")
    big = estimate_tokens("a longer prompt " * 30, ["x" * 300], "Sonnet")
    assert big[0] > small[0]      # input grows with prompt
    assert big[1] > small[1]      # output grows with bodies
    assert small[2] > 0 and big[2] > small[2]  # cost positive & monotonic


def test_breaker_trips_on_error_rate_and_manual():
    cb = CircuitBreaker(threshold=0.5, window=10, min_samples=4)
    for _ in range(4):
        cb.record(False)
    assert cb.is_open()
    cb.reset()
    for _ in range(4):
        cb.record(True)
    assert not cb.is_open()
    cb.trip()
    assert cb.is_open()


def test_generate_records_usage_then_enforces_quota():
    saved = _snapshot_and_clear("editor")
    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {_token(client, 'editor')}"}

            # 首次生成成功，并落一行 token_usage
            r1 = client.post("/api/variants", json={"toneId": "t1", "prompt": "tes"}, headers=headers)
            assert r1.status_code == 200
            with SessionLocal() as db:
                assert db.query(TokenUsage).filter(TokenUsage.user == "editor").count() == 1

            # 人为把今日用量顶到 per_user_daily，再次生成应 429
            with SessionLocal() as db:
                cfg = db.get(QuotaConfig, 1)
                db.add(TokenUsage(
                    id="test_big_editor", user="editor",
                    time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    model="Sonnet", input_tokens=cfg.per_user_daily, output_tokens=0,
                    cost=0.0, scene="文案生成",
                ))
                db.commit()

            r2 = client.post("/api/variants", json={"toneId": "t1", "prompt": "tes"}, headers=headers)
            assert r2.status_code == 429
            assert "配额" in r2.json()["detail"]
    finally:
        _restore("editor", saved)


def test_quota_endpoint_reflects_self_usage():
    saved = _snapshot_and_clear("admin")
    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {_token(client, 'admin')}"}
            client.post("/api/variants", json={"toneId": "t1", "prompt": "halo dunia"}, headers=headers)
            q = client.get("/api/quota", headers=headers).json()
            self_row = q["users"][0]
            assert self_row["isSelf"] is True
            assert self_row["used"] > 0            # 反映真实今日用量
            assert q["config"]["globalUsed"] > 0
    finally:
        _restore("admin", saved)
