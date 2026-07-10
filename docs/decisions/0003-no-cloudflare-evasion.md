# ADR 0003 · 不做 Cloudflare 规避

- **状态**：Accepted
- **日期**：2026-07-09（提炼归档于 2026-07-10）
- **来源**：交接文档 `HANDOFF-BACKEND.md` §9.7（已删除，见 git 历史）

## 背景

IDX 官网与 IDNFinancials 按出口 IP 被 Cloudflare 拦截：`httpx` 与静态抓取一律 403，Playwright 偶尔能过。

## 决策

**不实现任何 Cloudflare 规避手段**（不做指纹伪装、不接打码、不轮换代理绕 WAF）。

需要这两个源时，走**官方 API 授权**或**印尼住宅授权出口 IP**。

## 理由

系统已经在 OJK 监管市场批量生产荐股营销内容（见 [`0001-arch-review-closure.md`](0001-arch-review-closure.md) 的 A-1 红线）。在此之上再叠加对目标站点反爬机制的主动规避，会把「内容合规风险」扩大成「访问行为合规风险」，且违反站点 ToS。`docs/architecture.md` §7 已要求抓取源必须做 ToS/robots 确认。

## 后果

- `crawl_playwright.py` 的 `is_challenge_page` 只用于**识别并放弃**挑战页，不用于绕过。
- 抓取源清单以 RSS/官方 API 可达者为准（CNBC / Detik / Antara / Investing 等）。
- 看到「绕过 Cloudflare」「过 CF 五秒盾」这类需求，停下来上报，不要自己实现。
