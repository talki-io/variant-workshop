from fastapi.testclient import TestClient

from app.main import app


def _headers(c: TestClient, username: str) -> dict:
    r = c.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_menus_role_filter_and_auth():
    with TestClient(app) as c:
        assert c.get("/api/menus").status_code == 401
        eh = _headers(c, "editor")
        ah = _headers(c, "admin")
        e_paths = {m["path"] for m in c.get("/api/menus", headers=eh).json()}
        a_rows = c.get("/api/menus", headers=ah).json()
        a_paths = {m["path"] for m in a_rows}
        # editor 看得到通用项，看不到 admin 专属
        assert {"/generate", "/news", "/accounts"} <= e_paths
        assert "/dashboard" not in e_paths and "/users" not in e_paths
        # admin 看得到全部（含新模块）
        assert {"/users", "/menus", "/dashboard"} <= a_paths
        # order 升序
        orders = [m["order"] for m in a_rows]
        assert orders == sorted(orders)


def test_menus_all_admin_only():
    with TestClient(app) as c:
        assert c.get("/api/menus/all", headers=_headers(c, "editor")).status_code == 403
        assert c.get("/api/menus/all", headers=_headers(c, "admin")).status_code == 200


def test_menu_crud_and_validation():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        eh = _headers(c, "editor")
        # editor 不能建
        assert c.post("/api/menus", headers=eh,
                      json={"path": "/x", "label": "x", "icon": "EditOutlined", "visibleRoles": ["admin"]}).status_code == 403
        # icon 白名单外 → 422
        assert c.post("/api/menus", headers=ah,
                      json={"path": "/pytest_m", "label": "测试", "icon": "NopeIcon", "visibleRoles": ["admin"]}).status_code == 422
        # visibleRoles 非法 → 422
        assert c.post("/api/menus", headers=ah,
                      json={"path": "/pytest_m", "label": "测试", "icon": "EditOutlined", "visibleRoles": ["boss"]}).status_code == 422
        # 正常建（editor+admin 可见）
        r = c.post("/api/menus", headers=ah,
                   json={"path": "/pytest_m", "label": "测试项", "icon": "TagsOutlined", "order": 99,
                         "visibleRoles": ["editor", "admin"]})
        assert r.status_code == 201
        mid = r.json()["id"]
        try:
            assert r.json()["locked"] is False
            # 重复 path → 409
            assert c.post("/api/menus", headers=ah,
                          json={"path": "/pytest_m", "label": "x", "icon": "EditOutlined", "visibleRoles": ["admin"]}).status_code == 409
            # editor 现在能看到它
            assert "/pytest_m" in {m["path"] for m in c.get("/api/menus", headers=eh).json()}
            # 改可见角色为仅 admin → editor 看不到
            assert c.put(f"/api/menus/{mid}", headers=ah, json={"visibleRoles": ["admin"]}).status_code == 200
            assert "/pytest_m" not in {m["path"] for m in c.get("/api/menus", headers=eh).json()}
            # 禁用 → /menus 不返回，但 /menus/all 仍在
            assert c.put(f"/api/menus/{mid}", headers=ah, json={"enabled": False}).status_code == 200
            assert "/pytest_m" not in {m["path"] for m in c.get("/api/menus", headers=ah).json()}
            assert "/pytest_m" in {m["path"] for m in c.get("/api/menus/all", headers=ah).json()}
        finally:
            assert c.delete(f"/api/menus/{mid}", headers=ah).status_code == 200


def test_menu_locked_cannot_delete():
    with TestClient(app) as c:
        ah = _headers(c, "admin")
        allm = c.get("/api/menus/all", headers=ah).json()
        locked = next(m for m in allm if m["path"] == "/users")
        assert locked["locked"] is True
        assert c.delete(f"/api/menus/{locked['id']}", headers=ah).status_code == 409
