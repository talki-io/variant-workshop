# 项目治理报告（PROJECT_GOVERNANCE_REPORT）

- **日期**：2026-07-10
- **分支**：`chore/project-restructure`（基线 `0ccb4c5`，未提交）
- **范围**：项目结构重构 + 上下文治理 + 工作树精简。**未改业务逻辑，未重写 git 历史。**

本文件是本次治理的**唯一可追溯报告**，取代过程中产生的全部阶段性文档（见 §9）。

---

## 1. 重构原因

治理前的仓库有四个结构性问题：

1. **无入口。** 137 个文件的双栈项目没有 `README.md`。三份文档各自声称「先读我」，且互相指认的阅读顺序彼此矛盾。
2. **规范与日志混淆。** 4 份 `HANDOFF-*.md`（730 行）是时序工作日志，却和权威设计一起摆在根目录。其中 `HANDOFF-FIXME.md` 是一份已 100% 完成、仍叫「待修复清单」的文件；`HANDOFF-FRONTEND.md` 的核心结论「不接后端」早已被推翻。
3. **生产代码依赖 mock。** 喂假数据的组件走查页 `/components` 挂在生产路由上。
4. **新人跑不起来。** `backend/.env.example` 缺 `USE_REAL_LLM` 与 `CRAWL_SCHEDULER_ENABLED` 两个键。

仓库名 `ai-agent-imitator` 亦有误导——它不是 Agent 框架，是一条确定性的文案生成流水线。

**已于 2026-07-10 完成改名**：GitHub 仓库 `talki-io/ai-agent-imitator` → `talki-io/variant-workshop`（旧 URL 由 GitHub 自动重定向）；本地目录 `~/aiProject/ai-agent-imitator` → `~/aiProject/variant-workshop`；`git remote` 已切到新 URL；仓库描述补齐。数据库名 `imitator` 刻意保留（见 §8）。

---

## 2. 主要目录变化

| Before | After | 说明 |
| --- | --- | --- |
| （无） | `README.md` | 唯一入口 |
| （无） | `AGENTS.md` | AI Agent 工作入口 |
| `DESIGN.md` | `docs/architecture.md` | 正文一字未改 |
| `UI-DESIGN.md` | `docs/ui-design.md` | — |
| `ARCH-REVIEW-DEFECTS.md` | `docs/decisions/0001-arch-review-closure.md` | ADR 化 |
| `HANDOFF*.md`（4 份） | **已删除** | 有效规则先提炼（见 §4） |
| `images/design-draft/` | `docs/assets/design-draft/` | 现行设计基准，非历史资料 |
| `images/corrected-diagram/` | **已删除** | 沟通/bug 截图 |
| `frontend/desktop.png` | **已删除** | 第三方网站截图 |
| `frontend/src/mocks/`<br>`frontend/src/pages/ComponentsPage.tsx` | `frontend/src/dev-only/` | `/components` 路由由 `import.meta.env.DEV` 门禁，生产构建摇除 |
| 根目录 7 份 `.md` | 根目录 2 份 | — |

其它：`.env.example` 补齐两键；三份 `.gitignore` 按「根=公共，子=独有」重划、零重复；`/--full-page` 遗留规则删除；`index.html` 的 `/vite.svg` 死引用删除（仓库无正式品牌图标，不留占位图）。

---

## 3. 删除与保留原则

**删除前必须满足全部条件**：① 代码、配置、当前文档中零引用；② 非生产资源；③ 非当前 UI 设计基准；④ 属历史日志 / 沟通截图 / 已完成任务记录。

**图片逐张打开确认内容，不靠文件名判断。** 这一步改变了结论：

- 5 张 `Snipaste_*` 是局部运行截图与 bug 截图 → 删。
- `desktop.png` 是**第三方印尼股票网站（BBCA 行情页）截图**，含真实股票代码，正是 `docs/ui-design.md` 红线禁止的内容 → 删。
- 7 张 `design-draft/` 是**高保真设计基准**（`3e96c065-….png` 即三栏布局稿，与实现代码一一对应），触发条件 ③ 否决 → **保留**，并移出归档区、在 4 处建立活引用。

**永不删除**：`backend/.env`（含真实密钥，正确 untracked）、`package-lock.json`（可复现构建）、A-1 法务红线声明。

**最终删除的 git 跟踪文件共 10 个**：4 份 `HANDOFF*.md` + 6 张截图（256 KB）。

---

## 4. 有效规则迁移位置

删除历史文档前逐份提炼。**没有一条仍然有效的规则随日志消失。**

| 规则 | 原出处 | 现位置 |
| --- | --- | --- |
| 🔴 A-1 法务红线（对外投放前需法务书面确认） | `HANDOFF.md` §3 | `README.md` · `AGENTS.md` §4 · `docs/project-overview.md` §2 · `decisions/0001` |
| 产品定位、已拍板决策、一期底线 | `HANDOFF.md` §2/§5/§6 | `docs/project-overview.md` |
| 启动步骤、演示账号 | `HANDOFF-BACKEND.md` §2 | `docs/development-guide.md` |
| bcrypt 4.0.1 钉版 · DB 端口 · 首启顺序 · 热更 · 宿主跑不了后端 | `HANDOFF-BACKEND.md` §7 | `docs/development-guide.md` §5 |
| **样本永久缺失 → `score`/`aiScore`/`styleDistance`/`diversity` 是近似占位，不是 bug** | `HANDOFF-FIXME.md` §3 | **`decisions/0002-no-offline-calibration-layer.md`** |
| **不做 Cloudflare 规避** | `HANDOFF-BACKEND.md` §9.7 | **`decisions/0003-no-cloudflare-evasion.md`** |
| **禁止 `docker compose down -v`** | `HANDOFF-FIXME.md` §4 | `docs/development-guide.md` §5 · `AGENTS.md` §4 |
| **测试必须带 `-e DATABASE_URL=…imitator_test`**（否则污染 live 库） | `HANDOFF-FIXME.md` §4 | `docs/development-guide.md` §4 · `AGENTS.md` §4 |
| 模型 ID 裸串；Opus/Sonnet 4.7+ 传 `budget_tokens`/`temperature` 会 400 | `HANDOFF-FIXME.md` §4 | `docs/development-guide.md` §5 · `AGENTS.md` §6 |
| 前端健壮性原语（别裸写 `.then()`） | `HANDOFF-FIXME.md` §4 | `docs/development-guide.md` §5 · `AGENTS.md` §3 |
| 成本记账按 Anthropic 价目，接他厂后估算不准 | `HANDOFF-BACKEND.md` §9.7 | `docs/development-guide.md` §5 |
| 前端不提供角色切换开关 | `HANDOFF-FIXME.md` | `docs/development-guide.md` §2 |

---

## 5. 验证结果

| 检查 | 结果 |
| --- | --- |
| 前端 `npm run build`（含 `tsc --noEmit`） | ✅ 通过 |
| 后端 `pytest` | ✅ 57 passed |
| Markdown 死链（逐链接校验目标存在） | ✅ 0 |
| 代码/配置失效路径 | ✅ 0 |
| 生产产物含 mock 数据 | ✅ 无 |
| 生产产物含 `/vite.svg` | ✅ 无 |
| `.gitignore` 规则有效性（10 条关键路径 `git check-ignore`） | ✅ 全部通过 |
| 根目录非目录文件数 | ✅ 3 |
| A-1 红线声明处数 | ✅ 4 |

---

## 6. Git 恢复说明

**未提交、未重写历史、未使用 `git filter-repo`。删除的一切都在 git 里。**

```bash
# 找到删除提交
git log --diff-filter=D --oneline -- 'HANDOFF*.md'

# 查看被删文件内容
git show <sha>^:HANDOFF-BACKEND.md

# 恢复单个文件
git checkout <sha>^ -- HANDOFF-BACKEND.md
```

被删截图同理：`git show 0ccb4c5:frontend/desktop.png > desktop.png`。

---

## 7. 最终项目结构

```
variant-workshop/
├── .gitignore                仓库级公共规则
├── README.md                 项目介绍 · 快速启动 · 技术栈 · 目录导航
├── AGENTS.md                 AI Agent 入口：状态 · 接手顺序 · 约束 · 禁令 · 命令
├── backend/
│   ├── .gitignore            后端独有规则
│   ├── app/                  main · config · models · schemas · routers/
│   │                         pipeline/ · compliance/ · crawl*.py · llm.py
│   │                         breaker · usage · telemetry · scheduler
│   ├── migrations/           Alembic（11 个版本）
│   └── tests/                pytest（57 passed）
├── frontend/
│   ├── .gitignore            前端独有规则（含 _*.mjs）
│   └── src/
│       ├── services/         数据接触面，真实 API，不含 mock
│       ├── components/       生产组件
│       ├── pages/            业务页面
│       └── dev-only/         ⚠️ 仅开发期：走查页 + mock，生产不打包
└── docs/
    ├── project-overview.md   产品与业务
    ├── architecture.md       系统架构与模块关系（权威设计 v3）
    ├── development-guide.md  开发 · 运行 · 测试规范
    ├── ui-design.md          UI 设计规则
    ├── assets/design-draft/  7 张设计基准图
    ├── decisions/            ADR 0001 · 0002 · 0003
    └── audit/                本报告（默认不读）
```

---

## 8. 遗留事项

- 后端 `crawl_html.py:15` 跨模块私有导入 `_is_junk_title`；`app/` 顶层扁平堆 17 个 `.py`。
- `docs/assets/design-draft/` 文件名无语义，重命名需逐张核对屏幕归属。
- 无正式品牌 favicon；`index.html` 当前不引用图标。
- 数据库名仍为 `imitator`（`docker-compose.yml` / `config.py` / `conftest.py`）。改名要动 compose、`.env`、已有数据卷与 11 个迁移，且卷里有真实抓取的新闻数据——**刻意保留**，命名统一的价值在人读到的名字，不在连接串。

---

## 9. 本报告取代的阶段性文档

以下文档在治理过程中产生，结论已并入本文件，均已删除（从未提交，不在 git 历史中）：

`project-analysis-report.md` · `cleanup-report.md` · `project-refactor-plan.md` · `file-cleanup-proposal.md` · `PROJECT_MANAGEMENT_REPORT.md` · `PROJECT_CONTEXT_CLEANUP_REPORT.md` · `docs/archive/README.md`
