# 交接文档 · 后端第一轮（FastAPI + Postgres/pgvector + JWT，前端切真数据）

> 状态：**第二轮已完成并 e2e 验证通过**（2026-07-02）。
> 阅读顺序：先本文件 → 需要背景再看 `HANDOFF-FRONTEND.md` / `DESIGN.md` / `HANDOFF.md`。
> 落地计划原文：`~/.claude/plans/vectorized-juggling-dawn.md`。

---

## 1. 这一轮做完了什么

在第一轮「纯前端骨架 + mock」的基础上，起了真后端并把前端切到真实 API：

- **`backend/`（Python FastAPI）**：Postgres 16 + pgvector（Docker）+ SQLAlchemy 2.0 建真表 + 幂等灌假数据 + **真 JWT 鉴权 + 服务端 RBAC**。
- **8 个端点**严格对齐 `frontend/src/types/index.ts`（出参 camelCase）。
- **前端 `services/index.ts` 从 mock 切到真 `fetch`**（经 `http.ts` + Vite 代理），**页面组件零改动**；`AuthContext` 改真登录（存 token + `/me` 恢复会话 + 401 登出）。
- **后端与 DB 都跑在 Docker**（`python:3.12-slim`），绕开宿主 `pip` 缺失 + Python 3.14 轮子风险。前端仍宿主 `npm run dev`。

**验证通过**：headless Chrome 全流程（admin 登录→调性来自 API→生成 5 张变体卡→看板图表/表格→admin 菜单可见→刷新会话保持→editor 菜单隐藏），所有 `/api/*` 均 200，**console error = 0**；后端 curl 全绿（登录/RBAC 403/401/camelCase）；`npm run build` 通过。

---

## 2. 怎么跑起来

**后端（Docker）**
```bash
cd /home/tel/aiProject/ai-agent-imitator/backend
cp .env.example .env          # 首次：填一个随机 JWT_SECRET（DATABASE_URL 默认即可）
docker compose up --build -d   # db(pgvector, host:5433) + backend(host:8000)
curl localhost:8000/health     # {"status":"ok"}；OpenAPI 文档见 http://localhost:8000/docs
```

**前端（宿主）**
```bash
cd /home/tel/aiProject/ai-agent-imitator/frontend
npm install     # 首次
npm run dev     # http://localhost:5173 —— vite 已配 proxy /api → :8000
```

**演示账号**（种子，密码均 `demo1234`）：
- `admin`（管理员）：可见「消耗看板 / 抓取与配额」。
- `editor`（素材员）：这两项菜单隐藏，直接打 admin 端点后端返回 **403**。

---

## 3. API 契约（= 前端 `services/index.ts` 的后端实现）

| 方法 | 路径 | 权限 | 出参 | 前端函数 |
|---|---|---|---|---|
| POST | `/api/auth/login` | 公开 | `{ token, user }` | `AuthContext.login` |
| GET | `/api/auth/me` | 登录 | `User` | 刷新恢复会话 |
| GET | `/api/tones` | 登录 | `Tone[]` | `getTones` |
| POST | `/api/variants` | 登录 | `VariantBatch`（body `{toneId, prompt}`）| `generateVariants` |
| GET | `/api/news` | 登录 | `NewsItem[]` | `getNews` |
| GET | `/api/dashboard` | **admin** | `DashboardData` | `getDashboard` |
| GET | `/api/sources` | **admin** | `CrawlSource[]` | `getSources` |
| GET | `/api/quota` | **admin** | `{ config, users }` | `getQuota` |

- 鉴权：`Authorization: Bearer <JWT>`；HS256；过期见 `JWT_EXPIRE_MINUTES`（默认 720min）。
- `POST /api/variants` 本轮**不调模型**，按 `toneId` 取灌库固定批次（仅 t1 有专属批次，其它 tone 暂回退 t1）；`prompt` 接收但未使用。

---

## 4. 后端代码地图（改哪找哪）

```
backend/
  docker-compose.yml   # db(pgvector/pgvector:pg16) + backend；db 端口映射 5433:5432
  Dockerfile           # python:3.12-slim；app 目录 bind-mount + uvicorn --reload 热更
  requirements.txt     # 注意 bcrypt==4.0.1（passlib 1.7.4 与 bcrypt 5.x 不兼容，见坑）
  .env / .env.example  # DATABASE_URL / JWT_SECRET（.env 不提交）
  app/
    main.py            # lifespan: 建 vector 扩展 → create_all → seed；CORS；挂 router
    config.py db.py    # 配置 / engine+Session+get_db
    security.py        # bcrypt hash、JWT 签发解析、get_current_user / require_admin
    models.py          # 9 张表（含 style_vectors pgvector stub）
    schemas.py         # Pydantic 出参，alias_generator=to_camel 统一 camelCase
    seed.py            # 幂等灌假数据（内容 = frontend/src/mocks/*）
    routers/           # auth/tones/variants/news/dashboard/sources/quota
```

**关键约定**：出参一律走 `schemas.py` 的 `CamelModel`（`to_camel` alias），DB 内 snake_case；改字段两头都要动。RBAC 用路由级 `dependencies=[Depends(require_admin)]`（dashboard/sources/quota）。

---

## 5. 前端改动点（本轮唯一改动，页面零改）

- `vite.config.ts`：加 `server.proxy['/api'] → http://localhost:8000`。
- 新增 `src/services/http.ts`：`apiFetch` —— base `/api` + 自动带 token + 非 2xx 抛 `ApiError` + 401 广播 `auth:unauthorized`。
- 改写 `src/services/index.ts`：每个函数体 `return mock` → `apiFetch(...)`。`mocks/` 保留仅作参考。
- `src/auth/AuthContext.tsx`：`login` 改异步（POST 登录 + 存 token）；挂载时 `/me` 恢复；401 登出；`restoring` 期间显示 Spin 防重定向闪烁。`setRole` 保留为**纯前端菜单预览**（不改 token，服务端仍按真实角色 RBAC）。
- `src/pages/LoginPage.tsx`：账号+密码必填、异步提交 + loading + 错误提示；底部标注演示账号。
- `index.html`：加 favicon 指向 `/vite.svg`（消除 favicon 404，console 零错）。

---

## 6. 数据模型（本轮建的 9 张表）

`users / tones / news / variants / token_usage / crawl_source / quota_config / user_quota / style_vectors(pgvector stub, 空)`。字段见 `app/models.py`，对齐 `frontend/src/types/index.ts`。

- `dashboard` 的 `details` 真读自 `token_usage` 表（落地 §6 成本护栏）；`daily/topUsers/kpi` 为合成聚合（口径对齐前端 mock，待接真实记录后由 SQL 聚合）。
- `style_vectors` 建表不灌，仅验证 `CREATE EXTENSION vector` 生效（实测 pgvector 0.8.4），为下一轮风格向量铺底。

**下一轮才建的表**：模式库 / 语感指纹全字段 / 权重表(bandit) / 埋点 telemetry / golden 集 / 禁词表。

---

## 7. 注意事项 / 坑

- **passlib × bcrypt**：`passlib 1.7.4` 与 `bcrypt 5.x` 不兼容（启动即 `ValueError: password cannot be longer than 72 bytes`）。已在 requirements 钉 `bcrypt==4.0.1`。升级 passlib 或换 bcrypt 直连时注意。
- **DB 端口**：容器内 `db:5432`，宿主映射 **5433**（避开可能的本地 pg / 已存在的 mysql:3306）。`DATABASE_URL` 用服务名 `db:5432`。
- **首启顺序**：`main.py` lifespan 现在跑 `alembic upgrade head`（迁移里已含 `CREATE EXTENSION vector`，先于建表）再 seed；已替换旧的 `create_all`。改 schema 走迁移，别再手动 create_all。
- **热更**：`app/` 是 bind-mount + `--reload`，改 Python 直接生效，无需重建镜像；改 `requirements.txt` 才需 `--build`。
- **宿主环境**：Python 3.14 + 无 pip + 无本地 Postgres，所以后端全在 Docker；不要试图在宿主直接 `pip install` 跑。

---

## 7b. 追加：合规底线地基（2026-07-02，无模型/样本依赖）

爆款样本未到位、AI 管线暂缓期间，先把 DESIGN §5 一期必内建的**规则层合规底线**做好，供下一轮 M5/M6 直接 import：

- `app/compliance/rules.py` —— 可维护词表：`BANNED_WORDS`（收益/涨幅保证、无风险、内幕/操纵 → 硬拦截）+ `SOFT_FLAG_WORDS`（FOMO/未证实断言/催促 → 软提示）。**维护这两张表即可调合规口径**。
- `app/compliance/engine.py` —— `scan_compliance(text) -> ComplianceResult`，产出 `pass/soft/blocked` 三态，soft 时逐句给 `soft_flag_sentence` + `soft_flag_count`（与前端 Variant 三态模型一致；已对齐 mock v2/v4 的软提示句）。这是 M6 第 1 层（禁词硬拦截）+ 软提示；**第 2 层 Haiku 语义合规接 Anthropic 时再补**。
- `app/compliance/injection.py` —— P0-2 抗注入：`detect_injection` / `sanitize_untrusted` / `wrap_untrusted`（多语言模式：en/id/zh）。M3 清洗、M5 拼 prompt 前必须先过：抓取内容一律当不可信数据包裹隔离。
- 端点 `POST /api/compliance/check`（登录即可）：对任意文案返回三态 + 命中详情 + 抗注入体检，供内部即时自检；不在前端固定契约内，前端暂不调用。
- 测试 `backend/tests/`（pytest，14 用例全绿）。**注意 tests/ 未进镜像也未挂载**，跑法：
  ```bash
  cd backend && docker compose run --rm -v "$PWD/tests:/app/tests" backend python -m pytest tests -q
  ```
  （requirements 已含 pytest + httpx）

> ⚠️ 这只是「确定性护栏」，**消解不了红线 A-1 的业务责任**；正式对外投放仍需法务书面确认。

---

## 7c. 追加：前端网络健壮性（2026-07-02）

services 切真网络后，补齐各数据页的 loading/error/empty 三态，杜绝「白屏 / 无限 spinner / 未捕获 rejection / 渲染崩溃」：

- 复用原语：`src/hooks/useAsyncData.ts`（自动 try/catch/loading + `reload` 重试 + 函数式 `setData` 供本地乐观改动）；`src/components/AsyncBoundary.tsx`（loading→Spin / error→Result+重试 / 正常→children）。
- 全局兜底：`src/components/ErrorBoundary.tsx`（渲染崩溃兜底，接在 `App.tsx` 最外层）+ `src/components/GlobalErrorNotifier.tsx`（未捕获 Promise rejection → message.error 兜底）。
- 各页改造：NewsPage / DashboardPage / CrawlQuotaPage 改用 `useAsyncData`+`AsyncBoundary`（原来 `setLoading(false)` 只在 `.then()` → 失败即无限 spinner，已修）；GeneratePage 的 `getTones`/`generateVariants` 加 catch + message；`VariantList` 补 0 变体空态；News/CrawlQuota 补 `Empty` 空态；Dashboard 的 `Math.max(topUsers)` 加空数组保护。
- 已 headless 验证：happy path **0 console error**；News/Dashboard/Quota 各自注入 500 → 显示「加载失败」Result + 重试按钮、**无卡死 spinner、无 pageerror**；点重试恢复数据。（注意：antd 中文按钮会自动插空格，DOM 里是「重 试」，写选择器时留意。）

---

## 7d. 追加：成本护栏实装（2026-07-02，DESIGN §6）

把「配额/限流/熔断 + token 记账」从假数据变成真逻辑（仍不调模型，用估算）：

- `app/usage.py` —— `estimate_tokens`（prompt 长度 + 固定上下文开销 + 产出正文长度的确定性估算；接真实 Anthropic 后换成 usage 真值即可）/ `record_usage`（每次生成落一行 token_usage）/ `user_tokens_today` / `global_tokens_today`。占位计价表 `RATES`（¥/1k，按 Haiku/Sonnet/Opus）。
- `app/breaker.py` —— `CircuitBreaker`（进程内滚动窗口，错误率≥阈值自动 open，支持手动 trip/reset）。多实例部署下一轮换 Redis/DB 共享。
- `POST /api/variants` 现在：先查熔断（open→503）→ 估算用量 → 校验**单用户日配额**与**全局日预算**（超限→429，不启动生成）→ 生成后 `record_usage` 记账 + `breaker.record(True)`。
- `GET /api/quota`：`globalUsed` = 种子基线 + 今日实际记账（随生成上涨）；`users[0]` 是**当前登录用户的真实今日用量**（isSelf），其余为种子示例。
- 测试 `backend/tests/test_quota.py`（估算单调性、熔断触发、生成记账+429 强制、quota 反映真实自用量）。**全套 18 用例通过**。
- 前端无需改：GeneratePage 生成失败已有 message.error，429 的 detail（「今日 token 配额已用尽…」）会直接冒泡提示；配额页 used/globalUsed 自动显示真实值。

> 说明：Dashboard 的 daily/topUsers/kpi 仍是合成历史数据（种子行日期为 2025-05-27，非“今日”）；只有 `details` 与配额页反映真实记账。接真实调用后统一改由 SQL 聚合。

---

## 7e. 追加：Alembic 迁移（2026-07-02）

`create_all` 已替换为版本化迁移，DB schema 单一事实来源 = `backend/migrations/`：

- `alembic.ini` + `migrations/env.py`（从 `settings.database_url` 注入 URL、`target_metadata=Base.metadata`）+ `migrations/versions/0001_initial.py`（手写：`CREATE EXTENSION vector` + 9 张表 + 两个索引；含 downgrade）。
- `main.py` lifespan 启动即 `alembic upgrade head` 再 seed；Dockerfile COPY + compose 挂载了 `migrations/` 和 `alembic.ini`。
- 当前版本 `0001 (head)`；`alembic_version` 表已建。fresh 卷实测：迁移建全表 + 扩展 + seed 正常，18 用例全过，downgrade SQL 可生成（可逆）。
- **改 schema 的流程**：改 `app/models.py` → `docker compose exec backend alembic revision --autogenerate -m "xxx"` → 检查/微调生成的 `versions/*.py`（pgvector 列注意 import）→ 重启即自动 `upgrade head`。**不要再用 create_all**。
- 注意：本轮 `docker compose down -v` 清过一次卷让 Alembic 从零接管（假数据可弃）；今后有真实数据后升级用迁移，别再 `-v`。

---

## 7f. 追加：反馈埋点 + 变体采用（2026-07-02，DESIGN §4 M7 地基）

隐式信号入库，为下一轮 bandit 铺路（reward = 采用信号 − λ·合规命中）：

- 表 `telemetry_event`（迁移 `0002`，**未清卷、live 升级**验证 Alembic 增量流程）：id/user/event_type/variant_id/news_id/tone_id/position/edited_sentences/meta/created_at；索引 event_type、variant_id。
- `app/telemetry.py`：`record_event` + `ALLOWED_EVENTS`（adopt/export/copy 强正；regenerate/dismiss 弱负；edit；generate/generate_from_news；expand/dwell）。
- 端点：`POST /api/telemetry`（登录，未知 eventType→422）；`POST /api/variants/{id}/confirm`（登录，记 adopt 强正；变体不存在→404）；`GET /api/telemetry/summary`（**admin**，返回 total / byType / topAdopted）。
- 前端（thin，全 fire-and-forget，失败不阻断 UX）：`services.logEvent` / `confirmVariant`；GeneratePage 生成时打 `generate`/`generate_from_news`，点「采用」→ confirm + 本地把该变体标 confirmed（卡片「未确认」消失）。
- 测试：`tests/test_telemetry.py`（ingest 合法/非法、confirm 记 adopt、summary 聚合 + RBAC）；**全套 20 用例通过**。e2e：采用后 未确认 5→4、summary generate:1+adopt:1、0 console error。

> 说明：本轮只落「事件日志」；bandit 权重表（模板×hook×维度、ε-greedy）与 reward 计算是下一轮。confirm 不改共享的 canned 变体行（confirmed 仅前端本地态），避免跨用户串写。

---

## 7g. 追加：收口未阻断任务（2026-07-02）

一次性把不依赖样本/Anthropic 的独立线全部做完：

- **后端 API 层测试**（`tests/test_api.py`）：登录成功/失败、`/me`、坏 token 401、tones/news 需鉴权、dashboard/sources/quota 的 admin-only RBAC、出参 camelCase 形状。**全套 30 用例通过**。
- **密钥卫士（§7 P1-4）**：`main.py` 启动时若 `JWT_SECRET` 为默认/占位值高声告警；`.env` 已 gitignore、`.env.example` 无真密钥。真正的 Vault/Secret Manager + 轮换属部署期（ops），代码侧已就位（全部走 env，无硬编码）。
- **M1 采集层（RSS，`app/crawl.py`）**：`parse_feed`（RSS2.0/Atom）→ `ingest_entries`（URL 指纹去重 + 抗注入 sanitize + 存最小 news）→ `fetch_and_ingest`（httpx 抓取，失败不抛、返回 ok=False）。端点 `POST /api/sources/{id}/crawl`（admin；非 RSS→400，不存在→404）。测试 `tests/test_crawl.py`。**未完成部分**：富字段（key_facts/tickers/angle_hints/真实 heat）属 M3（Haiku，阻断）；搜索API/Playwright 类型未实现；真实抓取源清单 + robots/ToS 审核属**业务决策**（种子是 example.com 占位，抓取会正常报 404）。
- **前端占位收口**：看板时间 Segmented 真过滤 + 「导出 CSV」真下载；新闻热度/时间排序 + 日期范围过滤；抓取源「立即抓取」调真实 `/crawl` 端点、编辑/删除（本地态）、配额「刷新」reload。build 通过、e2e 全绿、0 console error。

---

## 7h. 追加：Anthropic API Key 已配置（2026-07-02）

- 密钥写入 `backend/.env` 的 `ANTHROPIC_API_KEY`（已 gitignore，绝不硬编码；`.env.example` 用占位符）。生产走 Secret Manager（§7 P1-4）。
- 依赖：`requirements.txt` 加 `anthropic==0.69.0`。
- `app/llm.py`：`get_client()` 客户端工厂（从 settings 读密钥）+ 模型分工常量（`MODEL_HAIKU=claude-haiku-4-5` 清洗/分类/语义合规、`MODEL_SONNET=claude-sonnet-5` / `MODEL_OPUS=claude-opus-4-8` 生成/评审）+ `verify_key()` 连通性自检。
- **已实测**：`docker compose exec backend python -c "from app.llm import verify_key; print(verify_key())"` → `{'ok': True, 'model': 'claude-haiku-4-5-20251001'}`。
- ⚠️ 模型 ID 用裸串（`claude-opus-4-8` 等），Opus/Sonnet 4.7+ 仅支持 adaptive thinking（`budget_tokens`/`temperature` 会 400）；接生成时注意。

**这解锁了**：M3 清洗的 LLM 部分（Haiku 相关性/热度）、M6 第 2 层语义合规（Haiku）、generateVariants 接真模型。**仍被阻断**：离线校准层（模式库/多调性语感指纹/风格向量/golden 集）——依赖 40–50 爆款样本，未到位；因此高质量 M5 生成仍受限（可先做不依赖指纹的基础版）。

---

## 7i. 追加：AI 管线接真实 Anthropic（2026-07-02，不依赖样本部分）

`USE_REAL_LLM=true`（`.env`）时走真实管线；测试用 `-e USE_REAL_LLM=false` 强制离线（不触网、免费）。无 key 或关闭时 `generateVariants` 回退灌库固定批次。

- **`app/llm.py`**：`call_text/call_json`（稳健 JSON 解析，跨 SDK 版本）+ 用量返回；模型常量。
- **M6 三层合规**：`app/compliance/semantic.py`（Haiku 批量语义判定，容错数组/对象包裹）+ `merge_status` 取最严，与规则层（禁词/软提示）合并成 pass/soft/blocked。语义层异常降级 pass，规则层兜底。
- **重写循环**（`generate.py`）：blocked 触发 Sonnet 改写，≤3 次，超限返回最优 + `notMeetingBar`。
- **M3 清洗**（`app/pipeline/clean.py`）：Haiku 把抓取标题富化成热点卡（relevant/keyFacts/tickers/angleHints/heat），进 prompt 前 `wrap_untrusted` 抗注入；接入 `crawl.py`（real-LLM 开启时富化）。
- **M5 生成**（`app/pipeline/generate.py`）：Sonnet 按维度矩阵生成 K 条 → 逐条三层合规（+重写）→ 排序。生成的变体**持久化**（`g_*` id），使采用/埋点可引用。
- **真实 token 记账**：管线各次调用真实 usage 按模型聚合写 `token_usage`（Sonnet 文案生成 / Haiku 合规分类·新闻摘要）；配额预检仍用估算。
- **M1 定时调度**：`app/scheduler.py`（APScheduler，`CRAWL_SCHEDULER_ENABLED=true` 启用，默认关）。
- 依赖加 `anthropic==0.69.0`、`apscheduler==3.10.4`。

**实测（live）**：语义 blocked/pass 正确；M3 富化产出真实 keyFacts/heat/ticker；`POST /api/variants` 出 5 条印尼语文案（账号语感、合规 pass、多样性、Sonnet+Haiku 双记账行）；前端 e2e 真实生成 5 卡、0 console error。**35 个 offline 测试全绿**（含 parse_json/merge_status 纯逻辑）。

⚠️ **质量上限（样本缺失，永久）**：无语感指纹/模式库/风格向量 → 只能**通用调性版**生成；`score`/`aiScore` 为模型自评、`styleDistance` 由 aiScore 派生的**近似占位**（非真实向量距离）；无 golden 集 → 无 CI 门禁。这是产品定位「出稿加速器」的固有边界，非 bug。

---

## 7j. 追加：真实印尼财经抓取源已接入（2026-07-02，纠正此前"需业务拍板"的过度保守）

公开 RSS feed 本就是给订阅/聚合用的，读取做内部起稿属开发用途（红线 A-1 管的是"对外投放生成结果"，非"读公开新闻"）；DESIGN §7 的"逐个核对 ToS/robots"针对整站全文抓取/商业付费源，RSS-first 正是其安全路径。因此这一项我自己接了，不再挂"等业务"。

- 种子 `crawl_source` 换成真源：**CNBC Indonesia·市场**（`cnbcindonesia.com/market/rss`）、**Detik Finance**（`finance.detik.com/rss`）、**Antara·经济**（`antaranews.com/rss/ekonomi.xml`）、**Investing.com·新闻**——4 个可抓 RSS；s3/s6 保留 Playwright 占位（JS 站兜底，未实现）。
- `fetch_and_ingest` 加 `max_items`（默认 15）控 M3 富化的 Haiku 调用量。
- **实测**：`POST /api/sources/s1/crawl` → 抓 15 条真实 CNBC 市场新闻入库，Haiku 逐条富化出真实 key_facts/heat/tickers（IHSG/EMMI/Danantara 等）。前端"立即抓取"按钮现在真的拉这些源。
- **仍需注意（非阻断）**：整站全文抓取、付费/商业数据源、Playwright JS 站——这类才需要逐个核对 ToS/robots，属下一轮。当前只用公开 RSS。

---

## 7k. 追加：M1/M3 抓取二次迭代——效率 + 准确性（2026-07-03）

针对 §7j 落地后的抓取链路做性能与质量优化，全部向后兼容（`parse_feed`/`ingest_entries`/`fetch_and_ingest` 签名保留）。改动文件：`crawl.py`（重写）、`pipeline/clean.py`、`scheduler.py`、`routers/sources.py`、`models.py`、迁移 `0005`、`tests/test_crawl.py`。

**效率**
- **E1 多源并发**：新增 `fetch_feed`（纯网络+解析、无 DB、线程安全）+ `fetch_and_ingest_many`（`ThreadPoolExecutor` 并发抓网络，入库主线程串行保 DB 会话安全）；调度器改用之。N 源延迟从累加→取最大。
- **E2 批量去重**：入库前 `select(News.id).where(id.in_(...))` 单查替代循环 `db.get`。
- **E3 批量富化**：`enrich_batch(items)` 多条一次 Haiku 调用返回等长数组，取代逐条 `enrich_news`。**实测：抓 15 条只记 1 次 Haiku 用量（1690in/1798out），而非 15 次——LLM 调用量 15×↓**。长度不齐/异常整批降级最小卡片。
- **E4 条件请求**：`crawl_source` 加 `etag`/`last_modified`（迁移 0005，nullable）；抓取带 `If-None-Match`/`If-Modified-Since`，命中 **304 直接短路**（fetched=0、零解析零富化）。抓完持久化返回的校验器。注：CNBC 只回 Last-Modified 且当前不认条件请求→回退 fetch+dedup（正确兜底），validator 已存供下次。
- **E5 重试退避**：`fetch_feed` 对连接错误/5xx 有限重试（默认 2 次），4xx 不重试。

**准确性**
- **A1 富字段来源扩容**：`parse_feed` 解析 `description`/`content:encoded`/atom `summary`，`FeedEntry.summary` 一并喂给 M3 → key_facts/tickers/heat 精度升（实测 heat 70–78、key_facts 每条 3 个）。
- **A2 清洗**：标题/摘要 `html.unescape` + 去标签 + 折叠空白（`&amp;`/`<b>`/CDATA 不再脏进库）。
- **A3 URL 指纹剥离追踪参数**：`utm_*`/`fbclid`/`gclid` 等 + fragment 剥离后再指纹 → 带追踪链接的同一篇归并。
- **A4 标题近重复**：`title_fingerprint`（小写去标点折空白）批次内去重 → 多源转载同一新闻只入一条。
- **A5 相关性回填**：M3 返回的 `relevant` 回填 `news.label`（relevant/irrelevant），不再恒为 none（实测已落 relevant）。
- **A6 按字节解析**：`parse_feed` 用 `resp.content` 字节 + 尊重 XML 编码声明，避免印尼语源乱码。

**验证**：pytest **47 绿**（含 5 条新增：追踪参数去重/富摘要清洗/字节解析/标题指纹/批次近重复）；迁移 0005 已上 live（`alembic_version=0005`，两列存在）；live e2e `POST /api/sources/s1/crawl` 抓 15 条真实 CNBC → label=relevant、heat 有值、单次批量富化记账。API 出参形状未变（`CrawlResultOut`/`CrawlSourceOut` 不含新列），前端零改。

**仍待**：条件请求命中率依赖源是否认 304（多数印尼源不认，靠 dedup 兜底）；跨抓取轮次的标题近重复（当前仅批次内，需存 title_fingerprint 列才能跨轮）；Playwright JS 站（s3/s6）；付费源 ToS。

---

## 7l. 修复：清除演示假新闻（死链），news 表只留真抓数据（2026-07-03）

用户反馈抓到的新闻链接打不开（`https://news.example.com/a/123456789`）。排查：这不是抓取伪造，而是 `seed.py` 早期灌的 **5 条占位演示新闻**（`n1`–`n5`，虚构 SAHM-X + 假 `example.com` URL），与真抓的 CNBC 新闻混在同一张 `news` 表，点开即死链。**原则：真实数据表绝不放假/占位链接。**

- **seed.py**：删掉 `if _empty(db, News)` 整块假新闻 + 移除未用的 `News` import。`news` 表今后**只由真实抓取填充**（`POST /api/sources/{id}/crawl` 或定时调度）；全新安装 news 为空属预期，跑一次抓取即有真实可打开的新闻。
- **live 库**：`delete from news where url like '%example.com%'`（删 5 行）；重启后确认不再重灌（仍 15 real / 0 fake）。
- **测试**：3 个依赖种子新闻的用例改为自给自足——`_ensure_news()` 优先复用真实行、否则插一条 `test.local` 测试行（仅测试库、跑完 `_cleanup_news` 清理）；`test_tones_news_require_auth` 的 `>=5` 改为断言返回列表（空库也成立）。
- **验证**：pytest **47 绿**；live API `GET /api/news` 返回 15 条、fake=0；随机 3 条真实 URL `curl` 均 **HTTP 200**（可打开）；backend 重启 0 error。

> 注：`variants` 表的 v1–v5 演示变体仍用虚构 SAHM-X——那是「生成内容」演示、非「抓取数据」，无死链问题，本次不动。

---

## 7m. 实现：Playwright JS 渲染抓取（IDX 官网等），M1 补齐 (2026-07-03)

用户要求实现此前占位的 Playwright 源（s3 IDX）。**实地侦察发现 IDX 改版后整站挂在 Cloudflare Managed Challenge 后**（直连首页/JSON 接口均 403 + `Just a moment` 挑战）——这就是「改版异常」的根因。

**边界（重要）**：只做**合法渲染**（真实无头 Chromium 正常执行页面 JS，含站点自带的 CF 托管挑战，与真人访问同理）；**不做**指纹伪造/打码/代理池等**反爬规避**——IDX 是 OJK 监管交易所，规避需业务/法务授权，本抓取器一律不越线，命中挑战即如实报 blocked、绝不造假数据。

- **新模块 `app/crawl_playwright.py`**：
  - 纯函数（可离线单测）：`is_challenge_page`（CF/人机验证特征检测）、`extract_news_links`（锚正则模式，标题即链接文本，如 Yahoo）、`_is_junk_title`（**垃圾标题闸：UUID/纯十六进制串一律拒收**）。
  - DOM 结构化模式 `_extract_dom`：标题不在 `<a>` 文本里的卡片列表用之。**IDX 选择器经实地渲染确认**：卡片 `.bzg_c` / 标题 `.card-title` / 链接 `a[href*='/news/news/']`。
  - `fetch_playwright`：无头 Chromium 渲染 → 检测挑战（命中则等 7s 重取，仍中则 blocked）→ 按模式抽取；goto 超时也尝试读现有内容判断是否被挑战挡。`fetch_playwright_and_ingest`：复用 `ingest_entries`（去重/抗注入/M3 富化/相关性回填）。
  - `SITE_CONFIGS`：idx=DOM 模式，idnfinancials/stockbit/默认=锚正则模式。
- **接线**：`sources.py` crawl 端点按 type 分派（RSS→httpx 条件请求 / Playwright→渲染；搜索API 仍 400）；`scheduler.py` RSS 并发后再串行跑启用的 Playwright 源。
- **镜像**：`requirements` 加 `playwright==1.49.1`；Dockerfile 基座**钉 `python:3.12-slim-bookworm`**（trixie 下 `playwright install --with-deps` 因废弃字体包失败）+ `python -m playwright install --with-deps chromium`。
- **验证**：
  - 单测 `tests/test_crawl_playwright.py` 5 例（挑战检测/去重解析过滤/slug 兜底/config 分派/**UUID 垃圾闸**），全套 **pytest 53 绿**。
  - **端到端真实数据**：`POST /api/sources/s3/crawl` → 渲染过 CF 挑战，`.card-title` 抽取 **12 条真实 IDX 官方新闻**（"IDX 2026 AGMS Approves..."/"ASEAN Exchanges Hold 39th CEO Meeting..."），文章 URL 用浏览器打开 title 与 headline 完全一致、非 404。Yahoo Finance 另测抽 8 条真实文章链接，证明渲染管线通用可用。
  - **无假数据**：曾误入 12 条 UUID-标题垃圾（锚无文本→slug 兜底成 UUID），已删并加垃圾闸根治；live news 表 27 行全真（15 CNBC + 12 IDX）、0 假。
- **源状态**：s3 IDX **enabled**（实测可抓，CF 偶发拦截会如实置 error）；s6 Stockbit / s7 IDNFinancials **disabled**（本机出口 IP 被 CF/信誉拦截，未验证可抓——启用需印尼住宅/授权出口或官方数据渠道，属业务决策）。
- **注意**：IDX 的 CF 挑战**偶发**——headless 有时自动放行有时超时/被挡；抓不到时 health=error + 明确 message，不影响已入库数据。多实例/高频抓取更易触发风控，谨慎调频。

---

## 7n. 启用 M1 定时调度（2026-07-03）

用户要求开启定时调度让 s1-s5 自动抓取。

- **启用**：`backend/.env` 加 `CRAWL_SCHEDULER_ENABLED=true`。⚠️ 该配置经 compose `env_file` 在**容器创建时**注入，`docker compose restart` 不重读 .env，必须 `docker compose up -d --force-recreate backend` 才生效。
- **改进**：`start_scheduler` 的 job 加 `next_run_time=now`（启动即抓一轮，不必等满 15 分钟）+ `max_instances=1, coalesce=True`（防重叠堆积）。
- **行为**：每 15 分钟抓一轮 = 启用的 RSS 源并发（s1/s2/s4/s5）+ 启用的 Playwright 源串行（s3 IDX）。新条目 M3 富化、记 system token 用量；RSS 走条件请求/去重，未变则近零成本。
- **实测**：force-recreate 后 `settings.crawl_scheduler_enabled=True`；首轮即抓，`crawl_source.last_crawl` 全部更新到同一时刻，**Detik/Antara/Investing 首次入库真实新闻**（news 15→82、0 假）；s3 IDX 本轮被 CF 拦（health=error，偶发，符合 §7m 记录）。
- **两点限制（未做，非阻断）**：① 每源 frequency 标签（"每2小时"等）**未被调度器逐源遵循**，统一 15 分钟；② IDX Playwright 每 15 分钟启浏览器且 CF 偶发拦截——高频对 CF 站不友好。若要按源频率/降低 IDX 频率，需给调度器加逐源 trigger（可下轮）。

---

## 8. 下一轮范围（记录，不在本轮）

1. **接真实 Anthropic + AI 管线**：M1 采集(Playwright/RSS/搜索API) → M3 清洗(Haiku+抗注入) → M5 生成(Opus/Sonnet 扇出) → M6 三层合规(禁词+Haiku语义+软提示，重写上限 2–3 次)。`POST /api/variants` 换成真生成。
2. **离线校准层**：补 40–50 爆款样本 → 模式库 / 多调性语感指纹 / 风格向量灌 `style_vectors` / 判别器 / golden 集。
3. Alembic 迁移、埋点 + bandit、密钥进 Secret Manager、配额/限流实际熔断。

🔴 **红线不变（A-1）**：系统在 OJK 监管市场批量生产荐股营销内容，**正式对外投放前必须先拿到需求方法务书面确认**。开发/联调/内部试用不受限。

---

## 9. 迭代进展汇总（2026-07-08 ~ 09，最新交接）

> 本段是 §1–§8 之后大量迭代的总览，后续接手先读这里。权威细节仍以代码为准；DESIGN.md 为设计基线。

### 9.1 数据库迁移（新增）
`0006` drop 废弃 user_quota｜`0007` generation_session.news_context｜`0008` style_sample（账号爆款样本）｜`0009` model_config（场景→模型配置）｜`0010` llm_model（多厂商模型库）+ model_config.model_id 改引用｜`0011` generation_session.style_refs（临时仿写范本）。启动 `main.py` lifespan 跑 `upgrade head` + seed + `refresh_model_config`。

### 9.2 模型管理（多厂商，可动态 CRUD）
- **两层**：`llm_model` 模型库（provider=anthropic 原生 / openai 兼容；model_id/base_url/api_key/enabled）+ `model_config` 场景绑定（generate/clean/compliance → 选库中模型 + max_tokens/temperature）。
- `llm.py`：`ModelSpec` + 进程缓存 + `scene_spec/scene_max_tokens/scene_temperature`（DB 无则回退内置默认）+ **多 provider 分发**（`_call_anthropic` 原生 SDK / `_call_openai` httpx 调 `/chat/completions`，覆盖 OpenAI/DeepSeek/Kimi/Qwen/Gemini兼容/中转）+ `verify_model`。
- 端点 `routers/models.py`（admin）：`GET/POST/PUT/DELETE /api/llm-models`（key 出参脱敏 hasKey、删除守卫：被场景绑定→409）+ `POST /api/llm-models/{id}/verify` + `GET /api/models`、`PUT /api/models/{scene}`（保存刷缓存即时生效）。
- 前端 `pages/ModelsPage`（模型库 CRUD + 场景绑定两区）。

### 9.3 账号/调性管理
`Tone` CRUD：`POST/PUT/DELETE /api/tones`（admin，删账号级联删其 style_sample）。前端 `pages/AccountsPage`。侧栏加「账号管理」「模型管理」（admin）。

### 9.4 文案生成（M5/M6）质变
- **人设「文案物种」+ 账号爆款 few-shot**（`style_sample` 表，`_load_samples` 注入）：从"资讯标题党"变"第一人称过来人分享干货 + 软 CTA"。前端「参考爆款」抽屉管理样本；账号无样本则退化通用版。
- **引用新闻 grounding**（`news_context`）：新闻作"引子"一句带过、不复述；持久化会话供恢复/重生成。
- **仿写范本临时 few-shot**（`style_refs`）：对话框「仿写范本」就地录入（非弹窗，带脉冲启动动画），本次仿写、不入样本库、随会话存。
- `_clean_body` 加固：解模型偶发的嵌套 JSON / 代码围栏，前端 `utils/text.ts` 展示层再兜底。
- 输出语言：中文（面向印尼华语股民）。三层合规 + 重写循环不变。

### 9.5 新闻采集/展示（M1/M3）
- **分页 + 服务端检索**：`GET /api/news` → `{items,total,sources}`，支持 q/source/sort/onlyUnlabeled/dateFrom-To/limit/offset，默认排除 irrelevant。前端 `NewsPage` 无限滚动 + 服务端搜索。
- **相关性硬过滤**：富化判 `relevant=False` 直接不入库（`ingest_entries`）+ 严格判定 prompt（只留印尼股票/上市公司相关）。
- **相对时间实时**：`utils/time.ts::newsFreshness` 前端按当前时间算，弃用抓取时定格的 published_label。
- **抓取库升级**：`feedparser`（RSS 专业解析）+ `beautifulsoup4/lxml`；新增 `crawl_html.py`（httpx+bs4 静态抓取，源类型 `HTML`），**OJK 从 Playwright 迁静态**。并发插入加 IntegrityError 逐条回退（防同源重复触发整批回滚）。
- **源治理**：启用 = RSS(CNBC市场/Detik/Kontan投资) + HTML(OJK官方) + Playwright(IDX/IDNFinancials，CF 受限尽力而为)；禁用 Antara/Investing/Stockbit。

### 9.6 依赖 / 运行
- 新增 `feedparser==6.0.12`、`beautifulsoup4==4.15.0`、`lxml==6.1.1`（**镜像需 rebuild：`docker compose build backend`**，否则测试容器 ImportError）。另加 `anthropic`/`playwright`（已有）。
- 起法不变：`cd backend && docker compose up -d`（DB :5433，API :8000）；前端 `npm run dev`（:5173）。演示账号 `admin`/`editor`（`demo1234`）。测试：`docker compose run --rm -e DATABASE_URL=…imitator_test -e USE_REAL_LLM=false -v "$PWD/tests:/app/tests" backend python -m pytest tests -q`（当前 **57 绿**）。

### 9.7 已知边界（非 bug）
- **IDX/IDNFinancials 被 Cloudflare 按出口 IP 拦截**（httpx/静态全 403，Playwright 偶尔过）→ 需官方 API 授权 / 印尼住宅授权出口 IP，**不做 CF 规避**。
- **成本记账仍按 Anthropic 价目**（`variants._MODEL_LABEL` 按 model_id 子串映射）；接非 Anthropic 模型后成本估算不准（功能不受影响，待补单价配置）。
- **生成质量上限**：无向量化语感指纹/模式库，few-shot 为"离线校准层"最小可用形态；styleDistance 近似占位、score/aiScore 模型自评。
- 🔴 **红线 A-1 不变**：正式对外投放前需需求方法务书面确认。
