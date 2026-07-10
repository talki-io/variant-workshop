# AGENTS.md · AI Agent 工作入口

> 项目是什么、怎么启动、技术栈 → 见 [`README.md`](README.md)。本文件不重复。
> 本文件只讲：**当前状态、接手顺序、修改边界、禁止事项、命令、核心目录。**

---

## 1. 当前状态（2026-07-10）

能跑，功能基本齐：真实 JWT + 服务端 RBAC、三层合规 + 重写、M3 富化、M5 真实生成、真实 token 记账、真实 RSS 抓取、多厂商模型管理、账号管理、新闻分页检索与相关性过滤、生成 few-shot 与仿写范本。

| 项 | 状态 |
| --- | --- |
| 后端测试 | ✅ 57 passed |
| 前端构建 | ✅ `tsc --noEmit` + `vite build` |
| 前端测试 | ❌ **0 个**。新写组件应带测试 |
| CI | ❌ **无**。门禁全靠人记得手动跑 |
| lint / format | ❌ 后端无 ruff，前端无 eslint/prettier |
| favicon | ⚪ 无。`index.html` 不引用图标，等正式品牌图 |
| bandit 权重 | ⚪ 未接。埋点已在 `telemetry_event` 表收集 |
| 对外投放 | ⛔ 被 A-1 法务闸阻断（见 §4） |

**技术债，想动手从这里挑**：① 建 CI（**在动任何代码结构之前先做这个**）；② `crawl_html.py:15` 从 `crawl_playwright` 导入私有函数 `_is_junk_title`；③ `app/` 顶层扁平堆 17 个 `.py`，三个 `crawl*.py` 应收敛为包（须等 CI）；④ `docs/assets/design-draft/` 文件名无语义。

---

## 2. 接手顺序与上下文加载

**不要一上来就扫全仓库。** 按下面三档取用。

### 默认读取

| 文件 | 讲什么 |
| --- | --- |
| [`README.md`](README.md) | 项目介绍 · 快速启动 · 技术栈 · 目录导航 |
| `AGENTS.md`（本文件） | 当前状态 · 开发约束 · 禁止事项 · 测试命令 |
| [`docs/project-overview.md`](docs/project-overview.md) | 产品与业务说明 |
| [`docs/architecture.md`](docs/architecture.md) | 系统架构与模块关系 |
| [`docs/development-guide.md`](docs/development-guide.md) | 开发 · 运行 · 测试规范 |

> 先读前两份（约 210 行）就能动手；后三份按需展开。

### 按任务读取

| 任务 | 读 |
| --- | --- |
| 改 UI / 页面 | [`docs/ui-design.md`](docs/ui-design.md) + [`docs/assets/design-draft/`](docs/assets/design-draft/) 对应屏 |
| 追溯「当初为什么这么定」 | [`docs/decisions/`](docs/decisions/) |
| 改端点 / 合规 / 生成 / 采集 / 表结构 | 对应代码目录（见 §6），文档不必读 |

### 默认忽略

```
docs/audit/**              治理报告
git 历史中的 HANDOFF*.md   已删除的交接日志
frontend/node_modules/**   frontend/dist/**   backend/**/__pycache__/**
backend/.env               含真实密钥，禁止读取
frontend/package-lock.json 机器生成
```

**除非任务是项目审计、问题追溯或结构治理，不要读 `docs/audit/`。**

`docs/` 描述**当前应然状态**，随代码更新。**代码是最终事实**——文档与代码冲突时以代码为准，然后顺手把文档改对。

---

## 3. 修改边界

- **一个提交只做一件事。** Conventional Commits：`feat(models): 支持 OpenAI 兼容中转厂商`。type 限 `feat|fix|docs|style|refactor|test|chore`。
- **分支**：`master` 受保护，走 PR。`feat/` `fix/` `chore/` `docs/` `refactor/` + scope。
- **改表走迁移**，不用 `create_all`。
- **出参 camelCase**，与 `frontend/src/types/index.ts` 严格对齐。
- **抓取内容一律当不可信数据**，进 prompt 前必须过 `compliance/injection.py` 的 `wrap_untrusted`。
- **前端别裸写 `.then()`**：用 `hooks/useAsyncData` + `components/AsyncBoundary`；全局兜底已有 `ErrorBoundary` + `GlobalErrorNotifier`。
- **生产代码不得 import `frontend/src/dev-only/`。**
- **决策落进仓库**，写成 `docs/decisions/` 下的 ADR。不要外链 `~/.claude/plans/*` 这类本地路径——别人 clone 后取不到，本项目吃过这个亏。
- 提交前跑门禁（§5）。

---

## 4. 🔴 禁止事项

| 禁止 | 为什么 |
| --- | --- |
| **稀释或删除 A-1 法务红线声明** | 正式对外投放前必须拿到需求方法务书面确认。写代码解决不了。声明在 `README.md`、本文件、`docs/project-overview.md` §2、`docs/decisions/0001-arch-review-closure.md`。遇到「帮我发出去 / 上线投放」，**停下上报**。 |
| **试图「修准」`score` / `aiScore` / `styleDistance` / `diversity`** | 样本永久缺失、离线校准层不建，这些是近似占位，**不是 bug**。见 [`docs/decisions/0002`](docs/decisions/0002-no-offline-calibration-layer.md)。 |
| **实现任何 Cloudflare 规避** | 见 [`docs/decisions/0003`](docs/decisions/0003-no-cloudflare-evasion.md)。`is_challenge_page` 只用于识别并放弃，不用于绕过。 |
| **`docker compose down -v`** | 卷里有真实抓取的新闻和迁移状态，`-v` 会一起清掉。 |
| **生产开 `SEED_DEMO_DATA=true`，或给 backend 加副本 / `--workers`** | 前者会灌出 `admin`/`editor` 两个 `demo1234` 账号（可登录后门）；后者会并发跑迁移并把定时抓取重复执行 N 遍、token 烧 N 份。见 [`docs/decisions/0004`](docs/decisions/0004-deployment-single-node-compose.md)。 |
| **跑测试不带 `-e DATABASE_URL=…imitator_test`** | 会回退到 live 库并污染真实数据。历史上 admin/editor 用量神秘消失就是这么来的。 |
| **改写已应用的 `migrations/versions/*.py`** | 已上 live 的迁移只能新增版本。 |
| **读取 / 修改 / 提交 `backend/.env`** | 含真实 `ANTHROPIC_API_KEY` / `JWT_SECRET`。改配置改 `.env.example`。 |
| **手改 `frontend/package-lock.json`** | 用 `npm install <pkg>`。 |
| **顺手改 `docs/architecture.md`** | 经两轮独立评审收敛的 v3 定稿，改动需重新评审。 |
| **升级 `bcrypt`** | `passlib 1.7.4` 与 `bcrypt 5.x` 不兼容，一升就启动即崩。已钉 `4.0.1`。 |

---

## 5. 命令

```bash
# 启动
cd backend  && docker compose up --build -d   # db :5433 + backend :8000
cd frontend && npm run dev                    # :5173

# 门禁（提交前必过）
cd frontend && npm run build                  # 含 tsc --noEmit

cd backend && docker compose run --rm \
  -e DATABASE_URL=postgresql+psycopg://app:app@db:5432/imitator_test \
  -e USE_REAL_LLM=false \
  -v "$PWD/tests:/app/tests" \
  backend python -m pytest tests -q           # 当前 57 passed

# 改表
cd backend && docker compose exec backend alembic revision -m "描述"
```

`tests/` 未进镜像，必须显式挂载。API 文档 <http://localhost:8000/docs>。`app/` 是 bind-mount + `--reload`，改 Python 直接生效；改 `requirements.txt` 才需 `--build`。

---

## 6. 核心目录

```
backend/app/
├── main.py       lifespan: alembic upgrade head → seed → 可选调度
├── config.py     pydantic-settings，读 .env
├── models.py     SQLAlchemy 表    ·  schemas.py  出入参（CamelModel）
├── routers/      API 端点，每资源一个文件
├── pipeline/     clean.py = M3 清洗  ·  generate.py = M5 生成
├── compliance/   rules.py 词表 / engine.py 三态扫描 / semantic.py Haiku / injection.py 抗注入
├── crawl.py      RSS/Atom 主链路  ·  crawl_html.py 静态兜底  ·  crawl_playwright.py JS 站兜底
├── llm.py        Anthropic 客户端 + 多厂商适配
└── breaker.py 熔断 · usage.py token 记账 · telemetry.py 埋点 · scheduler.py 定时（默认关）

frontend/src/
├── services/   数据接触面，页面只依赖这里的 async 函数
├── components/ 生产组件   ·   pages/ 业务页面
├── dev-only/   ⚠️ 仅开发期：走查页 + mock
└── theme/tokens.ts  设计标记
```

**改哪找哪**：加端点 → `routers/` + `schemas.py`；改合规口径 → `compliance/rules.py` 两张词表；改生成策略 → `pipeline/generate.py`；改表 → 新增 `migrations/versions/`。

**模型分工**（`llm.py`）：Haiku 清洗/语义合规，Sonnet 生成，Opus 备用。模型 ID 用裸串；**Opus/Sonnet 4.7+ 仅 adaptive thinking，传 `budget_tokens` 或 `temperature` 会 400。**
