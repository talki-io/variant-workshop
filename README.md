# variant-workshop（变体工坊）

印尼股市营销文案变体系统 · **内部出稿加速器**。

输入素材员的历史爆款（40–50 条、多账号）+ 自动采集的印尼股市新闻，产出有真人味、贴热点、过合规底线的文案变体草稿，供素材员选改。把「想角度 + 写多版」从小时级压到分钟级。

**它不是「爆款自动机」。人始终在选稿与合规这一环。**

> 🔴 **红线 A-1：正式对外投放前，必须先拿到需求方的法务书面确认。**
> 开发、联调、内部试用全部放行；真实对外发布等法务签字，遇到上报。
> 详见 [`docs/decisions/0001-arch-review-closure.md`](docs/decisions/0001-arch-review-closure.md)。

---

## 核心功能

| 模块 | 做什么 |
| --- | --- |
| 新闻采集 | RSS/API 优先、Playwright 兜 JS 站，定时抓取印尼财经源，清洗 + 相关性打标 |
| 文案生成 | 按目标账号调性，few-shot + 风格锚定，一次产出多个变体 |
| 合规扫描 | 三层：禁词硬拦截 → Haiku 语义合规 → 软提示；抓取内容抗注入 |
| 成本护栏 | token 记账、消耗看板、配额与限流、熔断 |
| 模型管理 | 多厂商模型库，运行时切换 |

---

## 技术栈

| 层 | 选型 |
| --- | --- |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · Postgres 16 + pgvector |
| 采集 | feedparser · BeautifulSoup · Playwright · APScheduler |
| 模型 | Anthropic（Haiku 清洗/合规；Sonnet 生成；Opus 备用） |
| 前端 | Vite · React 18 · TypeScript · Ant Design 5（含 X 对话 / Charts 图表） |
| 部署 | Docker Compose（单机；生产编排见 [`deploy/`](deploy/README.md)） |

**零模型训练。** 全系统基于 prompt + 检索 + 规则——历史爆款只有 40–50 条，够做 few-shot 与风格锚定，不够训练任何模型。

---

## 快速启动

**后端（Docker）**

```bash
cd backend
cp .env.example .env          # 填一个随机 JWT_SECRET；DATABASE_URL 默认即可
docker compose up --build -d  # db(pgvector, :5433) + backend(:8000)
curl localhost:8000/health    # {"status":"ok"}
```

**前端（宿主）**

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173，proxy /api → :8000
```

演示账号、测试命令、环境变量详解、已知的坑 → [`docs/development-guide.md`](docs/development-guide.md)。

---

## 目录导航

```
variant-workshop/
├── AGENTS.md         AI Agent 工作入口 —— Agent 先读这个
├── backend/          FastAPI 服务
│   ├── app/          业务代码（routers / pipeline / compliance / crawl*）
│   ├── migrations/   Alembic
│   └── tests/        pytest
├── frontend/         React SPA
│   └── src/
│       ├── components/   生产组件
│       ├── pages/        业务页面
│       ├── services/     API 层（真实 fetch，不含 mock）
│       └── dev-only/     ⚠️ 仅开发期：走查页 + mock，生产构建不打包
├── deploy/           生产编排（compose + 部署手册），开发不用
└── docs/             文档（见下）
```

| 文档 | 用途 |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | **AI Agent 入口**：当前状态、接手顺序、修改边界、禁止事项、测试命令 |
| [`docs/project-overview.md`](docs/project-overview.md) | 产品定位、已拍板的决策、一期底线 |
| [`docs/architecture.md`](docs/architecture.md) | 唯一权威设计（v3 定稿） |
| [`docs/development-guide.md`](docs/development-guide.md) | 怎么跑、怎么测、已知的坑 |
| [`deploy/README.md`](deploy/README.md) | 生产部署手册：首次部署、建管理员、备份、成本闸门、排障 |
| [`docs/ui-design.md`](docs/ui-design.md) | UI 设计语言与逐屏规范（配 [`docs/assets/design-draft/`](docs/assets/design-draft/) 设计基准图） |
| [`docs/decisions/`](docs/decisions/) | ADR：架构决策记录 |
| [`docs/audit/PROJECT_GOVERNANCE_REPORT.md`](docs/audit/PROJECT_GOVERNANCE_REPORT.md) | 项目治理报告（追溯用，日常开发不必读） |

**历史交接日志已于 2026-07-10 从工作树移除**，可在 git 历史中检索（`git log --diff-filter=D -- 'HANDOFF*.md'`）。其中仍然有效的规则已提炼进上表文档与 `docs/decisions/`。

AI Agent 接手请先读 [`AGENTS.md`](AGENTS.md) —— 它规定了默认读取、按任务读取与默认忽略的文件范围。
