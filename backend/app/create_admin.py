"""创建管理员账号。生产环境 seed_demo_data=False，库里没有任何用户，用本脚本开第一个口子。

    docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.create_admin <用户名>

密码从交互式提示读取；非交互场景（CI/自动化）用 ADMIN_PASSWORD 环境变量传入。
**不接受命令行传密码**——argv 会进 shell history，也会被同机的 `ps` 看到。
"""

import getpass
import os
import sys
import uuid

from sqlalchemy import func, select

from .db import SessionLocal
from .models import User
from .security import hash_password

_MIN_LEN = 12


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python -m app.create_admin <用户名>（密码走提示或 ADMIN_PASSWORD 环境变量）", file=sys.stderr)
        return 2

    name = sys.argv[1].strip()
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
        db.add(User(id=f"u_{uuid.uuid4().hex[:12]}", name=name, role="admin",
                    password_hash=hash_password(password)))
        db.commit()

    print(f"管理员 {name!r} 已创建。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
