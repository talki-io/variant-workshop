"""菜单管理（数据驱动导航注册表）。

混合门禁：`GET /menus`（渲染当前用户的侧栏）任意登录用户可调；其余（全量/增删改）走 require_admin。

icon 必须在白名单内——前端图标是静态 import + tree-shaking，只有注册表里的图标能渲染
（对应 frontend/src/layout/menuIcons.tsx，两处须保持一致）。
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MenuItem, User
from ..schemas import MenuItemCreateIn, MenuItemOut, MenuItemUpdateIn, OkOut
from ..security import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["menus"])

_ROLES = {"editor", "admin"}

# 图标白名单（须与 frontend/src/layout/menuIcons.tsx 的键集一致）
ICON_NAMES = {
    "EditOutlined", "ReadOutlined", "TeamOutlined", "RobotOutlined", "LineChartOutlined",
    "DatabaseOutlined", "AppstoreOutlined", "UserOutlined", "UsergroupAddOutlined",
    "SettingOutlined", "FileTextOutlined", "BellOutlined", "SearchOutlined", "DashboardOutlined",
    "BarChartOutlined", "PieChartOutlined", "CloudOutlined", "ApiOutlined", "ThunderboltOutlined",
    "SafetyOutlined", "ProfileOutlined", "ScheduleOutlined", "TagsOutlined", "FolderOutlined",
    "GlobalOutlined", "KeyOutlined", "HomeOutlined", "MenuOutlined", "UnorderedListOutlined",
}


def _validate_icon(icon: str) -> None:
    if icon not in ICON_NAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"图标 {icon!r} 不在白名单内",
        )


def _validate_roles(roles: list[str]) -> None:
    if not roles or any(r not in _ROLES for r in roles):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"visibleRoles 必须是 {sorted(_ROLES)} 的非空子集",
        )


def _path_taken(db: Session, path: str, *, exclude_id: str | None = None) -> bool:
    q = select(MenuItem).where(MenuItem.path == path)
    if exclude_id is not None:
        q = q.where(MenuItem.id != exclude_id)
    return db.scalar(q) is not None


@router.get("/menus", response_model=list[MenuItemOut])
def my_menus(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[MenuItem]:
    """当前用户可见的菜单（enabled 且角色在 visible_roles），按 order 升序——驱动实时侧栏。"""
    rows = db.scalars(select(MenuItem).where(MenuItem.enabled.is_(True)).order_by(MenuItem.order, MenuItem.path))
    return [m for m in rows if user.role in (m.visible_roles or [])]


@router.get("/menus/all", response_model=list[MenuItemOut], dependencies=[Depends(require_admin)])
def all_menus(db: Session = Depends(get_db)) -> list[MenuItem]:
    """全量菜单（含 disabled），供管理页。"""
    return list(db.scalars(select(MenuItem).order_by(MenuItem.order, MenuItem.path)))


@router.post("/menus", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_menu(body: MenuItemCreateIn, db: Session = Depends(get_db)) -> MenuItem:
    """新增菜单项（admin）。"""
    path = body.path.strip()
    label = body.label.strip()
    if not path or not label:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="路径与名称不能为空")
    _validate_icon(body.icon)
    _validate_roles(body.visible_roles)
    if _path_taken(db, path):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"路径「{path}」已有菜单项")
    m = MenuItem(
        id="m_" + uuid4().hex[:8],
        path=path,
        label=label,
        icon=body.icon,
        order=body.order,
        visible_roles=body.visible_roles,
        enabled=body.enabled,
        locked=False,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/menus/{menu_id}", response_model=MenuItemOut, dependencies=[Depends(require_admin)])
def update_menu(menu_id: str, body: MenuItemUpdateIn, db: Session = Depends(get_db)) -> MenuItem:
    """部分更新菜单项（admin）。locked 项仍可改（仅禁删）。"""
    m = db.get(MenuItem, menu_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单项不存在")
    if body.icon is not None:
        _validate_icon(body.icon)
        m.icon = body.icon
    if body.visible_roles is not None:
        _validate_roles(body.visible_roles)
        m.visible_roles = body.visible_roles
    if body.path is not None:
        path = body.path.strip()
        if not path:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="路径不能为空")
        if path != m.path and _path_taken(db, path, exclude_id=m.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"路径「{path}」已有菜单项")
        m.path = path
    if body.label is not None:
        if not body.label.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="名称不能为空")
        m.label = body.label.strip()
    if body.order is not None:
        m.order = body.order
    if body.enabled is not None:
        m.enabled = body.enabled
    db.commit()
    db.refresh(m)
    return m


@router.delete("/menus/{menu_id}", response_model=OkOut, dependencies=[Depends(require_admin)])
def delete_menu(menu_id: str, db: Session = Depends(get_db)) -> OkOut:
    """删除菜单项（admin）。locked 核心项（用户/菜单管理）禁止删除。"""
    m = db.get(MenuItem, menu_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单项不存在")
    if m.locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="核心菜单项不可删除")
    db.delete(m)
    db.commit()
    return OkOut(ok=True)
