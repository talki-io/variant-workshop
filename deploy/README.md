# 部署手册

单机 Docker Compose 生产部署。为什么不是 K8s / 多副本 → [`docs/decisions/0004-deployment-single-node-compose.md`](../docs/decisions/0004-deployment-single-node-compose.md)。

服务器上装了宝塔面板 → 先读本文了解栈本身，再看 [`baota.md`](baota.md)（两层 Nginx 怎么摆、代理超时、大陆网络下的中转配置）。

> 🔴 **红线 A-1**：本手册覆盖的是**把系统跑起来供内部试用**。
> 系统本身没有任何对外发布端点——A-1 约束的是「人拿产出的文案去对外投放」，那一步仍需需求方法务书面确认。
> 部署 ≠ 放行投放。

---

## 拓扑

```
                  :8080 (默认只绑 127.0.0.1)
                     │
              ┌──────▼──────┐
              │  frontend   │  nginx：静态托管 + SPA fallback
              │  (nginx)    │  /api/ ──反代──┐
              └─────────────┘                │
                                      ┌──────▼──────┐
                                      │   backend   │  uvicorn 单 worker
                                      │  (FastAPI)  │  lifespan: 迁移 → seed → 调度
                                      └──────┬──────┘
                                             │
                                      ┌──────▼──────┐
                                      │     db      │  pgvector/pg16
                                      │ (Postgres)  │  卷 pgdata，不暴露端口
                                      └─────────────┘
```

只有 frontend 对外。backend 与 db 不映射宿主端口，仅在 compose 内网可达。

---

## 首次部署

### 1. 准备配置

```bash
cd deploy
cp .env.example .env
chmod 600 .env
```

填 `.env`（三个必填项）：

```bash
openssl rand -base64 24   # → POSTGRES_PASSWORD
openssl rand -hex 32      # → JWT_SECRET
                          # → ANTHROPIC_API_KEY 用你自己的
```

`DATABASE_URL` 不用填——compose 会用上面的用户名/密码/库名自行组装。

### 2. 起栈

```bash
cd /path/to/variant-workshop
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

首次构建约 3–5 分钟（Playwright 要拉 Chromium）。启动时 `lifespan` 会自动跑 `alembic upgrade head`，不需要手工迁移。

### 3. 建管理员

生产**不灌演示账号**（`SEED_DEMO_DATA=false`）。空库首启后没有任何用户，必须手工开第一个口子：

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.create_admin <用户名>
```

按提示输两遍密码（≥12 位，拒绝 `demo1234`）。非交互场景用 `ADMIN_PASSWORD` 环境变量传，**不要用命令行参数**——argv 会进 shell history，也会被同机 `ps` 看到。

### 4. 验收

```bash
curl -s localhost:8080/healthz                    # → ok
curl -so /dev/null -w '%{http_code}\n' localhost:8080/          # → 200
curl -so /dev/null -w '%{http_code}\n' localhost:8080/api/tones # → 401（未带 token，反代通）
```

再确认演示账号确实进不去：

```bash
curl -so /dev/null -w '%{http_code}\n' -X POST localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"demo1234"}'
# → 401。若返回 200，立刻停服排查 SEED_DEMO_DATA。
```

---

## 对外暴露与 HTTPS

默认 `HTTP_BIND=127.0.0.1:8080`，只有本机可达。远程访问先用 SSH 隧道：

```bash
ssh -L 8080:127.0.0.1:8080 user@server
```

**要真正对外，必须先在前面放一层终结 TLS 的反代**（Caddy / Nginx / 云 LB），再把 `HTTP_BIND` 改成 `0.0.0.0:8080`。这个栈自己不做 HTTPS——JWT 明文过公网等于没有鉴权。

Caddy 最省事（自动签证书）：

```caddyfile
your-domain.com {
    reverse_proxy 127.0.0.1:8080
}
```

---

## 日常运维

```bash
C="docker compose -f deploy/docker-compose.prod.yml"

$C ps                        # 状态 + 健康
$C logs -f backend           # 跟日志（已按 10m×3 轮转）
$C restart backend           # 重启单个服务
$C up -d --build             # 拉新代码后重建
$C exec db psql -U app imitator   # 进库排查
```

### 更新版本

```bash
git pull
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

`lifespan` 会自动把新迁移跑到 head。**改表只新增迁移版本，不改写已应用的 `migrations/versions/*.py`。**

### 备份

卷里是真实抓取的新闻、token 记账和用户数据。至少每天一次：

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T db \
  pg_dump -U app -Fc imitator > backup-$(date +%F).dump
```

恢复：

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T db \
  pg_restore -U app -d imitator --clean --if-exists < backup-2026-07-10.dump
```

> ⚠️ **永远不要对这个栈跑 `docker compose down -v`。** `-v` 会连 `pgdata` 卷一起删——真实新闻、迁移状态、用户全没。停服用 `down`（不带 `-v`）。

---

## 成本闸门

两个开关直接决定花不花钱，`.env` 里控制：

| 变量 | 影响 |
| --- | --- |
| `USE_REAL_LLM=true` | 走真实 Anthropic 管线。`false` 时用离线桩，零 token 费用。需与非空 `ANTHROPIC_API_KEY` 同时满足才生效。 |
| `CRAWL_SCHEDULER_ENABLED=true` | 每 15 分钟自动抓一轮启用的源。`USE_REAL_LLM=true` 时还会顺带 Haiku 富化——**这会持续产生费用**。 |

想先观察再放开：`CRAWL_SCHEDULER_ENABLED=false`，改用「抓取源」页手动触发。

配额与熔断在「配额」页配（默认单用户 20k/日、全局 1M/日、错误率 ≥20% 持续 5 分钟熔断）。

---

## 排障

| 症状 | 原因 / 处置 |
| --- | --- |
| 生成变体时前端 504 | Nginx `proxy_read_timeout` 已设 300s。仍超时说明模型侧卡住，看 `logs backend`。 |
| Playwright 抓取崩溃 | Chromium 吃 `/dev/shm`。compose 已给 backend `shm_size: 1gb`；若仍崩，调大。 |
| backend 起不来，日志报迁移冲突 | 多半是手工改过已应用的迁移文件。回滚该文件，改用新增版本。 |
| 启动日志有「⚠️ JWT_SECRET 使用了默认/占位值」 | `.env` 里 `JWT_SECRET` 没填。填上重启（已签发的 token 会全部失效）。 |
| 启动日志有「库中没有任何用户」 | 正常——生产不灌演示账号。跑 `create_admin`（见上）。 |
| Cloudflare 拦截导致抓取源 `health=error` | 预期行为，系统只识别并放弃，**不做规避**（[ADR 0003](../docs/decisions/0003-no-cloudflare-evasion.md)）。 |

---

## 已知边界

- **backend 锁死单副本**，且 uvicorn 不能加 `--workers`。原因与扩容前提见 [ADR 0004](../docs/decisions/0004-deployment-single-node-compose.md)。
- **没有 CI**。构建门禁靠人手动跑（`AGENTS.md` §5）。
- **无 HTTPS 终结**、无集中式日志、无 Prometheus 指标。以当前使用规模（内部几名素材员）这些不是瓶颈；真需要时按 ADR 0004 的「何时该重新评估」一节推进。
