import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal
from .routers import auth, compliance, dashboard, models, news, quota, sources, telemetry, tones, variants
from .seed import seed

# 默认/占位密钥值——若线上用这些则拒绝安全承诺（§7 P1-4）。
_INSECURE_SECRETS = {"dev-insecure-secret", "change-me-to-a-long-random-string", ""}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0) 密钥卫士：用占位/默认 JWT_SECRET 时高声告警（生产务必换强随机值，走 Secret Manager）。
    if settings.jwt_secret in _INSECURE_SECRETS:
        logging.getLogger("uvicorn.error").warning(
            "⚠️ JWT_SECRET 使用了默认/占位值。生产环境必须改为强随机密钥并经 Secret Manager 注入（见 .env.example / HANDOFF-BACKEND §7）。"
        )
    # 1) 用 Alembic 迁移建/升级 schema（迁移里已含 CREATE EXTENSION vector）。
    #    单一事实来源，替代旧的 create_all。
    command.upgrade(AlembicConfig("alembic.ini"), "head")
    # 2) 幂等灌假数据 + 载入模型场景配置到进程缓存
    with SessionLocal() as db:
        seed(db)
        from .llm import refresh_model_config

        refresh_model_config(db)
    # 3) 可选：启用 M1 定时抓取
    if settings.crawl_scheduler_enabled:
        from .scheduler import start_scheduler

        start_scheduler()
    yield


app = FastAPI(title="变体工坊 API", version="0.1.0", lifespan=lifespan)

# 前端走 Vite proxy（同源 /api），CORS 仅为直连 5173 联调兜底。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, tones, variants, news, dashboard, sources, quota, compliance, telemetry, models):
    app.include_router(r.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
