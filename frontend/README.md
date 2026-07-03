# 变体工坊 · 前端（第一轮：骨架 + mock）

印尼股市营销文案变体系统的前端。本轮为**前端骨架先行**：按设计图 1:1 还原 6 屏，全部走 mock 数据，**不接后端**。设计与需求见上级目录 `DESIGN.md` / `HANDOFF.md` / `UI-DESIGN.md`，设计图见 `../images/design-draft/`。

## 技术栈
- Vite + React 18 + TypeScript
- antd 5（主题 token 见 `src/theme/tokens.ts`）
- @ant-design/x（对话）· @ant-design/charts（看板）
- react-router-dom v6

## 运行
```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # tsc 类型检查 + 产物构建
```

## 登录（mock）
任意用户名 + 任意密码即可登录，默认**管理员**角色。登录后可在左下角用户菜单**一键切换素材员/管理员**（dev），验证权限：素材员看不到「消耗看板 / 抓取与配额」。

## 6 屏
| 路由 | 屏 | 角色 |
|---|---|---|
| `/login` | 登录 | — |
| `/generate` | 文案生成工作台（核心：调性→对话→变体卡片） | 全部 |
| `/news` | 新闻库（筛选 + 详情抽屉 + 用它生成） | 全部 |
| `/dashboard` | 消耗看板（KPI + 图表 + 明细） | 管理员 |
| `/crawl-quota` | 抓取与配额 | 管理员 |
| `/components` | 组件规范（VariantCard 三态 / ToneSelector / tokens） | 全部 |

## 目录
- `src/services/` —— **数据接触面**：当前包 mock，下一轮把函数体换成 `fetch(FastAPI)` 即可，页面零改动。
- `src/mocks/` —— 静态假数据（脱敏样例：`SAHM-X` / `@akun_demo` / `财经源A-C`）。
- `src/components/` —— 复用组件（VariantCard / ToneSelector / ScoreRing / ComplianceBadge / HeatBar）。

## 下一轮（未做）
后端 FastAPI + 真实 Anthropic 调用 + Postgres/pgvector + 离线校准层；真实鉴权。详见 `../DESIGN.md`。

> 🔴 红线：正式对外投放前需法务书面回置（A-1），见 `../HANDOFF.md`。
