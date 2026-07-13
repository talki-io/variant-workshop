"""用户管理（admin CRUD）。

界面化增删改用户、改角色、重置密码、启用/停用——替代只能命令行建号的 create_user.py。

⚠️ 用户在库里被两种键引用且无外键（见 models）：
- `tones.owner_id` / JWT sub 用 **user.id**；
- `generation_session.user` / `token_usage.user` / `telemetry_event.user` 用 **user.name** 字符串。
因此改名必须跨三张 name 键表级联更新；删除会遗留孤儿 tones，需级联清理。
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    GenerationSession,
    StyleSample,
    TelemetryEvent,
    TokenUsage,
    Tone,
    User,
    Variant,
)
from ..schemas import OkOut, PasswordIn, UserCreateIn, UserOut, UserUpdateIn
from ..security import get_current_user, hash_password, require_admin

router = APIRouter(prefix="/api", tags=["users"], dependencies=[Depends(require_admin)])

_ROLES = ("editor", "admin")
_MIN_PASSWORD = 8


def _validate_password(password: str) -> None:
    if len(password) < _MIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"密码至少 {_MIN_PASSWORD} 位",
        )


def _name_taken(db: Session, name: str, *, exclude_id: str | None = None) -> bool:
    q = select(func.count()).select_from(User).where(User.name == name)
    if exclude_id is not None:
        q = q.where(User.id != exclude_id)
    return bool(db.scalar(q))


def _active_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(User).where(User.role == "admin", User.active.is_(True))
    ) or 0


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """列出全部用户（绝不出 password_hash）。"""
    return list(db.scalars(select(User).order_by(User.role.desc(), User.id)))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, db: Session = Depends(get_db)) -> User:
    """新增用户。校验：name 非空且唯一、role 合法、密码 ≥8 位。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="用户名不能为空")
    if body.role not in _ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"role 必须是 {list(_ROLES)} 之一")
    _validate_password(body.password)
    if _name_taken(db, name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"用户名「{name}」已存在")
    u = User(
        id="u_" + uuid4().hex[:12],
        name=name,
        role=body.role,
        password_hash=hash_password(body.password),
        active=body.active,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: UserUpdateIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
) -> User:
    """部分更新用户（改名/改角色/启停）。改名跨 name 键表级联；含防自锁与末位管理员守卫。"""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 目标变更是否会撤除该用户的"活跃管理员"身份
    demoting = body.role is not None and body.role != "admin"
    deactivating = body.active is not None and body.active is False
    if u.role == "admin" and u.active and (demoting or deactivating):
        if _active_admin_count(db) <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能降级/停用最后一个管理员")

    # 防自锁：不能改自己的角色或停用自己
    if u.id == me.id and (body.role is not None and body.role != u.role):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能修改自己的角色")
    if u.id == me.id and deactivating:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能停用自己")

    if body.role is not None and body.role not in _ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"role 必须是 {list(_ROLES)} 之一")

    # 改名：先查重，再跨三张 name 键表级联更新（同一事务）
    if body.name is not None:
        new_name = body.name.strip()
        if not new_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="用户名不能为空")
        if new_name != u.name:
            if _name_taken(db, new_name, exclude_id=u.id):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"用户名「{new_name}」已存在")
            old_name = u.name
            for model in (GenerationSession, TokenUsage, TelemetryEvent):
                db.execute(update(model).where(model.user == old_name).values(user=new_name))
            u.name = new_name

    if body.role is not None:
        u.role = body.role
    if body.active is not None:
        u.active = body.active

    db.commit()
    db.refresh(u)
    return u


@router.put("/users/{user_id}/password", response_model=OkOut)
def reset_password(user_id: str, body: PasswordIn, db: Session = Depends(get_db)) -> OkOut:
    """重置某用户密码（admin）。"""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    _validate_password(body.password)
    u.password_hash = hash_password(body.password)
    db.commit()
    return OkOut(ok=True)


@router.delete("/users/{user_id}", response_model=OkOut)
def delete_user(
    user_id: str, db: Session = Depends(get_db), me: User = Depends(get_current_user)
) -> OkOut:
    """删除用户 + 级联清其账号(tones)+参考文案(style_sample)+生成会话(+挂靠变体)。

    保留 token_usage / telemetry_event（历史成本与审计，孤儿 name 字符串无害）。
    守卫：不能删自己、不能删最后一个活跃管理员。
    """
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if u.id == me.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能删除自己")
    if u.role == "admin" and u.active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能删除最后一个管理员")

    # 级联：账号 + 其参考文案（按 owner_id 归属）
    for t in db.scalars(select(Tone).where(Tone.owner_id == u.id)):
        for s in db.scalars(select(StyleSample).where(StyleSample.tone_id == t.id)):
            db.delete(s)
        db.delete(t)
    # 级联：生成会话（按 name 键）+ 挂靠该会话的变体
    for sess in db.scalars(select(GenerationSession).where(GenerationSession.user == u.name)):
        for v in db.scalars(select(Variant).where(Variant.session_id == sess.id)):
            db.delete(v)
        db.delete(sess)
    db.delete(u)
    db.commit()
    return OkOut(ok=True)
