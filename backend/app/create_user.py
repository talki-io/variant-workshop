"""创建用户账号。生产 seed_demo_data=False，库里没有任何用户，用本脚本开口子。

系统没有「注册」和「修改密码」的界面/端点（auth.py 只有 login 与 /me），
所以增删用户、换密码都走这里。

    # 建素材员（默认角色 editor，最小权限）
    docker compose -f deploy/docker-compose.prod.yml exec backend \
        python -m app.create_user zhangwei

    # 建管理员，必须显式指定
    docker compose -f deploy/docker-compose.prod.yml exec backend \
        python -m app.create_user admin --role admin

角色：
    editor  生成文案、看新闻库、合规检查
    admin   editor 的全部 + 账号管理 / 模型管理 / 配额 / 抓取源 / 消耗看板

密码从交互式提示读取；非交互场景（批量建号/CI）用 ADMIN_PASSWORD 环境变量传入。
**不接受命令行传密码**——argv 会进 shell history，也会被同机的 `ps` 看到。
"""

import argparse
import getpass
import os
import sys
import uuid

from sqlalchemy import func, select

from .db import SessionLocal
from .models import User
from .security import hash_password

_MIN_LEN = 12
_ROLES = ("editor", "admin")


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="python -m app.create_user",
        description="创建用户账号（密码走交互提示或 ADMIN_PASSWORD 环境变量，不接受命令行传密码）",
    )
    ap.add_argument("name", help="用户名")
    # 默认 editor：最小权限。手滑不会凭空多出一个管理员。
    ap.add_argument("--role", choices=_ROLES, default="editor", help="角色（默认 editor）")
    args = ap.parse_args()

    name = args.name.strip()
    if not name:
        print("用户名不能为空。", file=sys.stderr)
        return 2

    password = os.environ.get("ADMIN_PASSWORD")
    if password is None:
        if not sys.stdin.isatty():
            print("非交互环境请用 ADMIN_PASSWORD 环境变量传密码。", file=sys.stderr)
            return 2
        password = getpass.getpass("密码：")
        if password != getpass.getpass("再输一次："):
            print("两次输入不一致。", file=sys.stderr)
            return 1

    # 先查演示密码：它只有 8 位，放在长度检查之后就永远轮不到，报错会误导人。
    if password == "demo1234":
        print("拒绝使用演示密码 demo1234。", file=sys.stderr)
        return 1
    if len(password) < _MIN_LEN:
        print(f"密码至少 {_MIN_LEN} 位。", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User).where(User.name == name)):
            print(f"用户 {name!r} 已存在。", file=sys.stderr)
            return 1
        db.add(User(id=f"u_{uuid.uuid4().hex[:12]}", name=name, role=args.role,
                    password_hash=hash_password(password), active=True))
        db.commit()

    print(f"{args.role} {name!r} 已创建。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
