"""测试隔离：让 pytest 跑在独立的 imitator_test 库，永不污染 live 的 imitator 库。

启用方式——运行 pytest 时把 DATABASE_URL 指向独立库：
    -e DATABASE_URL=postgresql+psycopg://app:app@db:5432/imitator_test
本文件在会话开始时（仅当 URL 指向 imitator_test）自动：建库(若缺) → 迁移到 head → seed，
确保即使刚 `down -v` 过、测试库不存在也能自愈。不带该 env 时本文件不做任何事（回退旧行为）。
"""

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text

from app.config import settings
from app.db import SessionLocal
from app.seed import seed

_TEST_DB = "imitator_test"


def _dbname(url: str) -> str:
    return url.rsplit("/", 1)[-1]


if _dbname(settings.database_url) == _TEST_DB:
    # 连到同一 server 的 live 库以发 CREATE DATABASE（CREATE 不能在事务里，故用 AUTOCOMMIT）。
    admin_url = settings.database_url.rsplit("/", 1)[0] + "/imitator"
    _eng = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with _eng.connect() as _c:
        if not _c.execute(text(f"select 1 from pg_database where datname='{_TEST_DB}'")).scalar():
            _c.execute(text(f"create database {_TEST_DB}"))
    _eng.dispose()
    # 对测试库迁移 + seed（env.py / SessionLocal 都读 settings.database_url = 测试库）。
    command.upgrade(AlembicConfig("alembic.ini"), "head")
    with SessionLocal() as _db:
        seed(_db)
