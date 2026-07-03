# 交接 · 待修复清单（给新开的 Claude 窗口）

> 目的：项目能跑，但**页面上很多交互是前端本地态 / 占位 / 死按钮**——因为对应的后端写回端点没建，此前几轮聚焦在「读取 + 生成管线」。本文件列出**未真正实现的功能**与修复方案，供你接手。
> **先读**：本文件 → `HANDOFF-BACKEND.md`（§1–§7j，架构/端点/约定/已实测）→ 需要背景再看 `DESIGN.md`（v3 权威设计）。记忆索引在 `~/.claude/projects/.../memory/`。

---

> ## ✅ 已收口（2026-07-02，本轮）——§5 的 1–4 全部做完并 e2e 实测
> 新增后端写回端点（全部 camelCase + RBAC + pytest，无需改表故无新迁移）：
> - `PUT /api/news/{id}/label`（editor/admin，记 `relevance` 埋点）
> - `POST/PUT/DELETE /api/sources`（admin，PUT 为部分更新含 enabled 开关）
> - `PUT /api/quota`（admin，globalUsed/Pct 为派生量不接受写入）
> - `PATCH /api/variants/{id}`（编辑正文→服务端重跑合规→记 `edit`）
> - `POST /api/variants/{id}/regenerate`（按维度重生成，原地替换保 id/rank；过熔断+配额护栏；记 `regenerate`+token 记账；离线库内轮换）
>
> 前端接线（`services/index.ts` 加 `labelNews/createSource/updateSource/deleteSource/updateQuota/editVariant/regenerateVariant`）：
> - NewsPage 打标（乐观更新+失败回滚）；CrawlQuotaPage 增删改/启用开关/保存配置全调真端点；删了「查看全部用户配额」死链。
> - VariantCard 行内编辑（TextArea+保存/取消，保存后回填服务端合规结果）+ 重新生成（loading，复用最近 prompt）。
> - ChatPanel 快捷 chips 现带 modifier 触发一次生成；Sender 加「引用新闻」→跳新闻库。
> - HeaderBar：搜索框回车跳 `/news` 带关键词（NewsPage 读 `location.state.q`）；铃铛去掉假的 8→「暂无新通知」Popover；今日 token 徽标 admin 读 `/api/quota` 真实自用量、editor 隐藏；头像接真实退出下拉。
> - 登录页去掉非功能「记住我」；「忘记密码」改提示联系管理员。
> - **§2.5 dev 角色切换已删除**（连同 `AuthContext.setRole`）——它只切前端视图、服务端仍按真实角色，误导。验证权限请用 editor 账号登录。
>
> **实测**：pytest 41 绿（`-e USE_REAL_LLM=false`，原 35 中 2 条过期断言已改鲁棒）；`npm run build` 通过；headless（google-chrome/agent-browser）实测 admin/editor 全页 0 console error、新闻打标点击落库、quota 保存 toast、editor 只见文案生成/新闻库且无 token 徽标；真实 LLM 走通 generate→edit(soft→pass)→regenerate。
>
> **仍未做**：§5 的 5（看板今日 KPI 仍合成历史数据；bandit 框架）、§2.4 备注不变；红线 A-1 不变。

---

> ## ✅ 生成会话持久化 + 恢复（2026-07-02，第二轮反馈）
> **问题**：工作台生成的变体只活在 React state，切模块/刷新即丢（数据其实已入 `variants` 表，但无用户/prompt/来源归属、无会话分组、无读取端点，取不回）。与「产出草稿供选改」定位冲突。
> **做法（DB 支撑，非 localStorage）**：
> - 迁移 `0003`：新表 `generation_session`（id/user/tone_id/prompt/source_headline/diversity/created_at）+ `variants.session_id`（nullable，种子/离线库存变体为 NULL 不进历史）。
> - 真实生成路径：建会话行 → 产出变体挂 `session_id` → 返回 `sessionId`；`GenerateIn` 加可选 `sourceHeadline`（引用新闻时带上）。
> - 新端点 `GET /api/variants/sessions?limit=N`：当前用户最近会话（含变体，最新在前，按 user 隔离）。
> - 前端：GeneratePage 首屏拉 `getSessions()`，有历史则**自动恢复最近一次**（调性+变体+聊天气泡+lastPrompt）；ChatPanel 顶部加「历史 (N)」下拉可切换恢复任意历史会话；生成成功后刷新历史列表。
> - ⚠️ 离线生成（`USE_REAL_LLM=false`）不建会话（会污染共享种子库），故会话创建仅真实路径；测试用直插 DB 验证读取端点（隔离/归属）。
> **实测**：pytest **42 绿**；`npm run build` 通过；真实 LLM 走通「generate→落库会话(含 sourceHeadline)→GET sessions 返回」；headless 实测：/generate 首屏自动恢复上次 5 条变体、**切到 /news 再回来 + 硬刷新内容都不丢**、历史下拉显示 (1)、0 console error。

---

> ## ✅ 文案生成页三栏改版（2026-07-02，按 gptimages2.0 新设计图）
> 设计图 `images/design-draft/3e96c065-2497-4127-a312-33c8e50bf777.png`：文案生成从「两栏(对话｜变体)」改为**「三栏(历史记录｜对话｜变体)」**，历史从 ChatPanel 下拉升级为**左侧独立面板**。
> - 新组件 `pages/GeneratePage/HistoryPanel.tsx`：标题「历史记录」+ 搜索历史任务(客户端 filter) + 排序(按时间/按收藏) + 会话卡片(prompt 标题 2 行截断 / 调性 handle / 相对时间「今天/昨天/前天 HH:MM」/「已生成」标签 / 收藏星标 / 「…」删除菜单 / 选中蓝色高亮) + 「查看更多历史」(limit 递增)。
> - ChatPanel 移除历史下拉（回到纯 ToneSelector）；GeneratePage 改三栏：左 `0 0 300px` 历史 / 中 `0 0 34%` 对话 / 右 `flex 1` 变体。
> - **收藏/删除做成真功能**（不做死按钮）：迁移 `0004` 给 `generation_session` 加 `favorite` 列；端点 `PATCH /api/variants/sessions/{id}`(收藏，仅本人)、`DELETE /api/variants/sessions/{id}`(删会话+其变体，仅本人)；`list_sessions` 改为收藏优先→最新在前；`GenerationSessionOut` 含 `favorite`。删除当前会话会清空工作台；删除也顺带满足了之前「会话无清理策略」的 TODO。
> - 前端：`services` 加 `toggleSessionFavorite/deleteSession`；收藏乐观更新+回滚、删除走 `modal.confirm`。
> **实测**：pytest **42 绿**（session 用例扩含 favorite/delete/ownership，admin 改删他人会话→404）；`npm run build` 通过；headless(1600×940) 实测三栏布局对齐设计图、点历史卡恢复、收藏星标切换、删除确认弹窗、0 console error。
>
> **消耗看板：UI 对齐设计图 (4) + 数据接真（2026-07-02）**：
> - UI 修正：KPI 标题加 ⓘ Tooltip、数字放大加粗、趋势色按指标语义（token/成本↓=绿、用户↑=绿）、Y 轴缩写 `2M/500K`（原 `2000000`）、图标题「近 N 天…」+「按天/按周」真实聚合下拉；Top10 数值改自适应 `abbrNum`（K/M，原固定 M 导致真实小值显示 `0.00M`）。
> - **数据接真**：`routers/dashboard.py` 整段重写——KPI/趋势/Top用户/明细全部由真实 `token_usage` 聚合（按天+模型、按用户累计、今日 vs 昨日趋势、配额从 QuotaConfig）。**删掉 `seed.py` 的假 token_usage（d1–d8 张伟等）+ live 库同步删除**；真实用户为 admin/editor/system。⚠️ 真实数据稀疏：目前只有今日一天用量，**趋势面积图会显得很空**（面积图需≥2天才成形），随使用天数累积自然填充——这是如实反映不是 bug。⚠️ quota 页的 UserQuota（张三/李四）仍是种子假用户，同类问题，未清（下一轮可比照处理）。
> - 实测：pytest **42 绿**；build 通过；live 生成 admin/editor 真实变体→记账→看板 Top10 显示 system/admin/editor 真实值、明细全真、0 console error。
> - ⚠️ 环境坑：本机 5173 被另一个项目 `ai-sixMajorDimensions-view`（六维诊股）占用；本项目前端现跑 **:5174**（`cd frontend && npm run dev` 自动选空闲口），后端 :8000 不变。别把 5173 的那个应用当成本项目。
>
> **配额页接真实数据 + 修复数据丢失 bug（2026-07-02，接上）**：
> - `routers/quota.py` 的「按用户配额使用情况」改为真实 `users` 表 + `user_tokens_today` 组装（自己置顶/其余按用量降序）；删 `seed.py` 的 UserQuota 假用户(张三/李四…)+live 库同步删。现只显示真实 admin/editor。
> - 🔑 **查出真实数据丢失根因**：`tests/test_quota.py::_cleanup_user` 无条件 `delete()` admin/editor 的 token_usage——测试共享 live 库，每跑一次 pytest 就把 admin/editor 真实用量清光（system 不受影响 → 现象是"真实用户行神秘消失"）。生产不跑测试所以数据安全。已改为**快照→清空→跑完恢复**（`_snapshot_and_clear`/`_restore`），实测 admin/editor 行现能扛过 pytest。残留：test_api 的 `_first_variant` 以 editor POST /variants 每次 pytest 新增 ~3 行 editor（真实生成非假用户）——共享库老问题，彻底隔离需独立测试库。

> **新闻库三栏化改版（同设计图 `design-draft/ChatGPT Image ...(3).png`）**：从「全宽列表 + 点击弹抽屉」改为**「左筛选栏+可滚动列表 / 右常驻『新闻详情』面板」两栏**。删 `NewsDetailDrawer.tsx`，新增 `NewsDetailPanel.tsx`（Card，标题/来源/关键事实/相关标的/角度提示/新鲜度/热度条/原文链接，底部固定「复制内容」[真·clipboard]+「用它生成」，空态提示）。NewsPage 改 `activeId` 选中态（按 id 从 list 派生详情，打标后自动同步）+ 首条自动选中 + 被筛掉自动改选。NewsCard 整卡可点选中（蓝色 ring 高亮）、操作按钮 stopPropagation、加「打标可选」灰字提示。⚠️注：agent-browser 合成鼠标点击 React 可能不接，验证卡片交互用 `el.click()` 派发真实事件（本会话通用坑）。实测 build 通过、5/5 详情字段、点卡切换详情、打标不误触选中、0 console error。

> **输入框改版（同设计图）**：ChatPanel 把 `@ant-design/x` 的 `Sender` 换成自定义输入框——工具栏(📎附件[点击提示即将开放，非死按钮]+引用新闻) → 多行 `Input.TextArea`(borderless, maxLength 1000, Enter 发送/Shift+Enter 换行) → 底部(左「N/1000」计数 + 右蓝色「发送」)。快捷 chips 补图标并对齐「缩短到IG长度」。实测发送链路(点发送/Enter→用户气泡+骨架屏+清空)正常、build 通过。⚠️注：生成中 antd 加载动画(Skeleton/Bubble)在 **dev 模式**会打一条 React "mix shorthand/non-shorthand background" 告警——源码零 `backgroundColor`，属 antd 内部、生产构建被剥离，非本改动引入。

---

---

## 0. 先跑起来 + 先自审

```bash
# 后端（Docker；已配 Anthropic key，真实生成开启）
cd backend && docker compose up -d          # db(pgvector,:5433) + backend(:8000)
# 前端
cd frontend && npm run dev                  # http://localhost:5173
```
账号 `admin` / `editor`，密码均 `demo1234`。后端 OpenAPI：http://localhost:8000/docs 。

**动手前先自己精确 audit**（本文件部分基于交接者记忆，以代码为准）：
```bash
cd frontend/src
grep -rn "onClick" --include=*.tsx | grep -v "=>"          # 可疑无处理器
grep -rn "message.success\|message.info" --include=*.tsx    # 占位确认（多数未落库）
grep -rn "<a " --include=*.tsx | grep -vE "href=|onClick="  # 死链
```
逐条对照下面的清单确认。

---

## 1. 根因：后端缺「写回」端点

现有后端只实现了**读 + 生成 + 采集触发 + 埋点**。以下写操作**没有端点**，所以前端只能改本地 state（刷新即丢），或按钮直接 no-op：

| 缺失端点 | 用途 | 前端受影响处 |
|---|---|---|
| `PUT /api/news/{id}/label` | 新闻打标（相关/不相关）落库 | NewsPage 👍👎 打标 |
| `POST /api/sources` | 新增抓取源落库 | CrawlQuotaPage 新增抓取源 Modal |
| `PUT /api/sources/{id}` | 编辑抓取源（名称/频率/启用等） | CrawlQuotaPage 源「编辑」+ 启用开关 |
| `DELETE /api/sources/{id}` | 删除抓取源 | CrawlQuotaPage 源「删除」 |
| `PUT /api/quota` | 保存配额/限流配置 | CrawlQuotaPage「保存配置」 |
| `PATCH /api/variants/{id}` 或生成变体 | 变体「编辑」「重新生成」 | VariantCard 编辑/重新生成按钮 |

**约定（务必遵守）**：
- 出参/入参一律 **camelCase**，与 `frontend/src/types/index.ts` 对齐；后端用 `app/schemas.py` 的 `CamelModel`（`alias_generator=to_camel`）。
- 改表结构走 **Alembic**（`backend/migrations/`，`alembic revision --autogenerate`，启动自动 `upgrade head`）——**不要再用 create_all**，也别 `docker compose down -v`（现在库里有真实数据）。
- 前端只经 `frontend/src/services/index.ts` 调后端；新端点在这里加 async 函数，页面调它，配 `useAsyncData`/`try-catch`（已有健壮性原语，见 `hooks/useAsyncData.ts`、`components/AsyncBoundary.tsx`）。
- 写操作权限：sources/quota 是 **admin-only**（后端加 `Depends(require_admin)`，见 `routers/sources.py` 现有写法）；news 打标 editor/admin 均可。

---

## 2. 前端占位 / 死按钮清单（逐条修）

按「影响 × 成本」排序，✅=已实现无需动，🔧=要修。

### 2.1 工作台 GeneratePage（`pages/GeneratePage/`）
- 🔧 **ChatPanel 的 Prompts 快捷 chips**（换个钩子 / 更口语 / 缩短长度 / 重新生成）：确认是否只填输入框还是真触发。应让它们**带 modifier 触发一次生成**（后端 `POST /api/variants` 可加可选 `modifier` 字段，或前端把 chip 文案拼进 prompt 重发）。
- 🔧 **Sender 的「引用新闻」按钮**：应打开新闻选择（或跳新闻库回带），当前多半 no-op。
- 🔧 **VariantCard「编辑」按钮**（`components/VariantCard.tsx`）：无 onClick。应支持行内编辑 body（编辑后可选记 `edit` 埋点 + 重新合规校验）。
- 🔧 **VariantCard「重新生成」按钮**：无 onClick。应对该条重新生成（调生成，带该变体维度），并记 `regenerate` 弱负埋点。
- ✅ 采用（confirm 已落库+埋点）、复制（clipboard）、发送生成（真实 Sonnet）。

### 2.2 新闻库 NewsPage（`pages/NewsPage/`）
- 🔧 **打标 👍👎**：`handleLabel` 现在只 `setData` 本地。需 `PUT /api/news/{id}/label` 落库 + 记 `edit`/relevance 埋点（M7 信号）。
- ✅ 搜索 / 来源筛选 / 时间范围 / 热度·时间排序 / 仅看未打标 / 详情抽屉 /「用它生成」跳转（均已实现）。
- 注：库里现已有 15 条真实 CNBC 新闻（交接者抓的）+ 5 条种子样例。

### 2.3 抓取与配额 CrawlQuotaPage（`pages/CrawlQuotaPage/`，admin）
- ✅ **立即抓取**：真实调 `POST /api/sources/{id}/crawl`（真源：CNBC/Detik/Antara/Investing）。
- 🔧 **新增抓取源**：Modal 提交后只加本地。需 `POST /api/sources`。
- 🔧 **编辑 / 删除抓取源**（Dropdown 菜单）：只改本地。需 `PUT/DELETE /api/sources/{id}`。
- 🔧 **启用开关 toggle**：只改本地。应 `PUT /api/sources/{id}` 持久化 enabled。
- 🔧 **「保存配置」按钮**：只 `message.success`。需 `PUT /api/quota` 落库（配额/阈值/熔断条件/全局预算）。
- 🔧 **「查看全部用户配额」链接**：no-op，按需实现或删除。
- 注：搜索API / Playwright 类型源抓取**后端未实现**（返回 400，故意，属下一轮）。

### 2.4 消耗看板 DashboardPage（`pages/DashboardPage/`，admin）
- ✅ 时间 Segmented 过滤、导出 CSV、图表、明细分页（均已实现）。
- ⚠️ **daily/topUsers/kpi 是合成历史数据**（种子日期 2025-05-27），只有明细表 `details` + 配额页反映真实记账。若要「今日 KPI 反映真实 token_usage」需改 `routers/dashboard.py` 由 SQL 聚合今日行——可做但注意种子历史数据要一并处理。

### 2.5 布局 / 登录（`layout/`, `pages/LoginPage.tsx`）
- 🔧 **HeaderBar**（`layout/HeaderBar.tsx`）：顶部**搜索框、通知铃铛、今日 token 徽标、面包屑**大概率静态/占位。按需接真实数据或删除（通知可做成读 telemetry/告警；token 徽标可读 `/api/dashboard` 或 `/api/quota`）。
- 🔧 **登录页「忘记密码」**：死链。实现或去掉。「记住我」未持久化（token 已存 localStorage，行为上会话已保持，可去掉该框或接真实语义）。
- ⚠️ **侧栏 dev 角色切换**（`layout/Sider.tsx` 的 `setRole`）：**只切前端菜单视图，不动 token**，切到 admin 后调 admin 端点仍会 403（服务端 RBAC 按登录账号真实角色）。要么删掉这个 dev 开关，要么改成「重新以对应账号登录」。真实验证权限请用 editor 账号登录。

---

## 3. 关键约束（不是 bug，别当 bug 修）

- 🔴 **红线 A-1**：系统在 OJK 监管市场批量产荐股营销文案，**正式对外投放前必须先拿到需求方法务书面确认**。技术侧三层合规消解不了业务责任。遇到「上线/对外发布」相关需求，停下上报。
- ⚠️ **生成质量上限（样本永久缺失，已确认不补）**：无「多调性语感指纹 / 模式库 / 风格参考向量」→ 只能**通用调性版**生成；变体的 `score`/`aiScore` 是**模型自评**，`styleDistance` 是由 aiScore 派生的**近似占位**（非真实向量距离），`diversity` 是维度组合近似。**这些不是要「修准」的 bug**——真值需要离线校准层，而校准层依赖样本。若产品要更准，只能是「拿到样本 → 建校准层」，不在本轮范围。
- **USE_REAL_LLM 开关**（`backend/.env`，现为 `true`）：真实生成/清洗走 Anthropic（已配 key）。关掉或无 key 时 `generateVariants` 回退灌库固定批次。**跑测试务必 `-e USE_REAL_LLM=false` 强制离线**（见下）。
- **bandit 奖励/权重**未实现：需真实采用埋点积累到一定量才有意义（`telemetry_event` 表已在收集 adopt/generate 等信号）。

---

## 4. 工程约定速查

- **后端结构**：`app/main.py`(lifespan: alembic upgrade + seed + 可选调度) / `routers/*`(每资源一个) / `schemas.py`(CamelModel) / `models.py`(SQLAlchemy) / `pipeline/`(clean=M3, generate=M5) / `compliance/`(rules+semantic+injection 三层) / `llm.py`(Anthropic 客户端+call helpers) / `usage.py`(token 记账) / `breaker.py`(熔断) / `scheduler.py`(APScheduler,默认关)。
- **模型分工**（`app/llm.py`）：Haiku=清洗/语义合规，Sonnet=生成，Opus 备用。模型 ID 用裸串（`claude-haiku-4-5`/`claude-sonnet-5`/`claude-opus-4-8`），Opus/Sonnet 4.7+ 仅 adaptive thinking（`budget_tokens`/`temperature` 会 400）。
- **测试（跑在独立库 imitator_test，永不碰 live 库）**：
  `cd backend && docker compose run --rm -e USE_REAL_LLM=false -e DATABASE_URL=postgresql+psycopg://app:app@db:5432/imitator_test -v "$PWD/tests:/app/tests" backend python -m pytest tests -q`。
  **现 42 用例全绿，改动后必须保持**。`tests/conftest.py` 会在测试库缺失时自动建库+迁移+seed（自愈，down -v 后无需手动建）。**务必带 `-e DATABASE_URL=...imitator_test`**——不带则回退到跑 live 库 imitator（会污染真实数据，正是之前 admin/editor 用量神秘消失的根因）。新写端点补测试（参考 `tests/test_api.py`）；`-e USE_REAL_LLM=false` 保证离线免费。
- **密钥**：`backend/.env`（已 gitignore），绝不硬编码；`.env.example` 只占位。
- **不要 `docker compose down -v`**：库里有真实抓取的新闻 + 迁移状态。改表用 Alembic 增量迁移。
- **前端健壮性原语已备**：`hooks/useAsyncData`（loading/error/reload）、`components/AsyncBoundary`（三态）、`ErrorBoundary` + `GlobalErrorNotifier`（全局兜底）。新页面/新调用照用，别裸 `.then()`。

---

## 5. 建议修复顺序（新窗口执行）

1. **后端写回端点四件套**：`PUT /api/news/{id}/label`、`sources` 的 `POST/PUT/DELETE`、`PUT /api/quota`。各加 schema + RBAC + Alembic（若需字段变更，多数不需要）+ pytest。
2. **前端接线**：`services/index.ts` 加对应函数；NewsPage 打标、CrawlQuotaPage 增删改+保存配置、启用开关 → 改成调真实端点（乐观更新 + 失败回滚/提示）。
3. **VariantCard 编辑 / 重新生成** + ChatPanel Prompts chips / 引用新闻按钮 接通。
4. **HeaderBar / 登录页占位**：接真数据或删除死元素；dev 角色切换按 §2.5 处理。
5. （可选）看板今日 KPI 改真实聚合；bandit 框架。
6. 全程保持 35+ 测试绿；每做完一块用 headless 或手动过一遍。

> 交接者已实测通过的部分（勿重复推翻）：JWT+RBAC、三层合规+重写、M3 富化、M5 真实生成、真实 token 记账、真实 RSS 抓取(CNBC/Detik/Antara/Investing)、前端健壮性、Alembic。详见 `HANDOFF-BACKEND.md §7b–§7j`。
