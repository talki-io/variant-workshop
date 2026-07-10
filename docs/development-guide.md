# 开发指南（development-guide）

> 怎么跑起来、怎么测、有哪些坑。
> 内容提取自历史交接文档 `HANDOFF-BACKEND.md`（已于 2026-07-10 从工作树移除，见 git 历史）。
> **本文描述当前应然状态，随代码更新。**

---

## 1. 环境前提

- Docker + Docker Compose
- Node.js 18+（前端跑在宿主）
- **不要试图在宿主直接 `pip install` 跑后端。** 宿主是 Python 3.14 且无 pip、无本地 Postgres——后端全部跑在 Docker 里。

---

## 2. 启动

### 后端（Docker）

```bash
cd backend
cp .env.example .env           # 首次：填一个随机 JWT_SECRET；DATABASE_URL 默认即可
docker compose up --build -d   # db(pgvector, 宿主:5433) + backend(宿主:8000)
curl localhost:8000/health     # {"status":"ok"}
```

OpenAPI 文档：<http://localhost:8000/docs>

### 前端（宿主）

```bash
cd frontend
npm install                    # 首次
npm run dev                    # http://localhost:5173
```

Vite 已配代理 `/api` → `:8000`，无需额外配置。

### 演示账号

种子数据，密码均 `demo1234`：

| 账号 | 角色 | 能看到什么 |
| --- | --- | --- |
| `admin` | 管理员 | 消耗看板 / 抓取与配额 / 账号管理 / 模型管理 |
| `editor` | 素材员 | 上述菜单隐藏；直接打 admin 端点，后端返回 **403** |

> 验证权限请用 `editor` 账号真实登录。前端不提供角色切换开关——它只切视图、服务端仍按真实角色，会误导。

---

## 3. 环境变量

`backend/.env`（不提交，见 `.gitignore`）。以 `.env.example` 为准，键集合必须一致。

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `…@db:5432/imitator` | host 用 compose 服务名 `db`、端口 `5432`（容器内网络） |
| `JWT_SECRET` | — | 填一个长随机串 |
| `JWT_EXPIRE_MINUTES` | `720` | HS256 |
| `ANTHROPIC_API_KEY` | 空 | **生产经 Secret Manager 注入，勿提交真实值** |
| `USE_REAL_LLM` | `false` | `true` 走真实 Anthropic 管线。**需与非空 `ANTHROPIC_API_KEY` 同时满足才生效** |
| `CRAWL_SCHEDULER_ENABLED` | `false` | `true` 时后台定时抓取已启用的 RSS 源；本地开发建议保持 `false` |

---

## 4. 测试

**注意 `tests/` 未进镜像也未挂载**，必须显式挂载。跑在独立的 `imitator_test` 库上，永不污染 live 库：

```bash
cd backend
docker compose run --rm \
  -e DATABASE_URL=postgresql+psycopg://app:app@db:5432/imitator_test \
  -e USE_REAL_LLM=false \
  -v "$PWD/tests:/app/tests" \
  backend python -m pytest tests -q
```

> ⚠️ **`-e DATABASE_URL=…imitator_test` 不能省。** 不带它会回退到 live 库 `imitator`，污染真实数据——历史上 admin/editor 的用量神秘消失就是这么来的。
> `-e USE_REAL_LLM=false` 保证测试离线、不产生 token 费用。

`conftest.py` 会在会话开始时自动建库（若缺）→ 迁移到 head → seed，即使测试库不存在也能自愈。

**前端门禁**：

```bash
cd frontend && npm run build    # 含 tsc --noEmit
```

前端目前无单元测试。新写的组件应带测试。

---

## 5. 坑

- **不要 `docker compose down -v`。** 卷里有真实抓取的新闻数据和 Alembic 迁移状态，`-v` 会一起清掉。改表用增量迁移。
- **passlib × bcrypt**：`passlib 1.7.4` 与 `bcrypt 5.x` 不兼容（启动即 `ValueError: password cannot be longer than 72 bytes`）。已在 `requirements.txt` 钉 `bcrypt==4.0.1`。升级 passlib 或换 bcrypt 直连时注意。
- **Anthropic 模型参数**：模型 ID 用裸串（`claude-haiku-4-5` / `claude-sonnet-5` / `claude-opus-4-8`）。Opus / Sonnet 4.7+ 仅支持 adaptive thinking，**传 `budget_tokens` 或 `temperature` 会 400**。
- **DB 端口**：容器内 `db:5432`，宿主映射 **5433**（避开本地 pg）。`DATABASE_URL` 里写服务名 `db:5432`，不是 5433。
- **首启顺序**：`main.py` 的 lifespan 跑 `alembic upgrade head`（迁移里含 `CREATE EXTENSION vector`，先于建表）再 seed。**改 schema 走迁移，不要用 `create_all`。**
- **热更**：`app/` 是 bind-mount + `--reload`，改 Python 直接生效。**改 `requirements.txt` 才需要 `--build`。**
- **宿主跑不了后端**：Python 3.14 + 无 pip + 无本地 Postgres。不要试图在宿主 `pip install`。
- **compose 里的 `POSTGRES_PASSWORD: app` 是本地开发口令。** 生产必须走 secret 注入，不要原样搬上服务器。
- **成本记账按 Anthropic 价目**（`routers/variants.py` 的 `_MODEL_LABEL` 按 model_id 子串映射）。接非 Anthropic 厂商后成本估算会不准，功能不受影响。

### 前端健壮性原语（别裸写 `.then()`）

`hooks/useAsyncData`（loading / error / reload）· `components/AsyncBoundary`（三态）· `ErrorBoundary` + `GlobalErrorNotifier`（全局兜底）。新页面、新调用一律照用。

---

## 6. 前端 dev-only 约定

`frontend/src/dev-only/` 存放**仅开发期使用**的资产：

- `dev-only/ComponentsPage.tsx` —— 组件走查页，用于视觉回归
- `dev-only/mocks/` —— 假数据（`@akun_demo`、`SAHM-X` 等虚构实体）

`/components` 路由由 `import.meta.env.DEV` 门禁，**生产构建中该分支连同动态 import 一并被摇除**，mock 数据不会进入产物。

**生产代码不得从 `dev-only/` import。** 违反会让假数据混进线上。

---

## 7. 合规护栏在哪

- `app/compliance/rules.py` —— 词表：`BANNED_WORDS`（硬拦截）+ `SOFT_FLAG_WORDS`（软提示）。**调合规口径改这两张表。**
- `app/compliance/engine.py` —— `scan_compliance(text)` 产出 `pass/soft/blocked` 三态。
- `app/compliance/injection.py` —— 抗注入：抓取内容一律当不可信数据，`wrap_untrusted` 包裹隔离后才能进 prompt。
- `POST /api/compliance/check` —— 对任意文案返回三态 + 命中详情，供内部自检。

> ⚠️ 这些只是**确定性护栏**，消解不了红线 **A-1** 的业务责任。正式对外投放仍需法务书面确认——见 [`project-overview.md`](project-overview.md) §2。
