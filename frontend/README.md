# 变体工坊 · 前端

React SPA，**已接真实 FastAPI 后端**（经 `services/` + `http.ts` + Vite 代理）。

项目介绍与技术栈见 [`../README.md`](../README.md)；启动、演示账号、测试与坑见 [`../docs/development-guide.md`](../docs/development-guide.md)；UI 规范见 [`../docs/ui-design.md`](../docs/ui-design.md)（配 [`../docs/assets/design-draft/`](../docs/assets/design-draft/) 设计基准图）。

```bash
npm install
npm run dev      # http://localhost:5173，proxy /api → :8000（需后端先起来）
npm run build    # tsc --noEmit + 产物构建
```

## 路由

| 路由 | 屏 | 角色 |
|---|---|---|
| `/login` | 登录 | — |
| `/generate` | 文案生成工作台（历史 ｜ 对话 ｜ 变体，三栏） | 全部 |
| `/news` | 新闻库（分页检索 + 详情抽屉 + 打标 + 用它生成） | 全部 |
| `/dashboard` | 消耗看板（KPI + 图表 + 明细） | 管理员 |
| `/crawl-quota` | 抓取与配额 | 管理员 |
| `/accounts` | 账号 / 调性管理 | 管理员 |
| `/models` | 模型管理（多厂商） | 管理员 |
| `/components` | 组件走查页 | **仅开发期**，生产构建不挂载 |

## 目录

- `src/services/` —— **数据接触面**：页面只依赖这里的 async 函数，全部走真实 API，不含 mock。
- `src/components/` —— 生产组件（VariantCard / ToneSelector / ScoreRing / ComplianceBadge / HeatBar / AsyncBoundary / ErrorBoundary / GlobalErrorNotifier）。
- `src/pages/` —— 业务页面。
- `src/theme/tokens.ts` —— 设计标记。
- `src/dev-only/` —— ⚠️ 仅开发期：组件走查页 + mock 假数据。约定见 [`../docs/development-guide.md`](../docs/development-guide.md) §6。

**生产代码不得从 `dev-only/` import。**

---

> 🔴 **红线 A-1**：正式对外投放前需法务书面确认。见 [`../docs/decisions/0001-arch-review-closure.md`](../docs/decisions/0001-arch-review-closure.md)。
