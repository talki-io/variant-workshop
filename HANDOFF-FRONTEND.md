# 交接文档 · 前端第一轮（骨架 + mock）

> 状态：**第一轮已完成并验证通过**。本文件供明天续上用。
> 阅读顺序：先本文件 → 需要背景再看 `DESIGN.md` / `HANDOFF.md` / `UI-DESIGN.md`。
> 落地计划原文：`~/.claude/plans/serene-sparking-shore.md`。

---

## 1. 今天做完了什么

**第一轮 = 前端骨架先行**（用户拍板：前端先行 / 后端定 Python+FastAPI / 缺爆款样本）。

- 产出 `frontend/`：Vite + React 18 + TS + antd 全家桶（+ `@ant-design/x` 对话 + `@ant-design/charts` 图表 + react-router v6）。
- 按 `images/design-draft/` 的 6 张设计图 **1:1 还原 6 屏**，全部 **mock 数据、不接后端**。
- **验证通过**：`npm run build` ✅；headless Chrome 走查 6 屏 **console error = 0**；登录→发消息→出 5 张变体卡 ✅；看板图表渲染 ✅；6 张实拍截图与设计图逐一比对一致。

之前已产出：`UI-DESIGN.md`（面向图像模型的 UI 规范）+ 6 张设计图。

---

## 2. 怎么跑起来（明天第一步）

```bash
cd /home/tel/aiProject/ai-agent-imitator/frontend
npm install      # 首次或换机才需要
npm run dev      # http://localhost:5173
```
登录：**任意用户名+任意密码**，默认「管理员」。左下角用户菜单可**一键切素材员/管理员**验证权限（素材员看不到「消耗看板 / 抓取与配额」）。

---

## 3. 代码地图（改哪找哪）

```
frontend/src/
  theme/tokens.ts        # 设计 token（色板/圆角/字体），全局 antd 主题
  types/index.ts         # 所有数据类型（Variant/NewsItem/Dashboard/Source/Quota/Tone/User）
  auth/                  # AuthContext（mock 登录/角色）+ 路由守卫
  layout/                # AppLayout / Sider（角色过滤菜单）/ HeaderBar
  components/            # 复用组件：VariantCard(三态)/ToneSelector/ScoreRing/ComplianceBadge/HeatBar
  pages/                 # LoginPage / GeneratePage(核心三栏) / NewsPage / DashboardPage / CrawlQuotaPage / ComponentsPage
  services/index.ts      # ★数据接触面：现在返回 mock，下一轮换成 fetch(FastAPI)
  mocks/                 # 静态假数据（脱敏样例 SAHM-X / @akun_demo / 财经源A-C）
```

**关键约定**：页面只调 `src/services/*` 的 async 函数，绝不直接 import `mocks/`。下一轮把 `services/index.ts` 每个函数体从「返回 mock」换成「`fetch('/api/...')`」即可，**页面零改动**。

---

## 4. 本轮明确没做（下一轮范围）

按计划本轮 out of scope，明天从这里接：
1. **起 `backend/`（Python FastAPI）**：鉴权 + `/api/variants|news|dashboard|sources|quota`。
2. **前端切真数据**：`services/index.ts` mock → `fetch`（唯一改动点）。
3. **真实鉴权**替换 mock AuthContext（NextAuth/JWT，见 DESIGN §7）。
4. **离线校准层**：需先补 **40–50 条爆款样本**（当前缺，是这条的前置阻断）→ 模式库/多调性语感指纹/风格向量/判别器/golden 集。
5. M1 采集 → M3 清洗(抗注入) → M5 生成 → M6 三层合规评审(禁词+Haiku语义+软提示，重写上限 2–3 次)。

**资源现状**：有 Anthropic API Key + Postgres/pgvector；**缺爆款样本**。

---

## 5. 明天可选的三个起点（按依赖，推荐 A）

- **A. 后端脚手架**：起 `backend/` FastAPI + 建 DB 表 + 先用假数据实现 `/api/*`，让前端 services 切过去跑通「前端↔后端」闭环。**最能证明架构可行。**
- **B. 补爆款样本 + 离线校准层**：地基活，但被「拿到 40–50 条样本」阻断，需先向需求方要样本。
- **C. 前端补收尾**：响应式细化 / 空态 / 组件规范页打磨（非必需，骨架已达标）。

---

## 6. 注意事项 / 坑

- **图像生成**：给 gptimages 的提示词**绝不能含真实品牌/公司/股票代码**（Ant Design/CNBC/BBRI 等触发「第三方内容相似」拒绝），一律虚构名。
- **antd 版本**：InputNumber 用 `suffix` 不用 `addonAfter`（已弃用）；Table 分页 `total` 不要设成远大于 dataSource 长度（会告警）——真接后端做服务端分页时再设 total。
- **@ant-design/x**：Sender 回车即提交（发送按钮是纯图标，无「发送」文字）；Bubble.List / Prompts 用法见 `pages/GeneratePage/ChatPanel.tsx`。
- `npm run build` 会有 bundle >500KB 告警，正常（antd+charts 体积），需要再做 code-split。

---

## 7. 🔴 红线（不变）

系统在 OJK 监管市场批量生产荐股营销内容，**正式对外投放前必须先拿到需求方法务书面确认（A-1）**。开发/联调/内部试用不受限，仅真实对外发布受限。详见 `HANDOFF.md`。
