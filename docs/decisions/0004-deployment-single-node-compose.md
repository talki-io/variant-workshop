# ADR 0004 · 生产部署用单机 Compose，backend 锁定单副本

- **状态**：Accepted
- **日期**：2026-07-10
- **来源**：生产部署方案落地（`deploy/`）

## 背景

需要把系统部署起来供内部试用。默认的运维直觉是「上 K8s、多副本、高可用」，但本项目有两处代码级约束让多副本直接不成立，且业务规模也不支持这套复杂度。

`backend/docker-compose.yml` 是纯开发配置：`--reload`、bind-mount 源码、`POSTGRES_PASSWORD: app`、db 端口直接映射到宿主、前端根本没有容器化。原样搬上服务器不安全。

## 决策

**单机 Docker Compose 部署**（`deploy/docker-compose.prod.yml`），三个服务：nginx 托管前端并反代 `/api` → 单副本 uvicorn → Postgres。

**backend 固定 `replicas: 1`，且 uvicorn 不得加 `--workers`。**

**生产关闭演示数据**（`SEED_DEMO_DATA=false`），管理员用 `python -m app.create_admin` 单独创建。

## 理由

### 为什么 backend 不能多副本

两处都在**每个进程**里执行，多开一个就出一份问题：

1. `app/main.py` 的 `lifespan` 调用 `command.upgrade(alembic_cfg, "head")`。多进程同时启动 = 并发迁移竞争。
2. `app/scheduler.py` 用进程内 `BackgroundScheduler`。N 个副本 = 同一批 RSS 源被抓 N 遍，`USE_REAL_LLM=true` 时 Haiku 富化的 token 也烧 N 份。该文件 docstring 自己写着「多实例部署应改用集中式调度，避免重复抓取」。

`uvicorn --workers N` 会 fork 出 N 个进程，触发的是同一个问题，所以一并禁止。

### 为什么不上 K8s

系统是单体 FastAPI + 一个 Postgres + 一个 React SPA，使用者是内部几名素材员，QPS 以「个位数/分钟」计。K8s / 服务网格 / 多副本带来的是运维复杂度，不是可用性——而且在上面那两处约束没解决之前，多副本反而是**错的**（重复抓取、重复计费）。

### 为什么必须关演示数据

`seed()` 原本无条件在 `lifespan` 里跑，空库首启会建 `admin` 和 `editor`，密码硬编码 `demo1234`。生产部署 = 一个公网可登录的管理员后门。这是部署前的阻断项，不是可延后的技术债。

## 后果

- `app/seed.py` 拆为 `seed_system`（模型库 / 场景绑定 / 配额 / 真实抓取源——所有环境都灌）与 `seed_demo`（种子账号 / 示例调性 / 变体 / 爆款样本——生产跳过）。`seed(db, demo=True)` 保持默认行为，`tests/conftest.py` 与 57 个测试不受影响。
- 新增 `app/create_admin.py`。密码走交互提示或 `ADMIN_PASSWORD` 环境变量，**不接受 argv**（会进 shell history 和 `ps`）。
  > 后续变更（2026-07-10）：该文件已更名为 `app/create_user.py` 并加 `--role editor|admin`（默认 `editor`），以便批量建素材员账号。命令改为 `python -m app.create_user <用户名> [--role admin]`。
- 生产库首启后 `users` 表为空，`lifespan` 会打一条告警日志提示建管理员。属预期，不是故障。
- 这个栈**不终结 TLS**，默认只绑 `127.0.0.1`。对外暴露必须先在前面放一层带证书的反代。
- 前端生产走 nginx 反代 `/api`（同源），因此 `main.py` 里那段只允许 `localhost:5173` 的 CORS 配置不需要为生产放开。

## 何时该重新评估

出现下面任一条，再考虑多副本 / K8s：

- 单副本 uvicorn 扛不住并发（先看 `docker stats` 和 p95 延迟，不要凭感觉）。
- 需要滚动更新做到零停机（当前 `up -d --build` 有秒级中断）。
- 多人多租户，配额与熔断需要跨实例共享状态。

**扩容前提**（必须先做，否则多副本必然出问题）：

1. 把 `alembic upgrade head` 移出 `lifespan`，改成部署流程里的独立一步（或一个 init container / one-shot 服务）。
2. 把 APScheduler 移出应用进程，改成集中式调度——单独的 scheduler 服务，或换成带分布式锁的调度器。

在这两件事做完之前，`replicas: 1` 是正确性要求，不是保守选择。
