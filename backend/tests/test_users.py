from datetime import datetime

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import TokenUsage, Tone


def _headers(c: TestClient, username: str, password: str = "demo1234") -> dict:
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_users_require_admin():
    with TestClient(app) as c:
        assert c.get("/api/users").status_code == 401
        assert c.get("/api/users", headers=_headers(c, "editor")).status_code == 403
        r = c.get("/api/users", headers=_headers(c, "admin"))
        assert r.status_code == 200
        rows = r.json()
        assert {"admin", "editor"} <= {u["name"] for u in rows}
        # 绝不出密码 hash
        assert all("passwordHash" not in u and "password_hash" not in u for u in rows)


def test_user_create_validation_and_duplicate():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        # 非法角色 / 过短密码 → 422
        assert c.post("/api/users", headers=ah,
                      json={"name": "pytest_v", "role": "boss", "password": "longenough1"}).status_code == 422
        assert c.post("/api/users", headers=ah,
                      json={"name": "pytest_v", "role": "editor", "password": "short"}).status_code == 422
        r = c.post("/api/users", headers=ah,
                   json={"name": "pytest_new", "role": "editor", "password": "initpass123"})
        assert r.status_code == 201
        uid = r.json()["id"]
        try:
            assert r.json()["active"] is True and r.json()["role"] == "editor"
            # 重名 → 409
            assert c.post("/api/users", headers=ah,
                          json={"name": "pytest_new", "role": "editor", "password": "initpass123"}).status_code == 409
        finally:
            c.delete(f"/api/users/{uid}", headers=ah)


def test_user_password_reset_and_deactivate_login():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        uid = c.post("/api/users", headers=ah,
                     json={"name": "pytest_login", "role": "editor", "password": "initpass123"}).json()["id"]
        try:
            assert c.post("/api/auth/login", json={"username": "pytest_login", "password": "initpass123"}).status_code == 200
            # 重置密码：旧密码失效、新密码可登录
            assert c.put(f"/api/users/{uid}/password", headers=ah, json={"password": "newpass1234"}).status_code == 200
            assert c.post("/api/auth/login", json={"username": "pytest_login", "password": "initpass123"}).status_code == 401
            tok = c.post("/api/auth/login", json={"username": "pytest_login", "password": "newpass1234"})
            assert tok.status_code == 200
            uh = {"Authorization": f"Bearer {tok.json()['token']}"}
            assert c.get("/api/auth/me", headers=uh).status_code == 200
            # 停用：登录 401 + 现存 token 立即失效
            assert c.put(f"/api/users/{uid}", headers=ah, json={"active": False}).status_code == 200
            assert c.post("/api/auth/login", json={"username": "pytest_login", "password": "newpass1234"}).status_code == 401
            assert c.get("/api/auth/me", headers=uh).status_code == 401
        finally:
            c.delete(f"/api/users/{uid}", headers=ah)


def test_user_rename_cascades_name_keyed_tables():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        uid = c.post("/api/users", headers=ah,
                     json={"name": "pytest_old", "role": "editor", "password": "initpass123"}).json()["id"]
        with SessionLocal() as db:
            db.add(TokenUsage(id="tu_rename_test", user="pytest_old",
                              time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                              model="Sonnet", input_tokens=1, output_tokens=1, cost=0.0, scene="文案生成"))
            db.commit()
        try:
            assert c.put(f"/api/users/{uid}", headers=ah, json={"name": "pytest_renamed"}).status_code == 200
            with SessionLocal() as db:
                # name 键表随改名级联更新
                assert db.get(TokenUsage, "tu_rename_test").user == "pytest_renamed"
        finally:
            with SessionLocal() as db:
                row = db.get(TokenUsage, "tu_rename_test")
                if row:
                    db.delete(row)
                    db.commit()
            c.delete(f"/api/users/{uid}", headers=ah)


def test_user_self_guards_and_delete_cascade():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        # 防自锁：admin 不能改自己角色 / 停用自己 / 删自己（均 409）
        assert c.put("/api/users/u_admin", headers=ah, json={"role": "editor"}).status_code == 409
        assert c.put("/api/users/u_admin", headers=ah, json={"active": False}).status_code == 409
        assert c.delete("/api/users/u_admin", headers=ah).status_code == 409

        # 删普通用户级联清其账号(tones)
        uid = c.post("/api/users", headers=ah,
                     json={"name": "pytest_cascade", "role": "editor", "password": "initpass123"}).json()["id"]
        uh = _headers(c, "pytest_cascade", "initpass123")
        tid = c.post("/api/tones", headers=uh, json={"handle": "@casc", "name": "级联体", "desc": "t"}).json()["id"]
        assert any(t["id"] == tid for t in c.get("/api/tones", headers=uh).json())
        assert c.delete(f"/api/users/{uid}", headers=ah).status_code == 200
        with SessionLocal() as db:
            assert db.get(Tone, tid) is None  # 账号随用户级联删除
